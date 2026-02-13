import os
import json
import re
import requests
from groq import Groq

# =========================================================
# 1. 모델 선택 로직 (기존 유지)
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

# =========================================================
# 2. AI 답변 정제기 (<think> 삭제 및 JSON 세탁)
# =========================================================

def clean_ai_response(text):
    if not text: return ""
    # <think> 태그 제거 (가장 중요)
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
# 4. [2단계] 키워드 추출 및 정체 분류
# =========================================================

def extract_top_entities(category, news_text_data):
    """
    뉴스 제목+요약을 분석하여 키워드를 추출하고,
    'person'(사람/그룹) vs 'content'(작품/곡)으로 분류함.
    """
    
    system_prompt = f"""
    You are a K-Content Trend Analyst for '{category}'. 
    
    [TASK]
    1. Analyze the provided news titles and summaries.
    2. Extract the most frequently mentioned keywords (Singers, Groups, Actors, Songs, Dramas, Movies, Shows, Places).
    3. CLASSIFY each keyword into 'person' or 'content'.
    
    [CLASSIFICATION RULES]
    - 'person': Groups (BTS, IVE), Singers (IU), Actors (Kim Soo-hyun), Entertainers (Yoo Jae-suk).
    - 'content': Song Titles (Hype Boy), Drama Titles (The Glory), Movie Titles (Exhuma), TV Shows (Running Man), Places, Events.
    
    [OUTPUT FORMAT]
    - JSON LIST of objects.
    - Example: [{{"keyword": "BTS", "type": "person"}}, {{"keyword": "Seven", "type": "content"}}]
    - Max 40 items.
    - Translate Korean names to English.
    """
    
    # 텍스트가 너무 길면 자름
    user_input = news_text_data[:15000]
    
    raw_result = ask_ai_master(system_prompt, user_input)
    parsed = parse_json_result(raw_result)
    
    if isinstance(parsed, list):
        # 중복 제거
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
# 5. [4단계] AI 브리핑 생성 (조건 미달 시 폐기)
# =========================================================

def synthesize_briefing(keyword, news_contents):
    system_prompt = f"""
    You are a Professional News Editor.
    Topic: {keyword}
    
    [TASK]
    Write a comprehensive news briefing in ENGLISH based on the provided text.
    
    [CRITICAL RULES]
    1. Length: Minimum 5 lines, Maximum 20 lines.
    2. Format: Plain text paragraphs.
    3. NO <think> tags.
    4. DATA CHECK: If the provided text has no meaningful information about '{keyword}' or says "no specific news",
       OUTPUT EXACTLY THIS SINGLE WORD: "INVALID_DATA"
       (Do not write "No specific news", just write "INVALID_DATA").
    """
    
    user_input = "\n\n".join(news_contents)[:6000] 
    result = ask_ai_master(system_prompt, user_input)
    
    # AI가 데이터 부족 판정을 내렸거나, 결과가 너무 짧으면 무효 처리
    if "INVALID_DATA" in result or len(result) < 50:
        return None
        
    return result
