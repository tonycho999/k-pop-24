import os
import json
import requests
import pytz
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from google import genai
from google.genai import types
from model_manager import ModelManager 

# 터미널 HTTPS 보안 경고창 완벽 제거
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ChartEngine:
    def __init__(self, db):
        self.db = db
        self.naver_client_id = os.environ.get("NAVER_CLIENT_ID")
        self.naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET")

        # Bugs 크롤링을 위한 프록시 유지 (네이버 API는 안 씀)
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

    def get_top10_chart(self, category, search_keyword):
        print(f"\n📊 --- Processing {category} (ABSOLUTE LATEST) ---", flush=True)

        if category == "k-pop":
            raw_context = self._scrape_bugs_realtime()
            source_type = "Bugs Music REAL-TIME Chart"
        else:
            raw_context = self._scrape_naver_news_api(search_keyword)
            source_type = f"Naver News Mention Count (Last 24 Hours, Keyword: {search_keyword})"

        if not raw_context:
            print(f"⚠️ [Skip] Valid real-time data not found for {category}.", flush=True)
            return json.dumps({"top10": []})

        return self._process_with_gemini(category, context=raw_context, source_type=source_type)

    def _scrape_naver_news_api(self, query):
        if not self.naver_client_id or not query: return None
        
        # 💡 [핵심] 차트 봇도 동일하게 문자열을 쪼개서 배열로 만듭니다.
        keyword_list = [k.strip() for k in query.split("|") if k.strip()]
        
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_client_id, "X-Naver-Client-Secret": self.naver_client_secret}
        
        korea_tz = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(korea_tz)
        deadline = now_kst - timedelta(hours=24)
        
        combined_text = ""

        # 💡 [핵심] 쪼개진 단어별로 각각 검색하여 데이터를 거대한 텍스트로 합칩니다.
        for keyword in keyword_list:
            params = {"query": keyword, "display": 100, "sort": "date"}
            try:
                res = requests.get(url, headers=headers, params=params, timeout=10)
                res.raise_for_status()
                news_items = res.json().get("items", [])
                
                for item in news_items:
                    pub_date = parsedate_to_datetime(item['pubDate']).astimezone(korea_tz)
                    if pub_date > deadline:
                        title = BeautifulSoup(item['title'], 'html.parser').text
                        desc = BeautifulSoup(item['description'], 'html.parser').text
                        combined_text += f"- {title}: {desc}\n"
            except Exception as e:
                print(f"  ❌ Naver API Error for '{keyword}': {e}")
                
        return combined_text if combined_text else None

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

    def _process_with_gemini(self, category, context, source_type):
        if not self.gemini_key or not self.model_name:
            return json.dumps({"top10": []})

        korea_tz = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S KST')
        
        special_rule = ""
        if category == "k-actor":
            special_rule = "Identify the REAL ACTORS mentioned most frequently in the news. Count their mentions and rank them. DO NOT include character names."
        elif category == "k-entertain":
            special_rule = "Identify the VARIETY SHOWS (예능 프로그램) or ENTERTAINERS (예능인) mentioned most frequently. Rank them by mention count. Ignore dramas or news programs."
        elif category == "k-culture":
            special_rule = "MUST extract ONLY exact PROPER NOUNS (Specific food/dessert names, festival names, hot place locations, or pop-up store brands). STRICTLY FORBIDDEN: generic words, full article titles, TV documentaries, regional government news (e.g., 창원시 유튜브). If it is not a specific brand, place, or food name, DROP IT."
        elif category == "k-pop":
            special_rule = "Output the Song Title and Singer Name exactly as ranked."

        prompt = f"""
        Current Date & Time in Korea: {now_kst}.
        Task: Create a Top 10 ranking chart for '{category}'.
        
        Source Data ({source_type}):
        {context}
        
        CRITICAL RULES:
        1. Base your rankings ONLY on the provided source text. For the music chart, place ONLY the Song Title in the 'title' field, and place ONLY the Singer Name (Artist Name) in the 'info' field. DO NOT include any rank descriptions (like 'ranked number one') in the 'info' field. {special_rule}
        2. Extract up to 10 items. If irrelevant or empty, return: {{ "top10": [] }}
        3. Translate all Korean into English naturally.
        4. 'info' MUST be extremely short (Maximum 2-3 words). Act like an Instagram hashtag. Use catchy English keyword phrases (e.g., "New Movie Issue", "Viral Dessert", "Scandal", "Pop-up Store"). For k-pop, 'info' must be ONLY the Singer Name. NEVER write a full sentence.
        5. Format strictly as JSON.
        
        Required JSON Structure:
        {{ "top10": [ {{ "rank": 1, "title": "English Target Name", "info": "Brief info or reason" }} ] }}
        """

        try:
            print(f"  > AI Analyst is counting and ranking data for {category}...", flush=True)
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
