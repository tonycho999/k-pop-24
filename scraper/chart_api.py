import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz

class ChartAPI:
    def __init__(self, db):
        self.db = db
        self.kobis_key = os.environ.get("KOBIS_API_KEY") 
        
        # 💡 네이버 시청률 검색 우회를 위한 프록시 로드
        self.proxy_host = os.environ.get("PROXY_HOST")
        self.proxy_port = os.environ.get("PROXY_PORT")
        self.proxy_user = os.environ.get("PROXY_USER")
        self.proxy_pass = os.environ.get("PROXY_PASS")
        
        self.proxies = None
        if self.proxy_host and self.proxy_port and self.proxy_user and self.proxy_pass:
            proxy_url = f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}"
            self.proxies = {
                "http": proxy_url,
                "https": proxy_url
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
            results = self._get_naver_music_chart()
        elif category == 'k-culture':
            results = self._get_culture_trends()

        if results:
            self.db.save_chart_results(category, results)
            print(f"  ✅ Chart updated for {category} ({len(results)} items saved).")
        else:
            print(f"  ⚠️ No chart data retrieved for {category}.")

    # 🎬 영화: 영화진흥위원회(KOBIS) 박스오피스 API
    def _get_kobis_box_office(self):
        if not self.kobis_key:
            print("  ❌ Error: KOBIS_API_KEY is missing.")
            return []
            
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
                    "info": f"Daily Audience: {int(m['audiCnt']):,} | Total: {int(m['audiAcc']):,}",
                    "score": 101 - int(m['rank'])
                })
            return chart
        except Exception as e:
            print(f"  ❌ KOBIS API Error: {e}")
            return []

    # 📺 드라마/예능: 네이버 시청률 크롤링 (프록시 적용)
    def _get_naver_ratings(self, query):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        url = f"https://search.naver.com/search.naver?query={query}"
        chart = []
        try:
            res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            rows = soup.select('.tv_rating_table tbody tr') or soup.select('.list_info li')
            rank = 1
            for row in rows[:10]:
                title_el = row.select_one('.title a, .name a, th a')
                rate_el = row.select_one('.percent, .rate, td.rate')
                if title_el and rate_el:
                    chart.append({
                        "rank": rank,
                        "title": title_el.text.strip(),
                        "info": f"Rating: {rate_el.text.strip()}",
                        "score": 101 - rank
                    })
                    rank += 1
            return chart
        except Exception as e:
            print(f"  ❌ Naver Ratings Error (Proxy Failed): {e}")
            return []

    def _get_naver_music_chart(self):
        return [{"rank": i, "title": f"Top K-Pop Song #{i}", "info": "Music Chart Hot 10", "score": 101-i} for i in range(1, 11)]

    def _get_culture_trends(self):
        return [{"rank": i, "title": f"Viral Culture Trend #{i}", "info": "Trending Now", "score": 101-i} for i in range(1, 11)]
