import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import urllib3
import xml.etree.ElementTree as ET
from google import genai

# SSL 프록시 접속 경고창 영구 숨김 처리
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ChartAPI:
    def __init__(self, db):
        self.db = db
        self.kobis_key = os.environ.get("KOBIS_API_KEY") 
        
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        if self.gemini_key:
            self.ai_client = genai.Client(api_key=self.gemini_key)
        
        self.proxy_host = os.environ.get("PROXY_HOST")
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

    def update_chart(self, category):
        results = []
        if category == 'k-movie':
            results = self._get_kobis_box_office()
        elif category == 'k-drama':
            results = self._get_naver_ratings("드라마 시청률")
        elif category == 'k-entertain':
            results = self._get_naver_ratings("예능 시청률")
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

        titles = [item['title'] for item in chart_data]
        prompt = f"""
        You are a K-Culture translator. Translate the following list of Korean titles (movies, tv shows, songs, or search trends) into natural English.
        - Must return ONLY a valid JSON array of strings.
        - Keep proper nouns Romanized.
        
        Titles to translate:
        {json.dumps(titles, ensure_ascii=False)}
        """
        try:
            ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            text = ai_res.text.replace("```json", "").replace("```", "").strip()
            translated_titles = json.loads(text)
            
            for i, item in enumerate(chart_data):
                if i < len(translated_titles):
                    item['title'] = translated_titles[i]
        except Exception as e:
            print(f"    ⚠️ AI Translation Error: {e}")
            
        return chart_data

    # 🎬 영화: 영화진흥위원회(KOBIS) 박스오피스 API (공식 API이므로 단일 호출)
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
                    "info": f"Daily: {int(m['audiCnt']):,}", # 💡 [수정] "Daily Audience" -> "Daily: 숫자" 로 극단적 축약
                    "score": 101 - int(m['rank'])
                })
            return chart
        except: return []

    # 📺 드라마/예능: 네이버 시청률 크롤링 (Plan A -> B -> C)
    def _get_naver_ratings(self, query):
        url = f"https://search.naver.com/search.naver?query={query}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

        def parse_html(html_text):
            soup = BeautifulSoup(html_text, 'html.parser')
            rows = soup.select('table.rate_table_info tbody tr') or soup.select('.tv_rating_table tbody tr') or soup.select('.list_info li')
            chart = []
            rank = 1
            for row in rows[:10]:
                title_el = row.select_one('.title a, .name a, th a')
                rate_el = row.select_one('.percent, .rate, td.rate')
                if title_el and rate_el:
                    chart.append({
                        "rank": rank,
                        "title": title_el.text.strip(),
                        "info": f"Rating: {rate_el.text.strip()}", # 💡 [수정] 짧고 명확하게
                        "score": 101 - rank
                    })
                    rank += 1
            return chart

        # 🛡️ Plan A: 순정 IP
        try:
            res = requests.get(url, headers=headers, timeout=10)
            chart = parse_html(res.text)
            if chart: return chart
        except: pass

        # 🕵️‍♂️ Plan B: 프록시 우회
        print(f"  🕵️ Plan B (Proxy) for {query}...")
        try:
            res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=15)
            chart = parse_html(res.text)
            if chart: return chart
        except: pass

        # 🚜 Plan C: 투명 브라우저 + 프록시
        print(f"  🚜 Plan C (Playwright) for {query}...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, proxy=self.playwright_proxy)
                page = browser.new_page(user_agent=headers["User-Agent"])
                page.goto(url, timeout=20000)
                page.wait_for_timeout(2000)
                html = page.content()
                browser.close()
                return parse_html(html)
        except Exception as e:
            print(f"  ❌ All Plans Failed for {query}: {e}")
            return []

    # 🎵 K-POP: 벅스(Bugs) 뮤직 실시간 차트 (Plan A -> B -> C)
    def _get_music_chart(self):
        url = "https://music.bugs.co.kr/chart"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

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
                        "info": f"By {artist_el.text.strip()}", # 💡 [수정] "Artist: OOO" -> "By OOO"
                        "score": 101 - rank
                    })
                    rank += 1
            return chart

        # 🛡️ Plan A
        try:
            res = requests.get(url, headers=headers, timeout=10)
            chart = parse_html(res.text)
            if chart: return chart
        except: pass

        # 🕵️‍♂️ Plan B
        print("  🕵️ Plan B (Proxy) for Music Chart...")
        try:
            res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=15)
            chart = parse_html(res.text)
            if chart: return chart
        except: pass

        # 🚜 Plan C
        print("  🚜 Plan C (Playwright) for Music Chart...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, proxy=self.playwright_proxy)
                page = browser.new_page(user_agent=headers["User-Agent"])
                page.goto(url, timeout=20000)
                page.wait_for_timeout(2000)
                html = page.content()
                browser.close()
                return parse_html(html)
        except Exception as e:
            print(f"  ❌ All Plans Failed for Music: {e}")
            return []

    # 🌍 K-Culture: 구글 트렌드 (Plan A -> B -> C)
    def _get_culture_trends(self):
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

        def parse_xml(xml_content):
            try:
                root = ET.fromstring(xml_content)
            except:
                # Playwright가 HTML로 감싸서 반환할 경우를 대비한 BeautifulSoup 파싱
                soup = BeautifulSoup(xml_content, 'html.parser')
                items = soup.find_all('item')
                chart = []
                rank = 1
                for item in items[:10]:
                    title = item.find('title').text
                    traffic = item.find('ht:approx_traffic')
                    info = f"Hits: {traffic.text}" if traffic else "Hot" # 💡 [수정] "Searches: 10K" -> "Hits: 10K"
                    chart.append({"rank": rank, "title": title, "info": info, "score": 101 - rank})
                    rank += 1
                return chart

            items = root.findall('.//item')
            chart = []
            rank = 1
            for item in items[:10]:
                title = item.find('title').text
                traffic = item.find('{https://trends.google.com/trends/trendingsearches/daily}approx_traffic')
                info = f"Hits: {traffic.text.replace('+', '')}" if traffic is not None else "Hot" # 💡 [수정] 기호 제거
                chart.append({"rank": rank, "title": title, "info": info, "score": 101 - rank})
                rank += 1
            return chart

        # 🛡️ Plan A
        try:
            res = requests.get(url, headers=headers, timeout=10)
            chart = parse_xml(res.content)
            if chart: return chart
        except: pass

        # 🕵️‍♂️ Plan B
        print("  🕵️ Plan B (Proxy) for Culture Trends...")
        try:
            res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=15)
            chart = parse_xml(res.content)
            if chart: return chart
        except: pass

        # 🚜 Plan C
        print("  🚜 Plan C (Playwright) for Culture Trends...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, proxy=self.playwright_proxy)
                page = browser.new_page(user_agent=headers["User-Agent"])
                page.goto(url, timeout=20000)
                page.wait_for_timeout(2000)
                content = page.content()
                browser.close()
                return parse_xml(content)
        except Exception as e:
            print(f"  ❌ All Plans Failed for Culture Trends: {e}")
            return []
