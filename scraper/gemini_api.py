# scraper/gemini_api.py (디버깅 모드)
import os
import json
import requests
import time
from dotenv import load_dotenv

# .env 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("GOOGLE_API_KEY")

# [핵심] 모델명에서 'models/'를 뺐습니다. (requests가 알아서 처리하도록)
MODEL_NAME = "gemini-1.5-flash"

def ask_gemini(prompt):
    """AI에게 질문 (에러 원문 출력 버전)"""
    if not API_KEY:
        print("🚨 Google API Key is missing!")
        return None
    
    # 공백 제거 (혹시 몰라 코드에서도 한 번 더 제거)
    clean_key = API_KEY.strip()

    # URL 생성 (models/ 접두사 명시)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={clean_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        # 타임아웃 60초
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        
        # 성공 (200 OK)
        if resp.status_code == 200:
            try:
                text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                text = text.replace("```json", "").replace("```", "").strip()
                return json.loads(text)
            except Exception:
                return None

        # [여기가 핵심] 실패 시 구글이 보낸 진짜 메시지 출력
        else:
            print(f"\n   ❌ [CRITICAL ERROR] Status Code: {resp.status_code}")
            print(f"   ❌ URL: {url.replace(clean_key, 'HIDDEN_KEY')}") # 키는 가리고 주소 확인
            print(f"   ❌ GOOGLE SAYS: {resp.text} \n") # <-- 이 메시지가 진짜 원인입니다.
            
            return None

    except Exception as e:
        print(f"   ❌ Connection Error: {e}")
        return None
