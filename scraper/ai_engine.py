import os
import json
import re
import requests
from groq import Groq

# =========================================================
# 1. 모델 선택 로직
# =========================================================

def get_groq_text_models():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return []
    try:
        client = Groq(api_key=api_key)
        all_models = client.models.list()
        valid_models = []
        for m in all_models.data:
            mid = m.id.lower()
            if any(x in mid for x in ['vision', 'whisper', 'audio', 'guard', 'safe']): continue
            valid_models.append(m.id)
        valid_models.sort(key=lambda x: '70b' in x, reverse=True) 
        return valid_models
    except: return []

def get_openrouter_text_models():
    fallback_models = [
        "google/gemini-2.0-flash-lite-preview-02-05:free",
        "google/gemini-2.0-flash-exp:free",
        "mistralai/mistral-7b-instruct:free",
        "meta-llama/llama-3-8b-instruct:free",
    ]
    try:
        res = requests.get("https://openrouter.ai/api/v1/models", timeout=3)
        if res.status_code == 200:
            data = res.json().get('data', [])
            valid_models = []
            for m in data:
                mid = m['id'].lower()
                if ':free' in mid and not any(x in mid for x in ['vision', 'image', '3d', 'diffusion']):
                    valid_models.append(m['id'])
            if valid_models: return valid_models
    except: pass
    return fallback_models

# =========================================================
# 2. AI 답변 정제기
# =========================================================

def clean_ai_response(text):
    if not text: return ""
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        for part in parts:
            if "{" in part or "[" in part:
                cleaned = part.replace("json", "").strip()
                break
    return cleaned

def ask_ai_master(system_prompt, user_input):
    raw_response = ""
    
    # Groq 시도
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        models = get_groq_text_models()
        client = Groq(api_key=groq_key)
        for model_id in models:
            try:
                completion = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
                    temperature=0.3
                )
                raw_response = completion.choices[0].message.content.strip()
                if raw_response: break
            except: continue

    # OpenRouter 시도
    if not raw_response:
        or_key = os.getenv("OPENROUTER_API_KEY")
        if or_key:
            models = get_openrouter_text_models()
            for model_id in models:
                try:
                    res = requests.post(
                        url="https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {or_key}"},
                        json={
                            "model": model_id,
                            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
                            "temperature": 0.3
                        },
                        timeout=30
                    )
                    if res.status_code == 200:
                        raw_response = res.json()['choices'][0]['message']['content']
                        if raw_response: break
                except: continue

    return clean_ai_response(raw_response)

def parse_json_result(text):
    if not text: return []
    text = clean_ai_response(text)
    try: return json.loads(text)
    except: pass
    try:
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match: return json.loads(match.group(0))
    except: pass
    return []

# =========================================================
# 3. [핵심] 카테고리별 맞춤형 분류 규칙 (Strict Mode)
# =========================================================

def extract_top_entities(category, news_text_data):
    
    # 카테고리별로 AI에게 내릴 특별 지령 (배우 금지, 기업 금지 등)
    specific_rule = ""
    
    if category == 'K-Drama':
        specific_rule = """
        [CONTEXT: K-DRAMA MODE]
        1. 'content' MUST be a Drama Title (e.g. 'Squid Game', 'The Glory').
        2. STRICTLY CLASSIFY ACTORS AS 'person' (e.g. 'Kim Soo-hyun', 'Song Hye-kyo' -> 'person').
        3. Do NOT include OSTs or Songs as content here.
        """
    elif category == 'K-Movie':
        specific_rule = """
        [CONTEXT: K-MOVIE MODE]
        1. 'content' MUST be a Movie Title (e.g. 'Parasite', 'Exhuma').
        2. STRICTLY CLASSIFY ACTORS/DIRECTORS AS 'person'.
        """
    elif category == 'K-Pop':
        specific_rule = """
        [CONTEXT: K-POP MODE]
        1. 'content' MUST be a Song Title or Album Name.
        2. STRICTLY CLASSIFY SINGERS/GROUPS AS 'person'.
        """
    elif category == 'K-Culture':
        specific_rule = """
        [CONTEXT: K-CULTURE MODE]
        1. 'content' MUST be a Food, Place (Hotspot), Fashion Item, or Festival.
        2. STRICTLY EXCLUDE CORPORATE NEWS (e.g. 'Samsung', 'Expo', 'Business', 'Stock').
        3. STRICTLY EXCLUDE CELEBRITIES.
        """
    
    system_prompt = f"""
    You are a K-Content Trend Analyst for '{category}'. 
    
    [TASK]
    Analyze the news summaries and extract keywords.
    Crucially, CLASSIFY the TYPE of each keyword based on the specific rules below.
    
    {specific_rule}
    
    [CLASSIFICATION TYPES]
    1. 'content': The ACTUAL TITLE of the work (Drama, Movie, Song) or Trend (Food, Place).
    2. 'person': Names of Humans (Actors, Singers, Idols, MCs).
    3. 'organization': Companies, Broadcasters (Netflix, MBC), Agencies (HYBE).
    4. 'generic': Common words (Review, Update, Chart, Ranking).

    [OUTPUT FORMAT]
    - Return a JSON LIST of objects:
      [{{ "keyword": "Actual Title", "type": "content" }}, {{ "keyword": "Actor Name", "type": "person" }}]
    - Max 40 items.
    - Translate Korean titles to English.
    """
    
    user_input = news_text_data[:50000]
    raw_result = ask_ai_master(system_prompt, user_input)
    parsed = parse_json_result(raw_result)
    
    if isinstance(parsed, list):
        seen = set()
        unique_list = []
        for item in parsed:
            if isinstance(item, dict) and 'keyword' in item and 'type' in item:
                kw = item['keyword']
                k_type = item['type'].lower()
                
                # 'organization'과 'generic'은 무조건 버림
                if k_type in ['content', 'person']:
                    if kw not in seen:
                        seen.add(kw)
                        unique_list.append(item)
        return unique_list
    return []

# =========================================================
# 4. 브리핑 생성
# =========================================================

def synthesize_briefing(keyword, news_contents):
    system_prompt = f"""
    You are a Professional News Editor. Topic: {keyword}
    [TASK] Write a comprehensive news briefing in ENGLISH (5-20 lines).
    [CRITICAL] NO <think> tags. If data is invalid or purely corporate PR, output "INVALID_DATA".
    """
    
    user_input = "\n\n".join(news_contents)[:40000] 
    result = ask_ai_master(system_prompt, user_input)
    
    if not result or "INVALID_DATA" in result or len(result) < 50:
        return None
        
    return result
