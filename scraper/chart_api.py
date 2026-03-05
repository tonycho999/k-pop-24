import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import urllib.parse
from groq import Groq

from model_manager import ModelManager 

class ChartEngine:
    def __init__(self):
        # 1. KOBIS (영화 API)
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

        # 2. IPRoyal 프록시 설정 (크롤링 방어막 우회용)
        self.proxy_host = os.environ.get("PROXY_HOST", "unblocker.iproyal.com")
        self.proxy_port = os.environ.get("PROXY_PORT", "12323")
        self.proxy_user = os.environ.get("PROXY_USER")
        self.proxy_pass = os.environ.get("PROXY_PASS")
        
        if self.proxy_user and self.proxy_pass:
            self.proxies = {
                "http": f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}",
                "https": f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}"
            }
            print("✅ IPRoyal Proxy credentials loaded securely.", flush=True)
        else:
            print("⚠️ IPRoyal Proxy credentials not found. Crawling might fail.", flush=True)
            self.proxies = None

        # 3. Groq 초기화
        self.groq_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key:
                self.groq_keys.append(key)

        if self.groq_keys:
            print(f"✅ Loaded {len(self.groq_keys)} Groq API Keys.", flush=True)
            self.groq_client = Groq(api_key=self.groq_keys[0])
            
            manager = ModelManager(client=self.groq_client, provider="groq")
            best_model_name = manager.get_best_model()
            
            if best_model_name:
                self.model_name = best_model_name
                print(f"✨ ChartEngine successfully received Groq model: {self.model_name}", flush=True)
            else:
                self.model_name = "llama-3.3-70b-versatile"
                print(f"⚠️ Fallback Groq model applied: {self.model_name}", flush=True)
        else:
            print("❌ CRITICAL: GROQ_API_KEY is missing!", flush=True)
            self.groq_client = None
            self.model_name = None

    def get_top10_chart(self, category):
        print(f"\n📊 --- Processing {category} ---", flush=True)

        # 각 카테고리별 전용 데이터 수집기로 데이터 추출 (AI 검색 완전 차단)
        if category == "k-movie":
            raw_context = self._get_kobis_data()
            source_type = "Official KOBIS Data"
            
        elif category == "k-pop":
            raw_context = self._scrape_kpop_data()
            source_type = "Melon Chart Crawling"
            
        elif category == "k-drama":
            raw_context = self._scrape_naver_search("방영중 드라마 시청률 순위")
            source_type = "Naver Search: Drama Ratings"
            
        elif category == "k-entertain":
            raw_context = self._scrape_naver_search("방영중 예능 시청률 순위")
            source_type = "Naver Search: Entertain Ratings"
            
        elif category == "k-culture":
            raw_context = self._scrape_naver_search("서울 핫플레이스 가볼만한곳 순위")
            source_type = "Naver Search: Hot Places"
            
        else:
            raw_context = None
            source_type = "Unknown"

        # 데이터 수집 실패 시 빈 배열 반환
        if not raw_context:
            print(f"⚠️ [Skip] No data found for {category}.", flush=True)
            return json.dumps({"top10": []})

        # 수집된 원본 데이터를 Groq에게 넘겨 번역 및 JSON 포장
        return self._process_with_groq(category, context=raw_context, source_type=source_type)

    def _get_kobis_data(self):
        if not self.kobis_key: return None
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={yesterday}"
        try:
            res = requests.get(url, timeout=15)
            data = res.json()
            box_office_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
            if not box_office_list: return None
            
            context = "OFFICIAL KOREAN BOX OFFICE:\n"
            for movie in box_office_list:
                context += f"- Rank {movie['rank']}: {movie['movieNm']} (Audiences: {movie['audiCnt']})\n"
            return context
        except Exception as e:
            print(f"❌ KOBIS Error: {e}", flush=True)
            return None

    def _scrape_kpop_data(self):
        """IPRoyal로 멜론 차트 크롤링"""
        if not self.proxies: return None
        url = "https://www.melon.com/chart/index.htm"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        print("  > 🚀 Scraping Melon Chart using IPRoyal...", flush=True)
        try:
            res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=30)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, 'html.parser')
            songs = soup.select('div.wrap_song_info')
            
            if not songs:
                return None
                
            context = "OFFICIAL MELON REAL-TIME TOP 10:\n"
            count = 1
            for song in songs:
                title_elem = song.select_one('div.ellipsis.rank01 a')
                artist_elem = song.select_one('div.ellipsis.rank02 > a')
                if title_elem and artist_elem:
                    context += f"- Rank {count}: {title_elem.text.strip()} by {artist_elem.text.strip()}\n"
                    count += 1
                if count > 10: break
            return context
        except Exception as e:
            print(f"  > ❌ Melon Crawling Error: {e}", flush=True)
            return None

    def _scrape_naver_search(self, query):
        """IPRoyal로 네이버 검색 결과를 긁어와서 텍스트만 추출"""
        if not self.proxies: return None
        
        encoded_query = urllib.parse.quote(query)
        url = f"https://search.naver.com/search.naver?query={encoded_query}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        print(f"  > 🚀 Scraping Naver Search for '{query}' using IPRoyal...", flush=True)
        try:
            res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=30)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 네이버 검색 결과의 메인 영역만 추출
            main_pack = soup.select_one('#main_pack')
            if not main_pack:
                print("  > ⚠️ Failed to find #main_pack in Naver HTML.", flush=True)
                return None
            
            # 쓸데없는 공백 제거하고 텍스트만 추출
            raw_text = main_pack.get_text(separator=' ', strip=True)
            
            # 텍스트가 너무 길면 Groq 토큰 초과 방지를 위해 자르기 (앞부분에 핵심 순위가 몰려있음)
            cleaned_text = ' '.join(raw_text.split())[:8000] 
            
            print(f"  > ✅ Scraped Naver text successfully ({len(cleaned_text)} chars).", flush=True)
            return cleaned_text
            
        except Exception as e:
            print(f"  > ❌ Naver Crawling Error: {e}", flush=True)
            return None

    def _process_with_groq(self, category, context, source_type):
        """수집된 원본 텍스트를 Groq에게 넘겨 번역 및 JSON 파싱"""
        if not self.groq_client or not self.model_name:
            return json.dumps({"top10": []})

        today = datetime.now().strftime('%Y-%m-%d')
        
        # 카테고리별 특수 규칙 부여 (가비지 데이터 필터링용)
        special_rules = ""
        if category == "k-drama":
            special_rules = "- STRICTLY INCLUDE ONLY TV Dramas/Series. FILTER OUT News programs and Variety Shows."
        elif category == "k-entertain":
            special_rules = "- STRICTLY INCLUDE ONLY Variety Shows (예능). FILTER OUT News and Dramas."
        elif category == "k-culture":
            special_rules = "- Identify top 10 trending places, neighborhoods, or pop-ups from the text."

        prompt = f"""
        Today is {today}.
        Task: Create a Top 10 ranking chart for '{category}' based ONLY on the provided source text.
        
        Source Data ({source_type}):
        {context}
        
        Rules:
        1. Extract exactly the Top 10 items from the source data provided above.
        2. Do not invent or hallucinate data. If the text has less than 10, extract as many as you can find.
        {special_rules}
        3. Translate all Korean titles and names naturally into English.
        4. 'info' should be a concise 1-sentence English description (e.g., ratings, artist, or reason for trending).
        5. Output STRICTLY as a valid JSON object without any markdown code blocks (` ``` `).
        
        Required Format:
        {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief description" }} ] }}
        """

        try:
            print(f"  > Sending request to Groq API (Model: {self.model_name})...", flush=True)
            
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a strict data formatting assistant. Output nothing but valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model_name,
                temperature=0.1, 
            )

            content = chat_completion.choices[0].message.content.strip()
            
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            print("  ✅ Groq JSON processing successful.", flush=True)
            return content

        except Exception as e:
            print(f"❌ Groq API Error: {e}", flush=True)
            return json.dumps({"top10": []})
