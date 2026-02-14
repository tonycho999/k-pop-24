# scraper/gemini_api.py
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("GOOGLE_API_KEY")

def get_best_model():
    """사용 가능한 최신 모델 찾기"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            # Pro -> Flash 순 선호
            for m in models:
                if 'generateContent' in m['supportedGenerationMethods'] and 'gemini-1.5-pro' in m['name']:
                    return m['name']
            for m in models:
                if 'generateContent' in m['supportedGenerationMethods'] and 'gemini-1.5-flash' in m['name']:
                    return m['name']
    except:
        pass
    return "models/gemini-1.5-flash"

def ask_gemini(prompt):
    """AI 호출 및 JSON 파싱"""
    if not API_KEY:
        print("🚨 Google API Key missing!")
        return None

    model_name = get_best_model()
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            try:
                text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                # 마크다운 제거 및 JSON 변환
                text = text.replace("```json", "").replace("```", "").strip()
                return json.loads(text)
            except Exception:
                # JSON 파싱 실패 시 None 반환
                return None
        else:
            print(f"   ❌ Gemini API Error: {resp.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Gemini Connection Error: {e}")
        return None
