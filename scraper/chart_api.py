import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import urllib3
from google import genai

# SSL 프록시 접속 경고창 영구 숨김 처리
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ChartAPI:
    def __init__(self, db):
        self.db = db
        self.kobis_key = os.environ.get("KOBIS_API_KEY") 
        self.tmdb_key = os.environ.get("TMDB_API_KEY") # 💡 TMDB 키 로드
        
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        if self.gemini_key:
            self.ai_client = genai.Client(api_key=self.gemini_key)
        
        raw_host = os.environ.get("PROXY_HOST", "").replace("http://", "").replace("https://", "")
        self.proxy_host = raw_host
        self.proxy_port = os.environ.get("PROXY_PORT")
        self.proxy_user = os.environ.get("PROXY_USER")
        self.proxy_pass = os.environ.get("PROXY_PASS")
        
        self.proxies = None
        self.playwright_proxy = None
        if self.proxy_host and self.proxy_port and self.proxy_user and self.proxy_pass:
            proxy_url = f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}"
            self.proxies = {"http": proxy_url, "https": proxy_url}
            self.playwright_proxy = {
                "server": f"http://{self.proxy_host}:{self.proxy_port}",
                "username": self.proxy_user,
                "password": self.proxy_pass
            }

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def update_chart(self, category):
        results = []
        if category == 'k-movie':
            results = self._get_kobis_box_office()
        elif category == 'k-drama':
            results = self._get_tmdb_ranking(is_drama=True) # 💡 TMDB API 호출 (드라마)
        elif category == 'k-entertain':
            results = self._get_tmdb_ranking(is_drama=False) # 💡 TMDB API 호출 (예능)
        elif category == 'k-pop':
            results = self._get_music_chart()
        elif category == 'k-culture':
            results = self._get_culture_trends()

        if results:
            results = self._translate_chart_titles(results, category)
            self.db.save_chart_results(category, results)
            print(f"  ✅ Chart updated for {category} ({len(results)} items saved).")
        else:
            print(f"  ⚠️ No chart data retrieved for {category}.")

    # 🤖 AI 영문 일괄 번역기
    def _translate_chart_titles(self, chart_data, category):
        if not hasattr(self, 'ai_client') or not self.ai_client:
            return chart_data

        items_to_translate = [{"title": item['title'], "info": item['info']} for item in chart_data]
        
        prompt = f"""
        You are an expert K-Culture translator. Translate the following JSON list of items into natural, trendy English.
        - 'title': Translate Korean into natural English. Keep proper nouns Romanized.
        - 'info': If it is an artist name starting with 'By' (K-Pop category), you MUST unify the format strictly to 'By English Name (Korean Name)'. 
          For non-music categories (Daily:, Pop:, Real-time Trend), leave the 'info' text exactly as it is.
        - Must return ONLY a valid JSON array of objects containing 'title' and 'info' keys.
        
        Items to translate:
        {json.dumps(items_to_translate, ensure_ascii=False)}
        """
        try:
            ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            text = ai_res.text.replace("```json", "").replace("```", "").strip()
            translated_items = json.loads(text)
            
            for i, item in enumerate(chart_data):
                if i < len(translated_items):
                    item['title'] = translated_items[i].get('title', item['title'])
                    item['info'] = translated_items[i].get('info', item['info'])
        except Exception as e:
            print(f"    ⚠️ AI Translation Error: {e}")
            
        return chart_data

    # 🎬 영화: 영화진흥위원회(KOBIS) 박스오피스 API
    def _get_kobis_box_office(self):
        if not self.kobis_key: return []
        kst = pytz.timezone('Asia/Seoul')
        yesterday = (datetime.now(kst) - timedelta(days=1)).strftime('%Y%m%d')
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={yesterday}"
        
        try:
            res = requests.get(url, timeout=10).json()
            movies = res.get('boxOfficeResult', {}).get('dailyBoxOfficeList', [])
            chart = []
            for m in movies[:10]:
                chart.append({
                    "rank": int(m['rank']),
                    "title": m['movieNm'],
                    "info": f"Daily: {int(m['audiCnt']):,}", 
                    "score": 101 - int(m['rank'])
                })
            return chart
        except: return []

    # 📺 드라마/예능: 글로벌 1위 TMDB 공식 API 연동 (에러율 0%)
    def _get_tmdb_ranking(self, is_drama=True):
        if not self.tmdb_key:
            print("  ❌ Error: TMDB_API_KEY is missing.")
            return []
            
        if is_drama:
            genre_filter = "&without_genres=10764,10767,10763"
        else:
            genre_filter = "&with_genres=10764|10767"

        url = f"https://api.themoviedb.org/3/discover/tv?api_key={self.tmdb_key}&with_original_language=ko{genre_filter}&sort_by=popularity.desc&language=ko-KR"
        
        try:
            res = requests.get(url, timeout=10).json()
            shows = res.get('results', [])
            chart = []
            rank = 1
            for s in shows[:10]:
                chart.append({
                    "rank": rank,
                    "title": s.get('name', 'Unknown'),
                    "info": f"Pop: {int(s.get('popularity', 0))}", 
                    "score": 101 - rank
                })
                rank += 1
            return chart
        except Exception as e:
            print(f"  ❌ TMDB API Error: {e}")
            return []

    # 🎵 K-POP: 벅스(Bugs) 뮤직 실시간 차트 (Plan A -> B -> C)
    def _get_music_chart(self):
        url = "https://music.bugs.co.kr/chart"
        def parse_html(html_text):
            soup = BeautifulSoup(html_text, 'html.parser')
            songs = soup.select('table.list.trackList tbody tr')
            chart = []
            rank = 1
            for song in songs[:10]:
                title_el = song.select_one('p.title a')
                artist_el = song.select_one('p.artist a')
                if title_el and artist_el:
                    chart.append({
                        "rank": rank,
                        "title": title_el.text.strip(),
                        "info": f"By {artist_el.text.strip()}",
                        "score": 101 - rank
                    })
                    rank += 1
            return chart

        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            chart = parse_html(res.text)
            if chart: return chart
        except Exception as e:
            print(f"    ⚠️ Plan A Failed: {e}")

        print("  🕵️ Plan B (Proxy) for Music Chart...")
        try:
            res = requests.get(url, headers=self.headers, proxies=self.proxies, verify=False, timeout=15)
            chart = parse_html(res.text)
            if chart: return chart
        except Exception as e:
            print(f"    ⚠️ Plan B Failed: {e}")

        print("  🚜 Plan C (Playwright) for Music Chart...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, proxy=self.playwright_proxy)
                page = browser.new_page(user_agent=self.headers["User-Agent"])
                page.goto(url, timeout=20000)
                page.wait_for_timeout(2000)
                html = page.content()
                browser.close()
                return parse_html(html)
        except Exception as e:
            print(f"  ❌ All Plans Failed for Music: {e}")
            return []

    # 🌍 K-Culture: 시그널(Signal.bz) 실시간 검색어 (Plan A -> B -> C)
    def _get_culture_trends(self):
        url = "https://signal.bz/news"
        def parse_html(html_text):
            soup = BeautifulSoup(html_text, 'html.parser')
            items = soup.select('.rank-layer .rank-text')
            chart = []
            rank = 1
            for item in items[:10]:
                chart.append({
                    "rank": rank,
                    "title": item.text.strip(),
                    "info": "Real-time Trend",
                    "score": 101 - rank
                })
                rank += 1
            return chart

        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            chart = parse_html(res.text)
            if chart: return chart
        except Exception as e:
            print(f"    ⚠️ Plan A Failed: {e}")

        print("  🕵️ Plan B (Proxy) for Culture Trends...")
        try:
            res = requests.get(url, headers=self.headers, proxies=self.proxies, verify=False, timeout=15)
            chart = parse_html(res.text)
            if chart: return chart
        except Exception as e:
            print(f"    ⚠️ Plan B Failed: {e}")

        print("  🚜 Plan C (Playwright) for Culture Trends...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, proxy=self.playwright_proxy)
                page = browser.new_page(user_agent=self.headers["User-Agent"])
                page.goto(url, timeout=20000)
                page.wait_for_timeout(2000)
                html = page.content()
                browser.close()
                return parse_html(html)
        except Exception as e:
            print(f"  ❌ All Plans Failed for Culture Trends: {e}")
            return []
