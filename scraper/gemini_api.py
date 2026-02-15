import os
import json
import requests
import time
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("GOOGLE_API_KEY")

def ask_gemini_with_search(prompt):
    """구글 검색(Grounding)을 사용하여 질문하고 JSON 결과를 반환"""
    if not API_KEY:
        print("🚨 API Key missing")
        return None

    # Grounding은 1.5-flash 모델이 속도와 정확도 면에서 효율적입니다.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY.strip()}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search_retrieval": {}}], # 구글 검색 활성화
        "generationConfig": {
            "temperature": 0.1 # 사실 기반 응답을 위해 낮게 설정
        }
    }

    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=90)
            if resp.status_code == 200:
                res_json = resp.json()
                if 'candidates' in res_json:
                    text = res_json['candidates'][0]['content']['parts'][0]['text']
                    
                    # 정규표현식으로 JSON 블록만 추출
                    match = re.search(r'(\{.*\})', text, re.DOTALL)
                    if match:
                        clean_json = re.sub(r'[\x00-\x1F\x7F]', '', match.group(1))
                        return json.loads(clean_json)
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed: {e}")
    return None
