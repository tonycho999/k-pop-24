# scraper/gemini_api.py
import os
import json
import requests
import time
import re
from dotenv import load_dotenv

# .env 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("GOOGLE_API_KEY")

def get_best_model_name():
    """사용 가능한 최신 모델 자동 탐색"""
    if not API_KEY: return "models/gemini-1.5-flash"
    
    # [수정] URL 공백 제거 안전장치
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY.strip()}"
    
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            chat_models = [m['name'] for m in models if 'generateContent' in m.get('supportedGenerationMethods', [])]
            
            # 우선순위: 1.5-flash -> 2.0 -> Pro
            for m in chat_models:
                if 'gemini-1.5-flash' in m: return m
            for m in chat_models:
                if 'gemini-2.0-flash' in m: return m
            if chat_models: return chat_models[0]
    except:
        pass
    # 기본값 반환 (공백 없이 깔끔하게)
    return "models/gemini-1.5-flash"

def extract_json_from_text(text):
    """AI 답변에서 JSON만 추출"""
    try:
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            return json.loads(text[start_idx : end_idx + 1])
        return None
    except:
        return None

def ask_gemini(prompt):
    """AI에게 질문 (URL 무결성 검사 + 안전 필터 해제)"""
    if not API_KEY:
        print("🚨 Google API Key is missing!")
        return None

    # 1. 모델명 가져오기 및 공백 제거
    model_name = get_best_model_name()
    if not model_name: model_name = "models/gemini-1.5-flash"
    
    # 2. URL 조립 (매우 중요: 모든 변수에 .strip() 적용)
    clean_model = model_name.replace("models/", "").strip()
    clean_key = API_KEY.strip()
    
    # f-string 안에 공백이 들어가지 않도록 주의
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={clean_key}"

    # [디버깅] URL 확인용 로그 (키는 가림)
    masked_url = url.replace(clean_key, "HIDDEN_KEY")
    # print(f"   ℹ️ Request URL: {masked_url}") 

    headers = {"Content-Type": "application/json"}
    
    # 안전 설정 (차단 방지)
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": safety_settings,
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    for attempt in range(3):
        try:
            # 타임아웃 60초
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if resp.status_code == 200:
                try:
                    res_json = resp.json()
                    if 'candidates' not in res_json or not res_json['candidates']:
                        return None
                    
                    text = res_json['candidates'][0]['content']['parts'][0]['text']
                    
                    # 1. 바로 파싱 시도
                    try:
                        return json.loads(text)
                    except:
                        # 2. 추출 후 파싱 시도
                        return extract_json_from_text(text)

                except Exception:
                    return None
            
            elif resp.status_code == 400 and "generationConfig" in resp.text:
                # JSON 모드 미지원 시 재시도
                del payload["generationConfig"]
                continue
                
            elif resp.status_code in [429, 500, 502, 503]:
                time.sleep(2)
                continue
                
            else:
                print(f"   ❌ Gemini Error {resp.status_code}: {resp.text[:100]}")
                return None

        except Exception as e:
            # 여기서 e를 출력하면 'No connection adapters...'가 나옴
            print(f"   ⚠️ Connection Error (Attempt {attempt+1}): {e}")
            print(f"      (URL was: {masked_url})") # URL 모양 확인
            time.sleep(2)

    return None
