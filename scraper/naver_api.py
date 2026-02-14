import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# .env 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

def search_news_api(keyword, display=10, sort='sim'):
    """네이버 뉴스 검색 API (정렬 옵션 포함)"""
    if not CLIENT_ID or not CLIENT_SECRET:
        print(f"   🚨 [Naver API Error] Client ID or Secret is MISSING.")
        return []

    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {
        "X-Naver-Client-Id": CLIENT_ID.strip(), 
        "X-Naver-Client-Secret": CLIENT_SECRET.strip()
    }
    
    params = {
        "query": keyword, 
        "display": display, 
        "sort": sort 
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        
        if resp.status_code == 200:
            items = resp.json().get('items', [])
            return items
        else:
            print(f"   🚨 [Naver API Fail] Status: {resp.status_code}")
            return []
            
    except Exception as e:
        print(f"   🚨 [Naver Connection Error] {e}")
        return []

def crawl_article(url):
    """뉴스 본문 및 HTTPS 이미지 추출 필터링 강화"""
    if "news.naver.com" not in url:
        return {"text": "", "image": ""}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        time.sleep(0.3) 
        resp = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 1. 뉴스 본문 추출
        content = ""
        for selector in ["#dic_area", "#articeBody", "#newsEndContents", ".go_trans._article_content"]:
            el = soup.select_one(selector)
            if el:
                for tag in el(['script', 'style', 'a', 'iframe', 'span']):
                    tag.decompose()
                content = el.get_text(strip=True)
                break
        
        # 2. 이미지 추출 및 HTTPS 필터링 강화
        image_url = ""
        og_img = soup.select_one('meta[property="og:image"]')
        if og_img:
            temp_url = og_img.get('content', '').strip()
            
            # [필터링 강화] 반드시 https://로 시작하는 경우만 허용
            if temp_url.startswith("https://"):
                image_url = temp_url
            else:
                # http:// 이거나 프로토콜이 없는 경우 로깅 및 제외
                image_url = ""

        return {"text": content, "image": image_url}

    except Exception:
        return {"text": "", "image": ""}
