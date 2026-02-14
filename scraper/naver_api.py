# scraper/naver_api.py
import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# [수정] 함수 정의에 sort='sim' 인자를 추가하여 
# 인자가 전달되지 않을 때는 정확도순(sim), 전달될 때는 최신순(date)으로 작동하게 합니다.
def search_news_api(keyword, display=10, sort='sim'):
    """네이버 뉴스 검색 API"""
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
        "sort": sort  # 여기서 인자로 받은 sort 값을 네이버 API에 전달합니다.
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
    """뉴스 본문 및 이미지 추출"""
    if "news.naver.com" not in url:
        return {"text": "", "image": ""}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        time.sleep(0.3) 
        resp = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')

        content = ""
        # 주요 뉴스 본문 셀렉터
        for selector in ["#dic_area", "#articeBody", "#newsEndContents", ".go_trans._article_content"]:
            el = soup.select_one(selector)
            if el:
                for tag in el(['script', 'style', 'a', 'iframe', 'span']):
                    tag.decompose()
                content = el.get_text(strip=True)
                break
        
        image_url = ""
        og_img = soup.select_one('meta[property="og:image"]')
        if og_img:
            image_url = og_img.get('content', '')

        return {"text": content, "image": image_url}

    except Exception:
        return {"text": "", "image": ""}
