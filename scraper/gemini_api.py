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
    
    url = f"[https://generativelanguage.googleapis.com/v1beta/models?key=](https://generativelanguage.googleapis.com/v1beta/models?key=){API_KEY.strip()}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            chat_models = [m['name'] for m in models if 'generateContent' in m.get('supportedGenerationMethods', [])]
            
            # 우선순위: 1.5-flash (빠름) -> 2.0 -> Pro
            for m in chat_models:
                if 'gemini-1.5-flash' in m: return m
            for m in chat_models:
                if 'gemini-2.0-flash' in m: return m
            if chat_models: return chat_models[0]
    except:
        pass
    return "models/gemini-1.5-flash"

def extract_json_from_text(text):
    """
    AI가 잡담을 섞어서 보내도 '{' 와 '}' 사이의 JSON만 추출하는 강력한 함수
    """
    try:
        # 1. 가장 바깥쪽 중괄호 찾기
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx : end_idx + 1]
            return json.loads(json_str)
        return None
    except Exception:
        return None

def ask_gemini(prompt):
    """AI에게 질문 (Safety Filter 해제 + JSON 파싱 강화)"""
    if not API_KEY:
        print("🚨 Google API Key is missing!")
        return None

    model_name = get_best_model_name()
    clean_model = model_name.replace("models/", "")
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){clean_model}:generateContent?key={API_KEY.strip()}"
    
    headers = {"Content-Type": "application/json"}
    
    # [핵심 1] 안전 설정 해제 (뉴스는 범죄/사고 내용이 있을 수 있으므로 차단 방지)
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
    ]

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": safety_settings,
        # [핵심 2] JSON 모드 명시 (가능한 모델의 경우)
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            
            # 200 OK
            if resp.status_code == 200:
                try:
                    res_json = resp.json()
                    
                    # AI가 답변을 거부했는지 확인 (Safety Filter 등)
                    if 'candidates' not in res_json or not res_json['candidates']:
                        print(f"   ⚠️ AI returned empty candidate. (Blocked?) Response: {res_json}")
                        return None
                        
                    content_parts = res_json['candidates'][0]['content']['parts']
                    text = content_parts[0]['text']
                    
                    # 1차 시도: 그냥 파싱
                    try:
                        return json.loads(text)
                    except:
                        # 2차 시도: 텍스트 정제 후 파싱
                        cleaned_json = extract_json_from_text(text)
                        if cleaned_json:
                            return cleaned_json
                        else:
                            print(f"   ⚠️ JSON Parsing Failed. Raw Text: {text[:200]}...")
                            return None

                except Exception as e:
                    print(f"   ⚠️ Unexpected Parsing Error: {e}")
                    return None
            
            # 400 Bad Request (JSON Mode 미지원 모델일 경우)
            elif resp.status_code == 400 and "generationConfig" in resp.text:
                print("   🔄 Retrying without JSON Config...")
                del payload["generationConfig"]
                continue
                
            # 429 Too Many Requests
            elif resp.status_code == 429:
                print(f"   ⏳ Rate Limit. Waiting 5s... (Attempt {attempt+1})")
                time.sleep(5)
                continue
                
            else:
                print(f"   ❌ Gemini Error {resp.status_code}: {resp.text[:200]}")
                return None

        except Exception as e:
            print(f"   ⚠️ Connection Error (Attempt {attempt+1}): {e}")
            time.sleep(2)

    return None
