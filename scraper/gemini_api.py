# scraper/gemini_api.py
import os
import json
import requests
import time
from dotenv import load_dotenv

# .env 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("GOOGLE_API_KEY")

def get_working_model_name():
    """
    [핵심] 구글에게 '나 지금 무슨 모델 쓸 수 있니?'라고 물어보고
    가장 적절한 모델의 '정확한 이름'을 가져옵니다.
    """
    if not API_KEY: return None

    # 1. 모델 목록 조회 URL
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY.strip()}"
    
    try:
        resp = requests.get(url, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            models = data.get('models', [])
            
            # 로그에 목록 출력 (디버깅용 - 나중에 로그 확인해보세요)
            print(f"   📋 Available Models: {[m['name'] for m in models]}")

            # 2. 우선순위대로 모델 찾기
            # 'generateContent' 기능을 지원하는 모델만 필터링
            chat_models = [m for m in models if 'generateContent' in m.get('supportedGenerationMethods', [])]
            
            # 1순위: 1.5-flash (정확한 버전명 찾기)
            for m in chat_models:
                if 'gemini-1.5-flash' in m['name']:
                    # "models/gemini-1.5-flash-001" 같은 풀네임 반환
                    return m['name'] 
            
            # 2순위: 1.5-pro
            for m in chat_models:
                if 'gemini-1.5-pro' in m['name']:
                    return m['name']
            
            # 3순위: 아무거나 (1.0 pro 등)
            if chat_models:
                return chat_models[0]['name']
                
        else:
            print(f"   ⚠️ ListModels Failed: {resp.status_code} {resp.text}")
            
    except Exception as e:
        print(f"   ⚠️ Model Discovery Error: {e}")

    # 실패 시 최후의 수단 (가장 옛날 모델이라도 시도)
    return "models/gemini-pro"

def ask_gemini(prompt):
    """AI에게 질문 (자동 모델 선택)"""
    if not API_KEY:
        print("🚨 Google API Key is missing!")
        return None

    # [1] 쓸 수 있는 모델을 자동으로 찾아옴
    model_name = get_working_model_name()
    print(f"   🤖 Selected Model: {model_name}") # 로그에서 확인 가능

    # [2] URL 생성
    # model_name에는 이미 'models/'가 포함되어 있을 수 있음.
    # 중복 방지를 위해 models/ 제거 후 다시 조합
    clean_model_name = model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={API_KEY.strip()}"
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        # 타임아웃 60초
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if resp.status_code == 200:
            try:
                text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                text = text.replace("```json", "").replace("```", "").strip()
                return json.loads(text)
            except Exception:
                return None
        
        else:
            print(f"   ❌ Gemini Error {resp.status_code}: {resp.text[:200]}")
            return None

    except Exception as e:
        print(f"   ❌ Connection Error: {e}")
        return None
