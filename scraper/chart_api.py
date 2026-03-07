import os
import json
import requests
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

        # 웹 크롤링(차트, 시청률, 블로그)을 위한 프록시 유지
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
            # 💡 [방법 B] 군더더기 없이 "배우" 단일 키워드로 뉴스 API 검색
            raw_context = self._scrape_naver_news_api("배우")
            source_type = "Naver News Mention Count (Last 24 Hours)"
        elif category == "k-pop":
            # 💡 벅스 실시간 차트 유지
            raw_context = self._scrape_bugs_realtime()
            source_type = "Bugs Music REAL-TIME Chart"
        elif category == "k-entertain":
            # 💡 예전에 잘 작동했던 네이버 통합검색 시청률 표 크롤링 복구!
            raw_context = self._scrape_naver_ratings("현재 방영중 예능 시청률 순위")
            source_type = "Naver Search (Entertainment Ratings Table)"
        elif category == "k-culture":
            # 💡 네이버 VIEW(블로그) 탭 크롤링 복구 (외국인 맞춤형 장소/유행)
            raw_context = self._scrape_naver_blogs("한국 핫플레이스 국내 축제 유행 디저트")
            source_type = "Naver VIEW (Blog/Cafe Viral Trends)"
        else:
            raw_context = None
            source_type = "Unknown"

        if not raw_context:
            print(f"⚠️ [Skip] Valid real-time data not found for {category}.", flush=True)
            return json.dumps({"top10": []})

        return self._process_with_gemini(category, context=raw_context, source_type=source_type)

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
        except Exception as e:
            print(f"  ❌ Bugs Chart Error: {e}")
            return None

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
            return rating_text if rating_text else None
        except Exception as e:
            print(f"  ❌ Naver Ratings Error: {e}")
            return None

    def _scrape_naver_blogs(self, query):
        url = f"https://search.naver.com/search.naver?where=view&query={urllib.parse.quote(query)}&nso=so%3Add%2Cp%3A1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            res = None
            if self.proxies:
                try: res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=10)
                except: pass
            if not res or res.status_code != 200:
                res = requests.get(url, headers=headers, verify=False, timeout=10)

            soup = BeautifulSoup(res.text, 'html.parser')
            titles = soup.select('a.title_link, .api_txt_lines, .link_tit')
            if titles:
                context = ""
                for i in range(min(30, len(titles))):
                    context += f"- Trend: {titles[i].text.strip()}\n"
                return context
            return None
        except Exception as e:
            print(f"  ❌ Naver Blogs Error: {e}")
            return None

    def _process_with_gemini(self, category, context, source_type):
        if not self.gemini_key or not self.model_name:
            return json.dumps({"top10": []})

        korea_tz = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S KST')
        
        special_rule = ""
        if category == "k-actor":
            special_rule = "Identify the REAL ACTORS mentioned most frequently in the news. Count their mentions and rank them. DO NOT include character names. Output ONLY real actor names."
        elif category == "k-culture":
            # 💡 외국인 팬들을 타겟팅하여 큐레이션 하도록 지시!
            special_rule = "Analyze the blog titles and extract the Top 10 viral things foreigners visiting Korea would love (e.g., hot places, local festivals, popular foods, desserts, pop-up stores). Explain briefly why it's trending."
        elif category == "k-pop":
            special_rule = "Output the Song Title and Singer Name exactly as ranked."
        elif category == "k-entertain":
            special_rule = "Extract the Variety Show names and their ratings from the table data. Rank them by rating."

        prompt = f"""
        Current Date & Time in Korea: {now_kst}.
        Task: Create a Top 10 ranking chart for '{category}'.
        
        Source Data ({source_type}):
        {context}
        
        CRITICAL RULES:
        1. Base your rankings ONLY on the provided source text. {special_rule}
        2. Extract up to 10 items. If irrelevant or empty, return: {{ "top10": [] }}
        3. Translate all Korean titles, names, and places naturally into English.
        4. 'info' MUST be a concise factual description (e.g., "Rating: 15.2%" or "A highly mentioned actor" or "A popular dessert cafe in Seongsu").
        5. Format strictly as JSON.
        
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
                    temperature=0.0,  # 팩트 기반 강제
                    response_mime_type="application/json",
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"  ⚠️ Gemini Error: {e}", flush=True)
            return json.dumps({"top10": []})
