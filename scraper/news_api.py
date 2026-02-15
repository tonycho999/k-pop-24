import os
import requests
import time
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
API_KEY = os.getenv("PERPLEXITY_API_KEY")

def ask_news_ai(prompt):
    """Perplexity API를 사용하여 3개의 기사 리스트를 추출합니다."""
    if not API_KEY: 
        return None, "API_KEY_MISSING"

    url = "https://api.perplexity.ai/chat/completions"
    
    payload = {
        "model": "sonar-pro", 
        "messages": [
            {
                "role": "system", 
                "content": "당신은 한국의 최신 연예/문화 뉴스를 정확하게 전달하는 전문 기자입니다. ##ARTICLE_START##와 ##ARTICLE_END## 태그를 사용하여 반드시 3개의 뉴스 기사 블록을 작성하세요."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "top_p": 0.9,
        "return_citations": True
    }

    headers = {
        "Authorization": f"Bearer {API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if resp.status_code != 200:
            return None, f"HTTP_{resp.status_code}: {resp.text}"

        res_json = resp.json()
        raw_text = res_json['choices'][0]['message']['content']
        
        # ✅ [핵심 수정] ##ARTICLE_START## 블록 단위로 기사 3개를 분리합니다.
        blocks = re.findall(r"##ARTICLE_START##(.*?)##ARTICLE_END##", raw_text, re.DOTALL | re.IGNORECASE)
        
        articles = []
        
        # 개별 블록 내에서 태그 정보를 추출하는 함수
        def extract_tag(tag, text):
            pattern = rf"##{tag}##\s*(.*?)(?=\s*##|$)"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else None

        for block in blocks:
            article_data = {
                'target_kr': extract_tag("TARGET_KR", block),
                'target_en': extract_tag("TARGET_EN", block),
                'headline': extract_tag("HEADLINE", block),
                'content': extract_tag("CONTENT", block)
            }
            # 필수 데이터가 있는 경우에만 리스트에 추가
            if article_data['headline'] and article_data['content']:
                articles.append(article_data)

        # 랭킹 데이터는 전체 원문에서 별도로 추출 (RANKINGS 태그 이후 끝까지)
        raw_rankings = None
        rankings_match = re.search(r"##RANKINGS##\s*(.*)", raw_text, re.DOTALL | re.IGNORECASE)
        if rankings_match:
            raw_rankings = rankings_match.group(1).strip()

        # ✅ 파싱된 기사 리스트와 원문을 함께 반환합니다.
        if len(articles) > 0:
            return articles, raw_text
            
        return None, f"PARSING_FAILED: 기사 블록을 찾을 수 없습니다. 원문: {raw_text[:200]}"

    except Exception as e:
        return None, f"EXCEPTION: {str(e)}"
