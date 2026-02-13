import os
import sys
import urllib.request
import urllib.parse
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

def get_naver_api_news(keyword, display=10, sort='sim'):
    """
    네이버 뉴스 검색 API 호출
    """
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("⚠️ 네이버 API 키가 설정되지 않았습니다.")
        return []

    try:
        encText = urllib.parse.quote(keyword)
        url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display={display}&start=1&sort={sort}"

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)

        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            data = json.loads(response.read().decode('utf-8'))
            items = []
            for item in data.get('items', []):
                clean_item = {
                    'title': BeautifulSoup(item['title'], 'html.parser').get_text(),
                    'link': item['link'],
                    'description': BeautifulSoup(item['description'], 'html.parser').get_text(),
                    'pubDate': item['pubDate']
                }
                items.append(clean_item)
            return items
        return []
    except Exception as e:
        print(f"⚠️ API 요청 실패: {e}")
        return []

def get_article_data(url, target_keyword=None):
    """
    [Updated] 기사 본문 크롤링 및 키워드 검증
    target_keyword가 본문에 없으면 None을 반환하여 수집 대상에서 제외함
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # 타임아웃 3초 (빠른 처리를 위해)
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code != 200: return None, None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 이미지 추출
        image_url = None
        og_image = soup.find("meta", property="og:image")
        if og_image: image_url = og_image.get("content")
        
        # 2. 본문 추출 (네이버 뉴스 vs 일반)
        content = ""
        if "news.naver.com" in url:
            article_body = soup.find('div', id='dic_area') or soup.find('div', id='articleBodyContents')
            if article_body: content = article_body.get_text(strip=True)
        else:
            paragraphs = soup.find_all('p')
            content = " ".join([p.get_text(strip=True) for p in paragraphs])

        # 내용이 너무 짧으면(광고 등) 무시
        if len(content) < 100: 
            return None, None

        # 🚨 [검증 로직] 본문에 타겟 키워드가 포함되어 있는지 확인
        if target_keyword:
            # 대소문자 무시하고 체크
            if target_keyword.lower() not in content.lower():
                # print(f"      🗑️ [Skip] 본문에 '{target_keyword}' 없음.") # 디버깅용
                return None, None

        return content[:1800], image_url 

    except Exception:
        return None, None
