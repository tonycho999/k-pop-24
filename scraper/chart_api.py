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

# ✅ ModelManager 같은 폴더에서 임포트 (경로 에러 방지)
from model_manager import ModelManager 

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
            # ✅ ModelManager 초기화 (제미나이 공급자로 설정)
            self.model_manager = ModelManager(client=self.ai_client, provider="gemini")

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def update_chart(self, category):
        # 💡 K-Culture는 별도의 AI 매거진 파이프라인을 타고 live_news 테이블로 직행합니다.
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

    # 🚀 AI K-Culture 매거진 에디터 파이프라인 (델타 업데이트 & 10개 항시 유지 & 아마존 키워 추출)
    def _update_k_culture_magazine(self):
        print("  🚀 Starting K-Culture Magazine Delta Update with Amazon Monetization...")
        if not self.naver_id or not self.naver_secret:
            print("  ❌ Error: NAVER_CLIENT_ID or NAVER_CLIENT_SECRET is missing.")
            return

        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            print("  ❌ Error: SUPABASE_URL or SUPABASE_KEY is missing.")
            return

        supa_headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }

        naver_headers = {
            "X-Naver-Client-Id": self.naver_id,
            "X-Naver-Client-Secret": self.naver_secret
        }

        # ✅ 파이프라인 실행 시 동적으로 가장 좋은 모델 1개 선택
        best_model = self.model_manager.get_best_model() if hasattr(self, 'model_manager') else 'gemini-2.5-flash'
        print(f"  🤖 Loaded Dynamic AI Model: {best_model}")

        categories = {
            'k-food': '먹거리 유행',
            'k-beauty': '뷰티 트렌드',
            'k-fashion': '패션 유행',
            'k-lifestyle': '라이프스타일 트렌드'
        }

        for sub_cat, query in categories.items():
            print(f"\n  [{sub_cat}] Fetching news & analyzing trends...")
            try:
                # 0. 기존 DB에서 현재 Top 10 데이터 가져오기 (비교용)
                get_url = f"{supabase_url}/rest/v1/live_news?category=eq.{sub_cat}&select=id,title,summary,score,likes"
                old_res = requests.get(get_url, headers=supa_headers)
                old_items = old_res.json() if old_res.status_code == 200 else []
                
                # 기존 타이틀을 딕셔너리로 저장하여 매칭에 사용
                old_dict = {item['title']: item for item in old_items}
                old_titles_list = list(old_dict.keys())

                # 1. 네이버 뉴스 검색 API 호출 (한국어 원문 수집)
                news_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(query)}&display=20&sort=sim"
                news_res = requests.get(news_url, headers=naver_headers, timeout=10)
                news_res.raise_for_status()
                items = news_res.json().get('items', [])

                snippets = [{"title": re.sub(r'<[^>]+>', '', i['title']), "desc": re.sub(r'<[^>]+>', '', i['description'])} for i in items]

                # 2. 제미나이(Gemini) 프롬프트 (아마존 키워드 추출 포함) - 💡 여유 있게 15개 요청
                prompt = f"""
                You are a K-Culture Magazine Editor. Analyze these recent Korean news snippets about {sub_cat} and identify the Top 15 hottest trends.
                
                CRITICAL RULE FOR FILTERING:
                You MUST ONLY extract trends that perfectly match the '{sub_cat}' category. 
                If an article mentions '{sub_cat}' but its main focus shifts to another category (e.g., "expanding from food to fashion"), COMPLETELY IGNORE IT.
                For example, if the category is 'k-food', completely IGNORE any news about fashion, cosmetics, or travel.
                If there are not enough relevant trends, just return a smaller array. DO NOT invent or use unrelated news.
                
                CRITICAL RULE FOR TITLES:
                Here are the previous Top 10 trend titles: {old_titles_list}
                If a current trend is about the EXACT SAME TOPIC as one of the previous titles, you MUST use the EXACT SAME string from the previous titles list. Do not rephrase it.
                If it is a completely new trend, create a new Catchy English Title.

                Return ONLY a valid JSON array of objects. Format:
                [
                  {{
                      "title": "Exact old title OR Catchy new English title",
                      "summary": "2-3 sentences in English explaining what the item is and why it's popular.",
                      "keyword": "A short exact Korean noun for image search (e.g., '두바이 초콜릿')",
                      "amazon_keyword": "1-4 English words to buy this on Amazon. IT MUST STRICTLY BELONG TO THE '{sub_cat}' CATEGORY (e.g., if k-food, MUST be an edible food item like 'Korean spicy ramen', NEVER clothing or makeup).",
                      "score": <integer from 15 (1st) down to 1 (15th)>
                  }}
                ]
                
                News snippets: {json.dumps(snippets, ensure_ascii=False)}
                """
                
                # ✅ 신형 API 문법(`config=`) 및 동적 모델(`best_model`) 적용 완료!
                ai_res = self.ai_client.models.generate_content(
                    model=best_model, 
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                
                # JSON 파싱
                trends = json.loads(ai_res.text)

                # 💡 [안전장치 추가] 딕셔너리로 응답이 왔다면 안쪽에 있는 리스트를 강제로 꺼냄
                if isinstance(trends, dict):
                    # 보통 딕셔너리 안에 밸류값으로 리스트가 들어있으므로 그것을 추출
                    trends = next(iter(trends.values())) if trends else []
                    
                    # 혹시나 리스트가 아니라 단일 객체 하나만 덜렁 왔다면 리스트로 감싸줌
                    if isinstance(trends, dict):
                        trends = [trends]

                # 3. 데이터 비교 및 델타 업데이트 실행
                processed_count = 0 # 💡 성공적으로 처리된(이미지가 있는) 기사 수를 셉니다.

                for t in trends:
                    if processed_count >= 10:
                        break # 💡 10개가 채워지면 루프 종료!

                    title = t.get('title', 'Unknown Trend')
                    new_summary = t.get('summary', '')
                    new_score = 10 - processed_count # 💡 순위를 10점 만점부터 차례대로 재부여합니다.
                    keyword = t.get('keyword', '') 
                    
                    # 아마존 키워드 가져오기
                    default_keyword = f"Korean {sub_cat.replace('k-', '')}"
                    amazon_keyword = t.get('amazon_keyword', default_keyword).strip()

                    # 💡 이미지 유효성 검사를 먼저 수행합니다!
                    img_url = ""
                    if keyword:
                        img_search_url = f"https://openapi.naver.com/v1/search/image?query={quote(keyword)}&display=3&sort=sim"
                        try:
                            img_res = requests.get(img_search_url, headers=naver_headers, timeout=5)
                            if img_res.status_code == 200:
                                img_items = img_res.json().get('items', [])
                                for img_item in img_items:
                                    candidate_url = img_item.get('link', '')
                                    try:
                                        check = requests.head(candidate_url, timeout=2, verify=False)
                                        if check.status_code == 200:
                                            # ✅ [이미지 유효성 추가 검증] 응답 헤더의 Content-Type이 진짜 이미지인지 확인
                                            content_type = check.headers.get('Content-Type', '')
                                            if content_type.startswith('image/'):
                                                img_url = candidate_url
                                                break 
                                    except:
                                        continue 
                        except Exception as e:
                            print(f"      ⚠️ Image Search API Error for '{keyword}': {e}")

                    # 💡 유효한 이미지를 찾지 못했다면 포기하고 다음 트렌드로 넘어갑니다. (개수 카운트 안 함)
                    if not img_url and title not in old_dict: # 기존 DB에 있는 건 이미지 재활용 가능성을 위해 일단 패스 (기존 로직 유지)
                         print(f"      ⏭️ No valid image found for '{keyword}'. Dropping trend: {title}")
                         continue

                    # 여기서부터는 이미지가 확인되었거나, 기존 DB에 있던 기사입니다.
                    processed_count += 1 # 성공 카운트 증가

                    if title in old_dict:
                        # [유지 & 업데이트]
                        old_item = old_dict[title]
                        item_id = old_item['id']
                        
                        if old_item['summary'] != new_summary or old_item['score'] != new_score:
                            patch_data = {
                                "summary": new_summary, 
                                "score": new_score,
                                "amazon_keyword": amazon_keyword
                            }
                            patch_res = requests.patch(f"{supabase_url}/rest/v1/live_news?id=eq.{item_id}", headers=supa_headers, json=patch_data)
                            
                            if patch_res.status_code >= 400:
                                print(f"      ❌ DB Update Error ({title}): {patch_res.text}")
                            else:
                                print(f"      🔄 Updated: {title} (Amazon: {amazon_keyword})")
                        else:
                            print(f"      ➖ Kept (No change): {title}")
                            
                    else:
                        # [신규 진입] - 위에서 img_url을 이미 확보했습니다.
                        post_data = {
                            "category": sub_cat,
                            "keyword": keyword, 
                            "title": title,
                            "summary": new_summary,
                            "link": "",
                            "image_url": img_url,
                            "score": new_score,
                            "likes": 0,
                            "amazon_keyword": amazon_keyword 
                        }
                        post_res = requests.post(f"{supabase_url}/rest/v1/live_news", headers=supa_headers, json=post_data)
                        
                        if post_res.status_code >= 400:
                            print(f"      ❌ DB Insert Error ({title}): {post_res.text}")
                        else:
                            print(f"      ✨ New Entry: {title} (Amazon: {amazon_keyword})")

                # 4. 💡 10개 한도 룰 적용
                try:
                    count_url = f"{supabase_url}/rest/v1/live_news?category=eq.{sub_cat}&select=id"
                    current_res = requests.get(count_url, headers=supa_headers)
                    if current_res.status_code == 200:
                        current_items = current_res.json()
                        total_count = len(current_items)
                        
                        if total_count > 10:
                            excess = total_count - 10
                            oldest_url = f"{supabase_url}/rest/v1/live_news?category=eq.{sub_cat}&select=id&order=created_at.asc&limit={excess}"
                            oldest_res = requests.get(oldest_url, headers=supa_headers)
                            
                            if oldest_res.status_code == 200:
                                drop_ids = [str(item['id']) for item in oldest_res.json()]
                                if drop_ids:
                                    del_url = f"{supabase_url}/rest/v1/live_news?id=in.({','.join(drop_ids)})"
                                    requests.delete(del_url, headers=supa_headers)
                                    print(f"      🗑️ Dropped {excess} oldest items to maintain exactly 10.")
                except Exception as e:
                    print(f"      ⚠️ Cleanup Error: {e}")

                time.sleep(3) 

            except Exception as e:
                print(f"    ❌ Error processing {sub_cat}: {e}")

        print("  🎉 K-Culture Magazine Delta Update Complete!")

    # 🤖 AI 영문 일괄 번역기 (K-Pop, K-Movie 등 기존 차트용)
    def _translate_chart_titles(self, chart_data, category):
        if not hasattr(self, 'ai_client') or not self.ai_client:
            return chart_data

        items_to_translate = [{"title": item['title'], "info": item['info']} for item in chart_data]
        
        # ✅ 번역 파이프라인에도 동적 모델 적용
        best_model = self.model_manager.get_best_model() if hasattr(self, 'model_manager') else 'gemini-2.5-flash'

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
            # ✅ 신형 문법 적용
            ai_res = self.ai_client.models.generate_content(
                model=best_model, 
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            translated_items = json.loads(ai_res.text)
            
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
