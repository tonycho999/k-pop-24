import os
import json
import requests
from datetime import datetime, timedelta
import pytz
import urllib3
import re
import time
from urllib.parse import quote
from google import genai

# SSL 프록시 접속 경고창 영구 숨김 처리
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ChartAPI:
    def __init__(self, db):
        self.db = db
        self.kobis_key = os.environ.get("KOBIS_API_KEY") 
        self.tmdb_key = os.environ.get("TMDB_API_KEY") 
        self.naver_id = os.environ.get("NAVER_CLIENT_ID")
        self.naver_secret = os.environ.get("NAVER_CLIENT_SECRET")
        
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        if self.gemini_key:
            self.ai_client = genai.Client(api_key=self.gemini_key)

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def update_chart(self, category):
        # 💡 [핵심 변경] K-Culture는 별도의 AI 매거진 파이프라인을 타고 live_news 테이블로 직행합니다.
        if category == 'k-culture':
            self._update_k_culture_magazine()
            return

        # 기존 차트 로직 (live_rankings 테이블 저장용)
        results = []
        if category == 'k-movie':
            results = self._get_kobis_box_office()
        elif category == 'k-drama':
            results = self._get_tmdb_ranking(is_drama=True)
        elif category == 'k-entertain':
            results = self._get_tmdb_ranking(is_drama=False)
        elif category == 'k-pop':
            results = self._get_music_chart()

        if results:
            results = self._translate_chart_titles(results, category)
            self.db.save_chart_results(category, results)
            print(f"  ✅ Chart updated for {category} ({len(results)} items saved).")
        else:
            print(f"  ⚠️ No chart data retrieved for {category}.")

    # 🚀 AI K-Culture 매거진 에디터 파이프라인 (네이버 검색 + 제미나이 기사 작성)
    def _update_k_culture_magazine(self):
        print("  🚀 Starting K-Culture Magazine Auto-Generation...")
        if not self.naver_id or not self.naver_secret:
            print("  ❌ Error: NAVER_CLIENT_ID or NAVER_CLIENT_SECRET is missing.")
            return

        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            print("  ❌ Error: SUPABASE_URL or SUPABASE_KEY is missing.")
            return

        # Supabase 직접 통신을 위한 헤더 세팅
        supa_headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }

        naver_headers = {
            "X-Naver-Client-Id": self.naver_id,
            "X-Naver-Client-Secret": self.naver_secret
        }

        # 카테고리별 네이버 뉴스 검색 키워드
        categories = {
            'k-food': '편의점 신상 OR 먹거리 유행 OR 디저트 인기',
            'k-beauty': '올리브영 인기 OR 뷰티 트렌드 OR 화장품 신제품',
            'k-fashion': '무신사 랭킹 OR 패션 유행 OR 요즘 코디',
            'k-lifestyle': '팝업스토어 OR 핫플레이스 OR 라이프스타일 트렌드'
        }

        for sub_cat, query in categories.items():
            print(f"  [{sub_cat}] Fetching news & generating trends...")
            try:
                # 1. 네이버 뉴스 검색 API 호출
                news_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(query)}&display=20&sort=sim"
                news_res = requests.get(news_url, headers=naver_headers, timeout=10)
                news_res.raise_for_status()
                items = news_res.json().get('items', [])

                # 뉴스 본문의 HTML 태그 깔끔하게 제거
                snippets = []
                for item in items:
                    title = re.sub(r'<[^>]+>', '', item['title'])
                    desc = re.sub(r'<[^>]+>', '', item['description'])
                    snippets.append({"title": title, "desc": desc})

                # 2. 제미나이(Gemini)에게 영문 기사 작성 지시
                prompt = f"""
                You are a K-Culture Magazine Editor. Analyze these recent Korean news snippets about {sub_cat}.
                Identify the Top 10 hottest trend items/topics in Korea right now.
                Return ONLY a valid JSON array of exactly 10 objects.
                Format for each object:
                {{
                    "title": "Catchy English Title (e.g., 'Dubai Chocolate Craze')",
                    "summary": "2-3 sentences in English explaining what the item is and why it's popular in Korea.",
                    "keyword": "A short exact Korean noun for image search (e.g., '두바이 초콜릿')",
                    "score": <integer from 100 (1st) down to 91 (10th)>
                }}
                News snippets: {json.dumps(snippets, ensure_ascii=False)}
                """
                ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                text = ai_res.text.replace("```json", "").replace("```", "").strip()
                trends = json.loads(text)

                # 3. 네이버 이미지 API로 썸네일 수집 및 DB 저장용 데이터 조립
                records = []
                for t in trends[:10]:
                    keyword = t.get('keyword', '')
                    img_url = ""
                    
                    if keyword:
                        img_search_url = f"https://openapi.naver.com/v1/search/image?query={quote(keyword)}&display=1&sort=sim"
                        img_res = requests.get(img_search_url, headers=naver_headers, timeout=5)
                        if img_res.status_code == 200:
                            img_items = img_res.json().get('items', [])
                            if img_items:
                                img_url = img_items[0].get('link', '')

                    records.append({
                        "category": sub_cat,
                        "title": t.get('title', 'Unknown Trend'),
                        "summary": t.get('summary', ''),
                        "image_url": img_url,
                        "score": t.get('score', 0),
                        "likes": 0
                    })

                # 4. Supabase DB 업데이트 (기존 카테고리 데이터 삭제 후 새 기사 삽입)
                requests.delete(f"{supabase_url}/rest/v1/live_news?category=eq.{sub_cat}", headers=supa_headers)
                requests.post(f"{supabase_url}/rest/v1/live_news", headers=supa_headers, json=records)

                print(f"    ✅ Saved 10 AI generated articles for {sub_cat}")
                time.sleep(3) # API 과부하 방지를 위한 3초 휴식

            except Exception as e:
                print(f"    ❌ Error processing {sub_cat}: {e}")

        print("  🎉 K-Culture Magazine Auto-Generation Complete!")

    # 🤖 AI 영문 일괄 번역기 (K-Pop, K-Movie 등 기존 차트용)
    def _translate_chart_titles(self, chart_data, category):
        if not hasattr(self, 'ai_client') or not self.ai_client:
            return chart_data

        items_to_translate = [{"title": item['title'], "info": item['info']} for item in chart_data]
        
        prompt = f"""
        You are an expert K-Culture data cleaner and translator. 
        Current Category: {category}
        
        Translate and format the following JSON list based on these strict rules:

        IF Category is 'k-pop':
        1. CLEAN TITLE: Extract ONLY the pure song title. Remove any artist names, "(Prod. by...)", "(feat...)", "[MV]", "(Official Video)", or "Artist - Title" formats.
        2. FIX ARTIST IN INFO: If the 'info' contains generic text like "Release - Topic" or the channel name is incorrect, extract the REAL artist name from the raw title and replace it.
        3. FORMAT INFO: Format the 'info' strictly as "By English Artist Name (Korean Name) (Views: X,XXX)". NEVER delete the Views number.

        IF Category is NOT 'k-pop':
        1. 'title': Translate Korean to natural English. Keep proper nouns Romanized.
        2. 'info': DO NOT change the 'info' text at all. Leave it exactly as it is.

        Must return ONLY a valid JSON array of objects containing 'title' and 'info' keys.
        
        Items to translate/clean:
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

    # 📺 2. K-Drama & K-Entertain: TMDB 공식 API 
    def _get_tmdb_ranking(self, is_drama=True):
        if not self.tmdb_key:
            print("  ❌ Error: TMDB_API_KEY is missing.")
            return []
            
        kst = pytz.timezone('Asia/Seoul')
        today = datetime.now(kst)
        
        if is_drama:
            six_months_ago = (today - timedelta(days=120)).strftime('%Y-%m-%d')
            genre_filter = "&without_genres=10764,10767,10763"
            date_filter = f"&first_air_date.gte={six_months_ago}"
        else:
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

    # 🎵 3. K-POP: 유튜브(YouTube) Data API v3 
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
