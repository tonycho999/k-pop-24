import os
import requests
import time
import re
import random
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("GOOGLE_API_KEY")

def ask_gemini_with_search_debug(prompt):
    if not API_KEY: return None, "API_KEY_MISSING"

    # [수정] 진단 정보에서 1순위로 확인되었던 확실한 모델명으로 교체
    model_name = "models/gemini-2.0-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={API_KEY.strip()}"
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search_retrieval": {}}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
    }

    # 최대 2회 시도
    for attempt in range(2):
        try:
            # [안전장치] timeout을 45초로 설정하여 무한 대기(Hang) 방지
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            
            # 할당량 초과(429) 발생 시 즉시 리턴하여 main.py의 랜덤 휴식 유도
            if resp.status_code == 429:
                return None, f"HTTP_429: Rate Limit Exceeded. (Retry in main.py)"

            if resp.status_code != 200:
                return None, f"HTTP_{resp.status_code}: {resp.text}"

            res_json = resp.json()
            
            # 응답 구조 안전하게 추출
            try:
                raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError):
                return None, f"STRUCT_ERR: Response structure changed. {str(res_json)[:200]}"
            
            # 검색 주석 제거
            raw_text = re.sub(r'\[\d+\]', '', raw_text)
            
            # 태그 파싱 로직
            def get_content(tag, text):
                pattern = rf"(?:\*+|#+)?{tag}(?:\*+|#+)?[:\s-]*(.*?)(?=\s*(?:#+|TARGET|HEADLINE|CONTENT|RANKINGS)|$)"
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                return match.group(1).strip() if match else None

            parsed = {
                'target_kr': get_content("TARGET_KR", raw_text),
                'target_en': get_content("TARGET_EN", raw_text),
                'headline': get_content("HEADLINE", raw_text),
                'content': get_content("CONTENT", raw_text),
                'raw_rankings': get_content("RANKINGS", raw_text)
            }

            if parsed['headline'] and parsed['content']:
                return parsed, raw_text
            return None, f"PARSING_FAILED: Missing Tags. Raw: {raw_text[:100]}"

        except requests.exceptions.Timeout:
            print(f"⏰ {model_name} 응답 지연 발생 (시도 {attempt+1})")
            continue 
        except Exception as e:
            return None, f"EXCEPTION: {str(e)}"
            
    return None, "ALL_ATTEMPTS_FAILED_OR_TIMEOUT"
