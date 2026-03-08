import os
import pytz
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class ChartManager:
    def __init__(self, model_manager):
        self.model = model_manager
        
        # 💡 [핵심] 대표님이 작성해주신 환경 변수 기반 IPRoyal 프록시 로직 완벽 적용
        self.proxy_host = os.environ.get("PROXY_HOST", "unblocker.iproyal.com")
        self.proxy_port = os.environ.get("PROXY_PORT", "12323")
        self.proxy_user = os.environ.get("PROXY_USER")
        self.proxy_pass = os.environ.get("PROXY_PASS")
        
        if self.proxy_user and self.proxy_pass:
            self.proxies = {
                "http": f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}",
                "https": f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}"
            }
            print("✅ IPRoyal Proxy successfully configured via Environment Variables!")
        else:
            self.proxies = None
            print("⚠️ Warning: Proxy credentials not found. Proceeding without proxy.")

    def _scrape_real_chart(self, target):
        """IPRoyal 프록시를 이용해 타겟 사이트의 순위표(HTML)를 직접 뜯어옵니다."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            if target == "melon":
                # 멜론 실시간 차트 직접 접속
                url = "https://www.melon.com/chart/index.htm"
                res = requests.get(url, headers=headers, proxies=self.proxies, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # 차트 테이블 안의 글자들만 싹 긁어옴 (가수, 곡명 등)
                chart_body = soup.find('tbody')
                return chart_body.get_text(separator=' | ', strip=True)[:4000] if chart_body else ""
                
            elif target == "nielsen":
                # 네이버의 시청률 요약표 직접 긁기
                url = "https://search.naver.com/search.naver?query=주간+예능+시청률"
                res = requests.get(url, headers=headers, proxies=self.proxies, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # 시청률 테이블 글자만 싹 긁어옴
                rating_table = soup.find('table')
                return rating_table.get_text(separator=' | ', strip=True)[:4000] if rating_table else ""
                
        except Exception as e:
            print(f"⚠️ Scraping Error for {target}: {e}")
            return ""

    def process_chart(self, category: str, context: str, source_type: str):
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        
        prompt = ""
        
        # 🎵 K-Pop: 멜론 차트 HTML 텍스트를 AI에게 번역/정리시킴
        if category == "k-pop":
            raw_chart_text = self._scrape_real_chart("melon")
            prompt = f"""
            Current Time: {now_kst}.
            Task: Create a Top 10 K-Pop Music Chart.
            Raw Website Text (Melon Chart): {raw_chart_text}
            
            CRITICAL RULES:
            1. Parse the provided raw text to find the actual Top 10 songs.
            2. 'title' MUST be the Song Name (English translated).
            3. 'info' MUST be ONLY the Singer Name.
            4. Score: Assign exactly 100 for 1st place, decreasing by 1 down to 91 for 10th place.
            """
            
        # 📺 K-Entertain: 닐슨코리아 시청률 HTML 텍스트를 AI에게 번역/정리시킴
        elif category == "k-entertain":
            raw_rating_text = self._scrape_real_chart("nielsen")
            prompt = f"""
            Current Time: {now_kst}.
            Task: Create a Top 10 Variety Show Rankings based on TV ratings.
            Raw Website Text (Nielsen Ratings): {raw_rating_text}
            
            CRITICAL RULES:
            1. Parse the raw text to find Top 10 variety shows based on ratings. EXCLUDE Dramas and News.
            2. 'title' MUST be the Show Name (English translated).
            3. 'info' MUST be the TV Channel (e.g., "tvN", "SBS", "MBC").
            4. Score: Assign exactly 100 for 1st place, decreasing by 1 down to 91 for 10th place.
            """
            
        # 🌟 K-Actor: 뉴스 DB 화제성 기준 (기존 유지)
        elif category == "k-actor":
            prompt = f"""
            Current Time: {now_kst}.
            Task: Create a Top 10 Actor Trend Chart based on mention frequency.
            Source Data: {context}
            
            CRITICAL RULES:
            1. Count mentions of ACTORS ONLY in the provided news context. Rank by frequency.
            2. 'title' MUST be the Actor Name (English).
            3. 'info' MUST be a very short 1-2 word English keyword (e.g., "New Drama", "Scandal", "Dating").
            4. Score: Freely assign between 80 and 100 based on the buzz. Be diverse.
            """
            
        # 🔥 K-Culture: 고유명사 & 트렌드 기준 (기존 유지)
        elif category == "k-culture":
            prompt = f"""
            Current Time: {now_kst}.
            Task: Create a Top 10 K-Culture Trend Chart.
            Source Data: {context}
            
            CRITICAL RULES:
            1. Extract PROPER NOUNS ONLY (Specific foods, desserts, festivals, hot places, memes).
            2. EXCLUDE generic words, TV shows, politicians, or ordinary news.
            3. 'title' MUST be the specific trend name (English).
            4. 'info' MUST be a 1-2 word category (e.g., "Dessert", "Pop-up", "Meme").
            5. Score: Freely assign between 50 and 80 ONLY. (DO NOT EXCEED 80).
            """

        prompt += """
        Format strictly as JSON.
        Required JSON Structure:
        { "top10": [ { "rank": 1, "title": "Target Name", "info": "Keyword", "score": 90 } ] }
        """

        print(f"  > AI is parsing raw HTML data for {category}...")
        try:
            result_text = self.model.generate_content(prompt)
            if not result_text: return None
            
            json_str = result_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)
            return data.get("top10", [])
        except Exception as e:
            print(f"❌ Gemini Chart Error for {category}: {e}")
            return None
