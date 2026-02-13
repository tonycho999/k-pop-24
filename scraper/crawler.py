import os
import json
import urllib.parse
import urllib.request
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import feedparser # pip install feedparser 필요

def get_naver_api_news(keyword):
    """네이버 API 뉴스 검색 (타임아웃 10초)"""
    url = f"https://openapi.naver.com/v1/search/news?query={urllib.parse.quote(keyword)}&display=100&sort=date"
    
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", os.environ.get("NAVER_CLIENT_ID"))
    req.add_header("X-Naver-Client-Secret", os.environ.get("NAVER_CLIENT_SECRET"))
    
    try:
        print(f"📡 네이버 API 호출 중: {keyword}...")
        res = urllib.request.urlopen(req, timeout=10) 
        items = json.loads(res.read().decode('utf-8')).get('items', [])
        
        valid_items = []
        now = datetime.now()
        threshold = now - timedelta(hours=24)

        for item in items:
            try:
                pub_date = parsedate_to_datetime(item['pubDate']).replace(tzinfo=None)
                if pub_date < threshold:
                    continue
                item['published_at'] = pub_date
                valid_items.append(item)
            except:
                continue

        return valid_items

    except Exception as e:
        print(f"❌ 네이버 API 에러 ({keyword}): {e}")
        return []

def get_article_data(link):
    """
    [업그레이드] 기사 본문(1,500자) 및 이미지 통합 추출 함수
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        # 타임아웃 5초 설정
        res = requests.get(link, headers=headers, timeout=5)
        
        if res.status_code != 200:
            return "", None

        soup = BeautifulSoup(res.text, 'html.parser')
        
        # --- 1. 본문 텍스트 추출 (재료 확보) ---
        # 주요 뉴스 사이트들의 본문 영역 태그 모음
        content_area = soup.select_one('#dic_area, #articleBodyContents, .article_view, #articeBody, .news_view, #newsct_article, .article-body')
        
        full_text = ""
        if content_area:
            # 불필요한 태그 제거 (스크립트, 스타일, 광고 버튼 등)
            for s in content_area(['script', 'style', 'iframe', 'button', 'a', 'div.ad']):
                s.decompose()
            full_text = content_area.get_text(separator=' ', strip=True)
            # [핵심] 요약 품질을 위해 최대 1,500자까지 확보
            full_text = full_text[:1500]
        else:
            # 본문 태그를 못 찾았을 경우, body 전체에서 텍스트만이라도 긁어오기 시도 (최후의 수단)
            full_text = soup.body.get_text(separator=' ', strip=True)[:1000] if soup.body else ""

        # --- 2. 이미지 추출 ---
        image_url = None
        
        # 본문 영역 안의 이미지를 1순위로 찾음
        if content_area:
            imgs = content_area.find_all('img')
            for i in imgs:
                src = i.get('src') or i.get('data-src')
                if src and 'http' in src:
                    # 너무 작은 아이콘/배너 제외
                    width = i.get('width')
                    if width and width.isdigit() and int(width) < 200: continue
                    image_url = src
                    break

        # 본문에 없으면 메타 태그(og:image) 확인
        if not image_url:
            og = soup.find('meta', property='og:image')
            if og and og.get('content'): 
                image_url = og['content']

        # 불량 이미지 키워드 필터링
        if image_url:
            bad_keywords = r'logo|icon|button|share|banner|thumb|profile|default|ranking|news_stand|ssl.pstatic.net'
            if re.search(bad_keywords, image_url, re.IGNORECASE): 
                image_url = None

        return full_text, image_url

    except Exception as e:
        print(f"    ⚠️ 크롤링 실패 ({link[:30]}...): {e}")
        return "", None

def get_google_trending_keywords():
    """(미래 사용용) 구글 트렌드 RSS 수집"""
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"
        feed = feedparser.parse(url)
        keywords = [entry.title for entry in feed.entries]
        return keywords
    except Exception as e:
        # print(f"❌ 구글 트렌드 수집 실패: {e}")
        return []
