# scraper/gemini_api.py
import os
import json
import requests
import time
from dotenv import load_dotenv

# .env 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("GOOGLE_API_KEY")

def get_best_model_name():
    """
    구글 API에서 현재 사용 가능한 최신 Flash 모델을 자동으로 찾아냅니다.
    (1.5, 2.0, 2.5 등 버전이 바뀌어도 알아서 적응함)
    """
    if not API_KEY: return "models/gemini-2.5-flash"

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY.strip()}"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get('models', [])
            
            # 'generateContent' 기능이 있는 모델만 필터링
            chat_models = [m['name'] for m in models if 'generateContent' in m.get('supportedGenerationMethods', [])]
            
            # 1순위: 2.5-flash (최신)
            for m in chat_models:
                if 'gemini-2.5-flash' in m: return m
            
            # 2순위: 2.0-flash
            for m in chat_models:
                if 'gemini-2.0-flash' in m: return m

            # 3순위: 구형 flash
            for m in chat_models:
                if 'flash' in m: return m
            
            # 4순위: 아무거나 (Pro 등)
            if chat_models: return chat_models[0]
            
    except Exception:
        pass

    # API 조회 실패 시 안전한 기본값 (로그 기반 최신 모델)
    return "models/gemini-2.5-flash"

def ask_gemini(prompt):
    """AI에게 질문 (최종)"""
    if not API_KEY:
        print("🚨 Google API Key is missing!")
        return None

    # 1. 모델 자동 선택
    model_name = get_best_model_name()
    
    # 2. URL 생성 (models/ 중복 방지 처리)
    clean_model = model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={API_KEY.strip()}"
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    # 재시도 로직 (최대 3회)
    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if resp.status_code == 200:
                try:
                    text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                    text = text.replace("```json", "").replace("```", "").strip()
                    return json.loads(text)
                except:
                    return None
            
            # 429(Too Many Requests) 또는 500번대 에러 시 잠시 대기 후 재시도
            elif resp.status_code in [429, 500, 502, 503]:
                time.sleep(2)
                continue
            
            else:
                print(f"   ❌ Gemini Error {resp.status_code}: {resp.text[:100]}")
                return None

        except Exception as e:
            print(f"   ⚠️ Connection Error (Attempt {attempt+1}): {e}")
            time.sleep(2)

    return None
