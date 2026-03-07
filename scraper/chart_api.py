import os
import json
import requests
import pytz
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from google import genai
from google.genai import types
from model_manager import ModelManager 

class ChartEngine:
    def __init__(self, db):
        self.db = db
        self.naver_client_id = os.environ.get("NAVER_CLIENT_ID")
        self.naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET")

        # 💡 닐슨코리아는 프록시가 없으면 100% 차단당합니다.
        self.proxy_host = os.environ.get("PROXY_HOST", "unblocker.iproyal.com")
        self.proxy_port = os.environ.get("PROXY_PORT", "12323")
        self.proxy_user = os.environ.get("PROXY_USER")
        self.proxy_pass = os.environ.get("PROXY_PASS")
        
        if self.proxy_user and self.proxy_pass:
            self.proxies = {
                "http": f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}",
                "https": f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}"
            }
        else:
            self.proxies = None

        self.gemini_key = os.environ.get("GEMINI_API_KEY")

        if self.gemini_key:
            temp_client = genai.Client(api_key=self.gemini_key)
            manager = ModelManager(client=temp_client, provider="gemini")
            self.model_name = manager.get_best_model()
            if not self.model_name:
                self.model_name = "gemini-2.5-flash"
        else:
            self.model_name = None

    def get_top10_chart(self, category):
        print(f"\n📊 --- Processing {category} (ABSOLUTE LATEST) ---", flush=True)

        if category == "k-actor":
            raw_context = self._scrape_naver_news_api("배우")
            source_type = "Naver News Mention Count"
        elif category == "k-pop":
            raw_context = self._scrape_bugs_realtime()
            source_type = "Bugs Music REAL-TIME Chart"
        elif category == "k-entertain":
            # 💡 [핵심] 닐슨코리아 공식 데이터로 교체
            raw_context = self._scrape_nielsen_ratings()
            source_type = "Nielsen Korea Official Ratings"
        elif category == "k-culture":
            raw_context = self._scrape_naver_news_api("핫플레이스")
            source_type = "Naver Realtime Viral Trends"
        else:
            raw_context = None
            source_type = "Unknown"

        if not raw_context:
            print(f"⚠️ [Skip] Valid real-time data not found for {category}.", flush=True)
            return json.dumps({"top10": []})

        return self._process_with_gemini(category, context=raw_context, source_type=source_type)

    def _scrape_nielsen_ratings(self):
        # 지상파, 종편, 케이블 페이지를 순회하며 수집
        urls = [
            "https://www.nielsenkorea.co.kr/tv_terrestrial_day.asp", # 지상파
            "https://www.nielsenkorea.co.kr/tv_terrestrial_day.asp?menu=Tit_1&sub_menu=2_1", # 종편
            "https://www.nielsenkorea.co.kr/tv_terrestrial_day.asp?menu=Tit_1&sub_menu=3_1"  # 케이블
        ]
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        combined_ratings = ""

        try:
            for url in urls:
                res = None
                if self.proxies:
                    res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=15)
                else:
                    res = requests.get(url, headers=headers, verify=False, timeout=15)
                
                # 닐슨은 EUC-KR 인코딩을 사용함
                res.encoding = 'euc-kr'
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # 시청률 테이블 추출
                tables = soup.select('table.정렬') # 닐슨코리아의 고유 테이블 클래스
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            title = cols[1].get_text(strip=True)
                            rating = cols[2].get_text(strip=True)
                            if title and rating and title != '프로그램명':
                                combined_ratings += f"Program: {title}, Rating: {rating}\n"
            
            return combined_ratings if combined_ratings else None
        except Exception as e:
            print(f"  ❌ Nielsen Scraping Error: {e}")
            return None

    def _scrape_naver_news_api(self, query):
        if not self.naver_client_id: return None
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_client_id, "X-Naver-Client-Secret": self.naver_client_secret}
        params = {"query": query, "display": 100, "sort": "date"}
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            res.raise_for_status()
            news_items = res.json().get("items", [])
            now_utc = datetime.now(timezone.utc)
            combined_text = ""
            for item in news_items:
                pub_date = parsedate_to_datetime(item['pubDate'])
                if now_utc - pub_date > timedelta(hours=24): continue
                title = BeautifulSoup(item['title'], 'html.parser').text
                desc = BeautifulSoup(item['description'], 'html.parser').text
                combined_text += f"- {title}: {desc}\n"
            return combined_text if combined_text else None
        except Exception as e:
            print(f"  ❌ Naver API Error for '{query}': {e}")
            return None

    def _scrape_bugs_realtime(self):
        url = "https://music.bugs.co.kr/chart"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            res = None
            if self.proxies:
                res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=10)
            else:
                res = requests.get(url, headers=headers, verify=False, timeout=10)

            soup = BeautifulSoup(res.text, 'html.parser')
            titles = soup.select('p.title a')
            artists = soup.select('p.artist a:nth-of-type(1)')
            if not titles or not artists: return None
            
            context = ""
            for i in range(min(15, len(titles))):
                context += f"- Rank {i+1}: {titles[i].text.strip()} by {artists[i].text.strip()}\n"
            return context
        except Exception as e:
            print(f"  ❌ Bugs Chart Error: {e}")
            return None

    def _process_with_gemini(self, category, context, source_type):
        if not self.gemini_key or not self.model_name:
            return json.dumps({"top10": []})

        korea_tz = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S KST')
        
        special_rule = ""
        if category == "k-actor":
            special_rule = "Identify the REAL ACTORS mentioned most frequently. DO NOT include character names. Output ONLY real actor names."
        elif category == "k-culture":
            special_rule = "Extract the most viral trends, foods, or memes currently happening in Korea."
        elif category == "k-pop":
            special_rule = "Output the Song Title and Singer Name."
        elif category == "k-entertain":
            # 💡 시청률 데이터를 기반으로 예능 랭킹을 매기도록 룰 강화
            special_rule = "The source data is from Nielsen Korea. Identify the most popular Variety Shows (Entertain) and their ratings. Ignore news or dramas. List the TOP 10 Variety Shows by rating."

        prompt = f"""
        Current Date & Time in Korea: {now_kst}.
        Task: Create a Top 10 ranking chart for '{category}'.
        
        Source Data ({source_type}):
        {context}
        
        CRITICAL RULES:
        1. Base your rankings ONLY on the provided source text. {special_rule}
        2. EXCLUDE OUTDATED DATA.
        3. Extract up to 10 items. If irrelevant, return: {{ "top10": [] }}
        4. Translate all Korean titles/names naturally into English.
        5. 'info' MUST be a concise factual description (e.g., "Rating: 15.2%").
        6. Format strictly as JSON.
        
        Required JSON Structure:
        {{ "top10": [ {{ "rank": 1, "title": "English Target Name", "info": "Factual description" }} ] }}
        """

        try:
            print(f"  > AI is counting and ranking data for {category}...", flush=True)
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"  ⚠️ Gemini Error: {e}", flush=True)
            return json.dumps({"top10": []})
