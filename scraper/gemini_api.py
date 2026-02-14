# scraper/gemini_api.py
import os
import json
import requests
import time
from dotenv import load_dotenv

# .env 로드 (로컬 실행용)
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("GOOGLE_API_KEY")

def get_best_model():
    """
    사용 가능한 모델을 API로 조회.
    실패하면 안전한 기본 모델 리스트를 반환.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            # 1순위: 1.5-flash (빠르고 저렴)
            for m in models:
                if 'gemini-1.5-flash' in m['name']: return m['name']
            # 2순위: 1.5-pro
            for m in models:
                if 'gemini-1.5-pro' in m['name']: return m['name']
    except Exception as e:
        print(f"   ⚠️ Model List Error: {e}")
    
    # API 조회 실패 시 사용할 안전한 모델명 (하드코딩)
    return "models/gemini-1.5-flash"

def ask_gemini(prompt):
    """AI에게 질문 (404 에러 시 재시도 로직 포함)"""
    if not API_KEY:
        print("🚨 Google API Key is missing!")
        return None

    # 1. 최적 모델 선택
    model_name = get_best_model()
    
    # URL 생성
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        # 2. 요청 전송
        # print(f"   🤖 Asking {model_name}...") # (로그가 너무 많으면 주석 처리)
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # 3. 성공 시 파싱
        if resp.status_code == 200:
            try:
                text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                text = text.replace("```json", "").replace("```", "").strip()
                return json.loads(text)
            except Exception:
                return None

        # 4. [중요] 404 에러 발생 시 (모델명 문제일 수 있음 -> 구형 모델로 재시도)
        elif resp.status_code == 404:
            print(f"   ❌ 404 Error on {model_name}. Retrying with 'gemini-pro'...")
            
            # 비상용 모델 (gemini-pro)로 URL 교체 후 재시도
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"
            resp = requests.post(fallback_url, headers=headers, json=payload, timeout=30)
            
            if resp.status_code == 200:
                text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                text = text.replace("```json", "").replace("```", "").strip()
                return json.loads(text)
            else:
                print(f"   ❌ Retry Failed: {resp.status_code} (Check API Enablement in Google Cloud)")
                return None
        
        else:
            print(f"   ❌ Gemini Error: {resp.status_code} ({resp.text[:50]})")
            return None

    except Exception as e:
        print(f"   ❌ Connection Error: {e}")
        return None
