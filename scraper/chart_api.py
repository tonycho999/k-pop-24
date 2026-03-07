import os
import json
import requests
import time
import pytz
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import urllib.parse
from email.utils import parsedate_to_datetime

from google import genai
from google.genai import types
from model_manager import ModelManager 

class ChartEngine:
    def __init__(self, db):
        self.db = db
        self.naver_client_id = os.environ.get("NAVER_CLIENT_ID")
        self.naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET")

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
            raw_context = self._scrape_recent_actor_news()
            source_type = "Naver News Mention Count (Last 24 Hours)"
        elif category == "k-pop":
            raw_context = self._scrape_bugs_realtime()
            source_type = "Bugs Music REAL-TIME Chart"
        elif category == "k-entertain":
            raw_context = self._scrape_naver_ratings("현재 방영중 예능 시청률 순위")
            source_type = "Naver Latest Entertain Ratings"
        elif category == "k-culture":
            raw_context = self._scrape_naver_blogs("실시간 한국 바이럴 트렌드 핫플")
            source_type = "Naver Realtime Viral Trends"
        else:
            raw_context = None
            source_type = "Unknown"

        if not raw_context:
            print(f"⚠️ [Skip] Valid real-time data not found for {category}.", flush=True)
            return json.dumps({"top10": []})

        return self._process_with_gemini(category, context=raw_context, source_type=source_type)

    def _scrape_recent_actor_news(self):
        if not self.naver_client_id: return None
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_client_id, "X-Naver-Client-Secret": self.naver_client_secret}
        params = {"query": "한국 영화 드라마 배우", "display": 100, "sort": "date"}
        try:
            res = requests.get(url, headers=headers, params=params, timeout=15)
            news_items = res.json().get("items", [])
            now_utc = datetime.now(timezone.utc)
            combined_text = ""
            for item in news_items:
                pub_date = parsedate_to_datetime(item['pubDate'])
                if now_utc - pub_date > timedelta(hours=24): continue # 💡 무조건 24시간 이내 기사만
                title = BeautifulSoup(item['title'], 'html.parser').text
                combined_text += f"- {title}\n"
            return combined_text
        except: return None

    def _scrape_bugs_realtime(self):
        url = "https://music.bugs.co.kr/chart"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            res = None
            if self.proxies:
                try: res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=10)
                except: pass
            if not res or res.status_code != 200:
                res = requests.get(url, headers=headers, verify=False, timeout=10)

            soup = BeautifulSoup(res.text, 'html.parser')
            titles = soup.select('p.title a')
            artists = soup.select('p.artist a:nth-of-type(1)')
            if not titles or not artists: return None
            
            context = ""
            for i in range(min(15, len(titles))):
                context += f"- Rank {i+1}: {titles[i].text.strip()} by {artists[i].text.strip()}\n"
            return context
        except: return None

    def _scrape_naver_ratings(self, query):
        url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            res = None
            if self.proxies:
                try: res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=10)
                except: pass
            if not res or res.status_code != 200:
                res = requests.get(url, headers=headers, verify=False, timeout=10)

            soup = BeautifulSoup(res.text, 'html.parser')
            tables = soup.select('table')
            rating_text = ""
            for table in tables:
                if '%' in table.text or '시청률' in table.text:
                    rows = table.select('tr')
                    for i, row in enumerate(rows):
                        if i == 0: continue
                        cols = row.select('td')
                        if len(cols) >= 2:
                            title = cols[0].text.strip()
                            rating = cols[1].text.strip()
                            rating_text += f"- Title: {title}, Rating: {rating}\n"
                    break 
                    
            if rating_text: return rating_text
            
            main_pack = soup.select_one('#main_pack')
            if main_pack: return main_pack.get_text(separator=' | ', strip=True)[:8000]
            return None
        except: return None

    def _scrape_naver_blogs(self, query):
        url = f"https://search.naver.com/search.naver?where=view&query={urllib.parse.quote(query)}&nso=so%3Add%2Cp%3A1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            res = requests.get(url, headers=headers, verify=False, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            titles = soup.select('a.title_link, .api_txt_lines, .link_tit')
            if titles:
                context = ""
                for i in range(min(30, len(titles))):
                    context += f"- Title: {titles[i].text.strip()}\n"
                return context
            return None
        except: return None

    def _process_with_gemini(self, category, context, source_type):
        if not self.gemini_key or not self.model_name:
            return json.dumps({"top10": []})

        korea_tz = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S KST')
        
        # 💡 [핵심] K-Actor 배역 철통 차단 및 카테고리별 특화 룰
        special_rule = ""
        if category == "k-actor":
            special_rule = "Identify the REAL ACTORS mentioned most frequently in the news. DO NOT include character names (e.g., 'Gihun'). Output ONLY real actor names."
        elif category == "k-culture":
            special_rule = "Extract the most viral trends, foods, or memes currently happening in Korea based on the text."
        elif category == "k-pop":
            special_rule = "Output the Song Title and Singer Name."

        prompt = f"""
        Current Date & Time in Korea: {now_kst}.
        Task: Create a Top 10 ranking chart for '{category}'.
        
        Source Data ({source_type}):
        {context}
        
        CRITICAL RULES:
        1. Base your rankings on the provided source text. {special_rule}
        2. EXCLUDE OUTDATED DATA: Ignore old items.
        3. Extract up to 10 items. If irrelevant, return: {{ "top10": [] }}
        4. Translate all Korean titles/names naturally into English.
        5. 'info' MUST be a concise 1-sentence description explaining why they are ranked (e.g., "Currently highly mentioned for the new drama...").
        6. Format strictly as JSON.
        
        Required JSON Structure:
        {{ "top10": [ {{ "rank": 1, "title": "English Target Name", "info": "Brief description" }} ] }}
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
