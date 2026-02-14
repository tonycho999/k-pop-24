import os
import json
import re
import requests
from groq import Groq

# =========================================================
# 1. 모델 선택 로직 (Groq 전용)
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
        # 70B(고성능) 모델 우선 정렬
        valid_models.sort(key=lambda x: '70b' in x, reverse=True) 
        return valid_models
    except: return []

# =========================================================
# 2. AI 답변 정제기 및 호출 마스터
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
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key: return ""
    
    models = get_groq_text_models()
    client = Groq(api_key=groq_key)
    
    for model_id in models:
        try:
            completion = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
                temperature=0.3
            )
            res = completion.choices[0].message.content.strip()
            if res: return clean_ai_response(res)
        except:
            continue
    return ""

def parse_json_result(text):
    if not text: return []
    try: return json.loads(text)
    except: pass
    try:
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match: return json.loads(match.group(0))
    except: pass
    return []

# =========================================================
# 3. [핵심] 카테고리별 엄격 분류 (Strict Mode)
# =========================================================

def extract_top_entities(category, news_text_data):
    # 카테고리별 배타적 규칙 설정 (사용자 요청 반영)
    specific_rule = ""
    if category == 'K-Drama':
        specific_rule = """
        [STRICT K-DRAMA MODE]
        1. 'content' MUST be a REAL Drama/Series Title (e.g. 'Squid Game').
        2. DO NOT extract K-Pop singers or generic terms like 'K-Pop', 'Music', 'News'.
        3. If no actual Drama Title is found, return an EMPTY LIST [].
        """
    elif category == 'K-Movie':
        specific_rule = """
        [STRICT K-MOVIE MODE]
        1. 'content' MUST be a REAL Movie Title (e.g. 'Parasite').
        2. DO NOT include TV Shows or Dramas.
        """
    elif category == 'K-Pop':
        specific_rule = """
        [STRICT K-POP MODE]
        1. 'content' MUST be a Song Title, Album, or Group Name.
        2. DO NOT include Movie or Drama titles.
        """
    elif category == 'K-Culture':
        specific_rule = """
        [STRICT K-CULTURE MODE]
        1. 'content' MUST be Food, Place, or Trend items.
        2. EXCLUDE all actors, singers, and corporate PR news.
        """

    system_prompt = f"""
    You are an expert K-Content Analyst for '{category}'. 
    [TASK] Extract keywords ONLY belonging to '{category}'.
    
    {specific_rule}
    
    [CLASSIFICATION TYPES]
    1. 'content': The ACTUAL TITLE of the work (Drama, Movie, Song) belonging ONLY to '{category}'.
    2. 'person': Names of Humans (Actors, Singers) relevant to '{category}'.

    [OUTPUT FORMAT]
    - Return a JSON LIST of objects: [{{ "keyword": "Name", "type": "content" }}]
    - Translate Korean titles to English.
    - If no relevant keywords for '{category}' exist, return [].
    """
    
    # 유료 버전의 넓은 컨텍스트 활용 (20,000자 수용)
    user_input = news_text_data[:20000] 
    raw_result = ask_ai_master(system_prompt, user_input)
    parsed = parse_json_result(raw_result)
    
    # 데이터 정제 (중복 제거 및 타입 필터링)
    if isinstance(parsed, list):
        seen = set()
        unique_list = []
        for item in parsed:
            if isinstance(item, dict) and 'keyword' in item and 'type' in item:
                kw = item['keyword']
                k_type = item['type'].lower()
                if k_type in ['content', 'person'] and kw not in seen:
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
    [CRITICAL] NO <think> tags. If data is invalid, output "INVALID_DATA".
    """
    
    # 기사 내용도 최대 40,000자까지 분석하도록 확장
    user_input = "\n\n".join(news_contents)[:40000] 
    result = ask_ai_master(system_prompt, user_input)
    
    if not result or "INVALID_DATA" in result or len(result) < 50:
        return None
        
    return result
