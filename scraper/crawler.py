import os
import json
import urllib.parse
import urllib.request
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import feedparser 

def get_naver_api_news(keyword):
    """네이버 API 뉴스 검색 (타임아웃 10초)"""
    url = f"https://openapi.naver.com/v1/search/news?query={urllib.parse.quote(keyword)}&display=100&sort=date"
    
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", os.environ.get("NAVER_CLIENT_ID"))
    req.add_header("X-Naver-Client-Secret", os.environ.get("NAVER_CLIENT_SECRET"))
    
    try:
        # print(f"📡 네이버 API 호출 중: {keyword}...")
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
    * 수정사항: Mixed Content 방지를 위해 HTTPS 이미지 강제
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        # 타임아웃 5초 설정
        res = requests.get(link, headers=headers, timeout=5)
        
        if res.status_code != 200:
            return "", None

        soup = BeautifulSoup(res.text, 'html.parser')
        
        # --- 1. 본문 텍스트 추출 ---
        content_area = soup.select_one('#dic_area, #articleBodyContents, .article_view, #articeBody, .news_view, #newsct_article, .article-body')
        
        full_text = ""
        if content_area:
            for s in content_area(['script', 'style', 'iframe', 'button', 'a', 'div.ad']):
                s.decompose()
            full_text = content_area.get_text(separator=' ', strip=True)
            full_text = full_text[:1500]
        else:
            full_text = soup.body.get_text(separator=' ', strip=True)[:1000] if soup.body else ""

        # --- 2. 이미지 추출 (HTTPS 강제) ---
        image_url = None
        
        if content_area:
            imgs = content_area.find_all('img')
            for i in imgs:
                src = i.get('src') or i.get('data-src')
                # http:// 는 버리고 반드시 https:// 로 시작하는 것만 가져옴
                if src and src.startswith('https://'):
                    width = i.get('width')
                    if width and width.isdigit() and int(width) < 200: continue
                    image_url = src
                    break

        if not image_url:
            og = soup.find('meta', property='og:image')
            if og and og.get('content'): 
                candidate = og['content']
                if candidate.startswith('https://'):
                    image_url = candidate

        if image_url:
            bad_keywords = r'logo|icon|button|share|banner|thumb|profile|default|ranking|news_stand|ssl.pstatic.net'
            if re.search(bad_keywords, image_url, re.IGNORECASE): 
                image_url = None

        return full_text, image_url

    except Exception as e:
        return "", None

def get_google_trending_keywords():
    """
    [수정] 구글 트렌드 RSS 수집 (차단 우회 적용)
    - feedparser로 바로 호출하지 않고, requests로 User-Agent 헤더를 달아서 호출
    """
    try:
        url = "https://trends.google.co.kr/trends/trendingsearches/daily/rss?geo=KR"
        
        # 봇 차단 방지를 위한 브라우저 헤더 위장
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 1. requests로 데이터 먼저 가져오기
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # 2. 가져온 텍스트 데이터를 feedparser에 전달
            feed = feedparser.parse(response.text)
            keywords = [entry.title for entry in feed.entries]
            return keywords
        else:
            print(f"⚠️ 구글 트렌드 응답 코드 에러: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ 구글 트렌드 수집 예외 발생: {e}")
        return []
