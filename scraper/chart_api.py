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

    # 💡 [수정] main.py가 던져주는 search_keyword를 받습니다!
    def get_top10_chart(self, category, search_keyword):
        print(f"\n📊 --- Processing {category} (ABSOLUTE LATEST) ---", flush=True)

        # K-POP은 예외! 검색어 무시하고 벅스뮤직 직행
        if category == "k-pop":
            raw_context = self._scrape_bugs_realtime()
            source_type = "Bugs Music REAL-TIME Chart"
        else:
            # 💡 [핵심] 나머지 모든 부서는 뉴스 봇과 동일한 '안전한 API 수집'으로 통일!
            raw_context = self._scrape_naver_news_api(search_keyword)
            source_type = f"Naver News Mention Count (Last 24 Hours, Keyword: {search_keyword})"

        if not raw_context:
            print(f"⚠️ [Skip] Valid real-time data not found for {category}.", flush=True)
            return json.dumps({"top10": []})

        return self._process_with_gemini(category, context=raw_context, source_type=source_type)

    # 💡 [완벽 이식] HTML 크롤링 다 버리고, 실패 없는 24시간 네이버 뉴스 API 무한 수집기 탑재!
    def _scrape_naver_news_api(self, query):
        if not self.naver_client_id or not query: return None
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_client_id, "X-Naver-Client-Secret": self.naver_client_secret}
        
        # 1. 봇의 시계를 한국 시간(KST)으로 강제 고정
        korea_tz = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(korea_tz)
        
        # 2. 정확히 24시간 전이라는 '데드라인' 설정
        deadline = now_kst - timedelta(hours=24)
        
        combined_text = ""
        start_index = 1
        max_pages = 5 # 100개씩 최대 5번 (500개) 스캔하여 언급량 정확도 극대화

        try:
            for _ in range(max_pages):
                params = {"query": query, "display": 100, "start": start_index, "sort": "date"}
                res = requests.get(url, headers=headers, params=params, timeout=10)
                res.raise_for_status()
                news_items = res.json().get("items", [])
                
                if not news_items:
                    break 
                    
                reached_deadline = False
                
                for item in news_items:
                    # 기사 발행 시간을 KST로 변환
                    pub_date = parsedate_to_datetime(item['pubDate']).astimezone(korea_tz)
                    
                    if pub_date > deadline:
                        title = BeautifulSoup(item['title'], 'html.parser').text
                        desc = BeautifulSoup(item['description'], 'html.parser').text
                        combined_text += f"- {title}: {desc}\n"
                    else:
                        # 24시간 경과 기사 등장 시 수집 즉시 스톱
                        reached_deadline = True
                        break 
                
                if reached_deadline:
                    break 
                    
                start_index += 100 
                
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

    def _process_with_gemini(self, category, context, source_type):
        if not self.gemini_key or not self.model_name:
            return json.dumps({"top10": []})

        korea_tz = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S KST')
        
        # 💡 [핵심] 종목이 '화제성 순위'로 통일됨에 따라 AI 지시사항도 완벽하게 수정!
        special_rule = ""
        if category == "k-actor":
            special_rule = "Identify the REAL ACTORS mentioned most frequently in the news. Count their mentions and rank them. DO NOT include character names."
        elif category == "k-entertain":
            special_rule = "Identify the VARIETY SHOWS (예능 프로그램) or ENTERTAINERS (예능인) mentioned most frequently. Rank them by mention count. Ignore dramas or news programs."
        elif category == "k-culture":
            special_rule = "Extract the Top 10 VIRAL TRENDS (e.g., hot places, local festivals, popular foods, pop-up stores). Explain briefly why it's trending."
        elif category == "k-pop":
            special_rule = "Output the Song Title and Singer Name exactly as ranked."

        prompt = f"""
        Current Date & Time in Korea: {now_kst}.
        Task: Create a Top 10 ranking chart for '{category}'.
        
        Source Data ({source_type}):
        {context}
        
        CRITICAL RULES:
        1. Base your rankings ONLY on the provided source text. {special_rule}
        2. Extract up to 10 items. If irrelevant or empty, return: {{ "top10": [] }}
        3. Translate all Korean titles, names, and places naturally into English.
        4. 'info' MUST be a concise factual description (e.g., "A highly mentioned show" or "A popular pop-up store in Seongsu").
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
