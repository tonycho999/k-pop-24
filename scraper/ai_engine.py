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
            if 'vision' in mid or 'whisper' in mid or 'audio' in mid: continue
            valid_models.append(m.id)
        valid_models.sort(reverse=True)
        return valid_models
    except: return []

def get_openrouter_text_models():
    try:
        res = requests.get("https://openrouter.ai/api/v1/models", timeout=5)
        if res.status_code != 200: return []
        data = res.json().get('data', [])
        valid_models = []
        for m in data:
            mid = m['id'].lower()
            if ':free' in mid and ('chat' in mid or 'instruct' in mid or 'gpt' in mid):
                if 'diffusion' in mid or 'image' in mid or 'vision' in mid or '3d' in mid: continue
                valid_models.append(m['id'])
        valid_models.sort(reverse=True)
        return valid_models
    except: return []

def get_hf_text_models():
    return ["mistralai/Mistral-7B-Instruct-v0.3"]

# =========================================================
# 2. AI 답변 정제기 (<think> 제거)
# =========================================================

def clean_ai_response(text):
    if not text: return ""
    # <think> 태그 제거
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    
    # ```json 코드블럭 제거
    if "```" in cleaned:
        parts = cleaned.split("```")
        for part in parts:
            if "{" in part or "[" in part:
                cleaned = part.replace("json", "").strip()
                break
    return cleaned

def ask_ai_master(system_prompt, user_input):
    raw_response = ""
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

    if not raw_response:
        or_key = os.getenv("OPENROUTER_API_KEY")
        if or_key:
            models = get_openrouter_text_models()
            for model_id in models:
                try:
                    res = requests.post(
                        url="[https://openrouter.ai/api/v1/chat/completions](https://openrouter.ai/api/v1/chat/completions)",
                        headers={"Authorization": f"Bearer {or_key}"},
                        json={
                            "model": model_id,
                            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
                            "temperature": 0.3
                        },
                        timeout=20
                    )
                    if res.status_code == 200:
                        raw_response = res.json()['choices'][0]['message']['content']
                        if raw_response: break
                except: continue

    return clean_ai_response(raw_response)

# =========================================================
# 3. JSON 파서
# =========================================================

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
# 4. [핵심 수정] 키워드 추출 + 분류 (사람 vs 작품 구분)
# =========================================================

def extract_top_entities(category, news_titles):
    """
    뉴스 제목에서 키워드를 뽑고, 이것이 '사람(그룹)'인지 '작품(제목)'인지 분류함.
    """
    
    system_prompt = f"""
    You are a K-Content Trend Analyst for '{category}'. 
    
    [TASK]
    1. Analyze the news titles and extract the most mentioned keywords (Singers, Actors, Titles, Topics).
    2. CLASSIFY each keyword as either 'person' (includes Groups, Bands, Actors, MCs) or 'content' (Songs, Dramas, Movies, Shows, Places, Concepts).
    
    [RULES]
    - 'person': BTS, NewJeans, IU, Kim Soo-hyun, Yoo Jae-suk, SEVENTEEN.
    - 'content': Hype Boy, Squid Game, The Glory, Running Man, Han River, Fashion Week.
    - Output format: JSON LIST of objects. 
      Example: [{{"keyword": "BTS", "type": "person"}}, {{"keyword": "Dynamite", "type": "content"}}]
    - Max 40 items.
    - Translate Korean names to English.
    """
    
    user_input = "\n".join(news_titles)[:15000]
    
    raw_result = ask_ai_master(system_prompt, user_input)
    parsed = parse_json_result(raw_result)
    
    # 리스트인지 확인하고 중복 제거 (keyword 기준)
    if isinstance(parsed, list):
        seen = set()
        unique_list = []
        for item in parsed:
            if isinstance(item, dict) and 'keyword' in item:
                if item['keyword'] not in seen:
                    seen.add(item['keyword'])
                    unique_list.append(item)
        return unique_list
    return []

# =========================================================
# 5. 요약 로직 (<think> 태그 절대 금지)
# =========================================================

def synthesize_briefing(keyword, news_contents):
    system_prompt = f"""
    You are a Professional News Editor.
    Topic: {keyword}
    
    Task: Create a concise, engaging news briefing (3-6 sentences) based on the provided text.
    
    [STRICT RULES]
    1. ABSOLUTELY NO <think> tags or internal monologue. Output ONLY the final briefing text.
    2. DO NOT say "No specific news". If specific info is missing, assume the keyword is trending due to general popularity and write a generic positive update.
    3. Tone: Professional, Journalistic.
    4. Output: Plain Text.
    """
    
    user_input = "\n\n".join(news_contents)[:4000] 
    return ask_ai_master(system_prompt, user_input)
