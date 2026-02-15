import os
import requests
import time
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("GOOGLE_API_KEY")

def ask_gemini_with_search(prompt):
    if not API_KEY:
        print("🚨 Google API Key missing")
        return None

    # 전문 프로그래머의 팁: 최신 모델인 gemini-1.5-flash를 유지하되, 
    # AI가 형식이 아닌 '내용'에 집중하도록 온도를 살짝 조절합니다.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY.strip()}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search_retrieval": {}}],
        "generationConfig": {
            "temperature": 0.7, # 기사의 질을 위해 창의성을 조금 부여합니다.
            "topP": 0.9
        }
    }

    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                res_json = resp.json()
                # AI가 생성한 원문 텍스트 전체를 가져옵니다.
                raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
                
                # 1. 구글 검색 주석([1], [2] 등)을 미리 제거하여 가독성 확보
                raw_text = re.sub(r'\[\d+\]', '', raw_text)
                
                # 2. 태그 기반 파싱 (JSON 대신 태그를 찾아 딕셔너리로 변환)
                parsed_data = {}
                
                # 정규표현식으로 ##태그## 사이의 내용을 추출합니다.
                def extract_tag(tag, text):
                    pattern = f"##{tag}##(.*?)##"
                    match = re.search(pattern, text, re.DOTALL)
                    if not match:
                        # 마지막 태그일 경우 뒤에 ##이 없을 수 있으므로 재시도
                        pattern = f"##{tag}##(.*)"
                        match = re.search(pattern, text, re.DOTALL)
                    return match.group(1).strip() if match else None

                try:
                    # 필수 데이터들을 태그 기반으로 수집
                    parsed_data['target_kr'] = extract_tag("TARGET_KR", raw_text)
                    parsed_data['target_en'] = extract_tag("TARGET_EN", raw_text)
                    parsed_data['headline'] = extract_tag("HEADLINE", raw_text)
                    parsed_data['content'] = extract_tag("CONTENT", raw_text)
                    parsed_data['raw_rankings'] = extract_tag("RANKINGS", raw_text)

                    # 필수 데이터가 하나라도 있으면 성공으로 간주하고 반환
                    if parsed_data['headline'] and parsed_data['content']:
                        return parsed_data
                    else:
                        print(f"⚠️ 태그 추출 실패. 원문: {raw_text[:100]}...")
                except Exception as parse_err:
                    print(f"❌ 텍스트 파싱 중 오류: {parse_err}")

            time.sleep(5)
        except Exception as e:
            print(f"⚠️ 시도 {attempt+1} 실패: {e}")
    return None
