import os
import json
import requests
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
        self.tmdb_key = os.environ.get("TMDB_API_KEY") 
        
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        if self.gemini_key:
            self.ai_client = genai.Client(api_key=self.gemini_key)
        
        # (참고: 이제 스크래핑을 하지 않으므로 프록시는 사실상 사용되지 않지만, 
        # 기존 환경 변수 호환성을 위해 세팅만 남겨둡니다.)
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

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def update_chart(self, category):
        results = []
        if category == 'k-movie':
            results = self._get_kobis_box_office()
        elif category == 'k-drama':
            results = self._get_tmdb_ranking(is_drama=True)
        elif category == 'k-entertain':
            results = self._get_tmdb_ranking(is_drama=False)
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
          For non-music categories (Daily:, Pop:, Views:, Search:), leave the 'info' text exactly as it is.
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

    # 🎬 1. K-Movie: 영화진흥위원회(KOBIS) 박스오피스 API
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

    # 📺 2. K-Drama & K-Entertain: TMDB 공식 API (최신 방영작 날짜 필터링 적용!)
    def _get_tmdb_ranking(self, is_drama=True):
        if not self.tmdb_key:
            print("  ❌ Error: TMDB_API_KEY is missing.")
            return []
            
        kst = pytz.timezone('Asia/Seoul')
        today = datetime.now(kst)
        
        if is_drama:
            # 드라마: 최근 6개월 이내 첫 방영
            six_months_ago = (today - timedelta(days=120)).strftime('%Y-%m-%d')
            genre_filter = "&without_genres=10764,10767,10763"
            date_filter = f"&first_air_date.gte={six_months_ago}"
        else:
            # 예능: 최근 1개월 이내 새 에피소드 방영
            one_month_ago = (today - timedelta(days=30)).strftime('%Y-%m-%d')
            today_str = today.strftime('%Y-%m-%d')
            genre_filter = "&with_genres=10764|10767"
            date_filter = f"&air_date.gte={one_month_ago}&air_date.lte={today_str}"

        url = f"https://api.themoviedb.org/3/discover/tv?api_key={self.tmdb_key}&with_original_language=ko{genre_filter}{date_filter}&sort_by=popularity.desc&language=ko-KR"
        
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

    # 🎵 3. K-POP: 유튜브(YouTube) Data API v3 (인기 급상승 음악)
    def _get_music_chart(self):
        youtube_key = os.environ.get("YOUTUBE_API_KEY")
        if not youtube_key:
            print("  ❌ Error: YOUTUBE_API_KEY is missing.")
            return []

        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&chart=mostPopular&regionCode=KR&videoCategoryId=10&maxResults=10&key={youtube_key}"
        
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            items = res.json().get('items', [])
            
            chart = []
            rank = 1
            for item in items:
                snippet = item.get('snippet', {})
                stats = item.get('statistics', {})
                
                title = snippet.get('title', 'Unknown')
                channel_name = snippet.get('channelTitle', 'Unknown') 
                views = int(stats.get('viewCount', 0)) 
                
                formatted_views = f"{views:,}"
                
                chart.append({
                    "rank": rank,
                    "title": title,
                    "info": f"By {channel_name} (Views: {formatted_views})", 
                    "score": 101 - rank
                })
                rank += 1
            return chart
            
        except Exception as e:
            print(f"  ❌ YouTube API Error: {e}")
            return []

    # 🌍 4. K-Culture: 구글 트렌드 공식 RSS (한국 일일 인기 검색어)
    def _get_culture_trends(self):
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"
        
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            res.raise_for_status()
            
            import xml.etree.ElementTree as ET
            root = ET.fromstring(res.text)
            
            chart = []
            rank = 1
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text
                
                traffic_info = "Hot Trend"
                for child in item:
                    if 'approx_traffic' in child.tag:
                        traffic_info = f"Search: {child.text}"
                        
                chart.append({
                    "rank": rank,
                    "title": title,
                    "info": traffic_info, 
                    "score": 101 - rank
                })
                rank += 1
            return chart
            
        except Exception as e:
            print(f"  ❌ Google Trends Error: {e}")
            return []
