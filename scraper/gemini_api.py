import os
import requests
import time
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("GOOGLE_API_KEY")

def ask_gemini_with_search_debug(prompt):
    if not API_KEY: return None, "API_KEY_MISSING"

    # [수정] 가장 안정적인 v1 버전 주소로 변경
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY.strip()}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search_retrieval": {}}], # 구글 검색 도구 사용
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048 # 응답 길이 보장
        }
    }

    for attempt in range(2): # 재시도 횟수
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            
            # 404 에러 등이 발생했을 때 원인을 파악하기 위해 로그 강화
            if resp.status_code != 200:
                error_detail = f"HTTP_{resp.status_code}: {resp.text}"
                print(f"🚨 API 호출 실패: {error_detail}")
                return None, error_detail

            res_json = resp.json()
            raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
            
            # [기존과 동일한 태그 파싱 로직]
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
            return None, raw_text

        except Exception as e:
            time.sleep(5)
            last_err = f"EXCEPTION: {str(e)}"
            
    return None, last_err
