import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import urllib3
import xml.etree.ElementTree as ET

# 💡 보기 흉한 SSL 프록시 접속 경고창(InsecureRequestWarning) 영구 숨김 처리
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ChartAPI:
    def __init__(self, db):
        self.db = db
        self.kobis_key = os.environ.get("KOBIS_API_KEY") 
        
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

    # 📺 드라마/예능: 네이버 시청률 크롤링 (프록시 & 3중 셀렉터 적용)
    def _get_naver_ratings(self, query):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        url = f"https://search.naver.com/search.naver?query={query}"
        chart = []
        try:
            res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            rows = soup.select('table.rate_table_info tbody tr') or soup.select('.tv_rating_table tbody tr') or soup.select('.list_info li')
            
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

    # 🎵 K-POP: 대한민국 1위 음원 차트 '멜론(Melon) Top 100' 실시간 스크래핑
    def _get_naver_music_chart(self):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        url = "https://www.melon.com/chart/index.htm"
        chart = []
        try:
            # 멜론 차트 접속 시 프록시 사용 (차단 방지)
            res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 멜론 차트는 .lst50 (1~50위) 와 .lst100 (51~100위) 로 나뉨
            songs = soup.select('.lst50, .lst100')
            rank = 1
            for song in songs[:10]:
                title = song.select_one('.ellipsis.rank01 a').text.strip()
                artist = song.select_one('.ellipsis.rank02 a').text.strip()
                chart.append({
                    "rank": rank,
                    "title": title,
                    "info": f"Artist: {artist}",
                    "score": 101 - rank
                })
                rank += 1
            return chart
        except Exception as e:
            print(f"  ❌ Music Chart Error: {e}")
            return []

    # 🌍 K-Culture: 구글 트렌드 (대한민국 실시간 급상승 검색어)
    def _get_culture_trends(self):
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"
        chart = []
        try:
            res = requests.get(url, proxies=self.proxies, verify=False, timeout=15)
            root = ET.fromstring(res.content)
            items = root.findall('.//item')
            rank = 1
            for item in items[:10]:
                title = item.find('title').text
                # 검색량 데이터 가져오기
                traffic = item.find('{https://trends.google.com/trends/trendingsearches/daily}approx_traffic')
                info = f"Searches: {traffic.text}" if traffic is not None else "Trending Now"
                
                chart.append({
                    "rank": rank,
                    "title": title,
                    "info": info,
                    "score": 101 - rank
                })
                rank += 1
            return chart
        except Exception as e:
            print(f"  ❌ Culture Trends Error: {e}")
            return []
