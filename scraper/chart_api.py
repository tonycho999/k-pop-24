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
            raw_context = self._scrape_naver_news_api("배우")
            source_type = "Naver News Mention Count (Last 24 Hours)"
        elif category == "k-pop":
            raw_context = self._scrape_bugs_realtime()
            source_type = "Bugs Music REAL-TIME Chart"
        elif category == "k-entertain":
            raw_context = self._scrape_naver_ratings("현재 방영중 예능 시청률 순위")
            source_type = "Naver Search (Entertainment Ratings Table)"
        elif category == "k-culture":
            raw_context = self._scrape_naver_blogs("한국 핫플레이스 국내 축제 유행 디저트")
            source_type = "Naver VIEW (Blog/Cafe Viral Trends)"
        else:
            raw_context = None
            source_type = "Unknown"

        if not raw_context:
            print(f"⚠️ [Skip] Valid real-time data not found for {category}.", flush=True)
            return json.dumps({"top10": []})

        return self._process_with_gemini(category, context=raw_context, source_type=source_type)

    # 💡 [핵심 업데이트] 봇의 시간 동기화 및 24시간 풀 스캔 로직 탑재
    def _scrape_naver_news_api(self, query):
        if not self.naver_client_id: return None
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_client_id, "X-Naver-Client-Secret": self.naver_client_secret}
        
        # 1. 봇의 시계를 한국 시간(KST)으로 강제 고정
        korea_tz = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(korea_tz)
        
        # 2. 정확히 24시간 전이라는 '데드라인' 설정
        deadline = now_kst - timedelta(hours=24)
        
        combined_text = ""
        start_index = 1
        max_pages = 5 # 혹시 모를 무한루프 방지 (최대 500개 기사까지만 허용)

        try:
            # 3. 100개 단위로 '24시간'이 다 찰 때까지 무한 수집 (최대 5번)
            for _ in range(max_pages):
                params = {"query": query, "display": 100, "start": start_index, "sort": "date"}
                res = requests.get(url, headers=headers, params=params, timeout=10)
                res.raise_for_status()
                news_items = res.json().get("items", [])
                
                if not news_items:
                    break # 더 이상 가져올 기사가 없으면 탈출
                    
                reached_deadline = False
                
                for item in news_items:
                    # 기사 발행 시간을 KST로 변환하여 봇의 시간과 동일선상에 둠
                    pub_date = parsedate_to_datetime(item['pubDate']).astimezone(korea_tz)
                    
                    # 데드라인(24시간 전) 이내의 기사만 수집
                    if pub_date > deadline:
                        title = BeautifulSoup(item['title'], 'html.parser').text
                        desc = BeautifulSoup(item['description'], 'html.parser').text
                        combined_text += f"- {title}: {desc}\n"
                    else:
                        # 24시간을 넘어간 옛날 기사가 등장하면 즉시 스캔 종료
                        reached_deadline = True
                        break 
                
                if reached_deadline:
                    break # 바깥쪽 페이징 루프도 완전히 종료
                    
                start_index += 100 # 아직 24시간이 안 끝났다면 다음 100개(페이지) 요청 준비
                
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
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"  ⚠️ Gemini Error: {e}", flush=True)
            return json.dumps({"top10": []})
