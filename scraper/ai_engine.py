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
    
    # [디버깅] 키 확인
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("   [DEBUG] ⚠️ GROQ_API_KEY가 없습니다.")
    
    # Groq 시도
    if groq_key:
        models = get_groq_text_models()
        if not models: print("   [DEBUG] Groq 모델을 찾을 수 없습니다.")
        
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
            except Exception as e:
                print(f"   [DEBUG] Groq 에러 ({model_id}): {e}")
                continue

    # OpenRouter 시도
    if not raw_response:
        or_key = os.getenv("OPENROUTER_API_KEY")
        if not or_key:
            print("   [DEBUG] ⚠️ OPENROUTER_API_KEY가 없습니다.")
        
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
                        timeout=20
                    )
                    if res.status_code == 200:
                        raw_response = res.json()['choices'][0]['message']['content']
                        if raw_response: break
                    else:
                        print(f"   [DEBUG] OpenRouter 에러: {res.status_code} {res.text}")
                except Exception as e:
                    print(f"   [DEBUG] OpenRouter 예외: {e}")
                    continue

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
# 4. [2단계] 키워드 추출
# =========================================================

def extract_top_entities(category, news_text_data):
    system_prompt = f"""
    You are a K-Content Trend Analyst for '{category}'. 
    
    [TASK]
    1. Analyze the provided news titles and summaries.
    2. Extract the most frequently mentioned keywords.
    3. CLASSIFY each keyword into 'person' or 'content'.
    
    [CLASSIFICATION RULES]
    - 'person': Groups (BTS), Singers, Actors, Entertainers.
    - 'content': Song Titles, Drama Titles, Movie Titles, Shows, Places.
    
    [OUTPUT FORMAT]
    - JSON LIST of objects. Example: [{{"keyword": "BTS", "type": "person"}}]
    - Max 40 items.
    """
    
    user_input = news_text_data[:15000]
    
    # [디버깅] AI 호출 직전
    # print(f"   [DEBUG] AI에게 키워드 추출 요청 중... (입력 길이: {len(user_input)})")
    
    raw_result = ask_ai_master(system_prompt, user_input)
    
    # [디버깅] 결과 확인
    if not raw_result:
        print("   [DEBUG] ❌ AI 응답이 비어있습니다.")
    # else:
    #     print(f"   [DEBUG] AI 응답(앞부분): {raw_result[:100]}...")

    parsed = parse_json_result(raw_result)
    
    if not parsed and raw_result:
        print(f"   [DEBUG] ❌ JSON 파싱 실패. 원본: {raw_result[:200]}")

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
# 5. [4단계] AI 브리핑
# =========================================================

def synthesize_briefing(keyword, news_contents):
    system_prompt = f"""
    You are a Professional News Editor. Topic: {keyword}
    [TASK] Write a comprehensive news briefing in ENGLISH (5-20 lines).
    [CRITICAL] NO <think> tags. If data is invalid, output "INVALID_DATA".
    """
    
    user_input = "\n\n".join(news_contents)[:6000] 
    result = ask_ai_master(system_prompt, user_input)
    
    if "INVALID_DATA" in result or len(result) < 50:
        return None
        
    return result
