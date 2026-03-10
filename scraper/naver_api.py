import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import urllib3
from urllib.parse import quote
from google import genai
from email.utils import parsedate_to_datetime

# SSL 프록시 접속 경고창 영구 숨김 처리
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NaverNewsAPI:
    def __init__(self, db_client):
        self.db = db_client
        
        # API 키 세팅
        self.naver_id = os.environ.get("NAVER_CLIENT_ID")
        self.naver_secret = os.environ.get("NAVER_CLIENT_SECRET")
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        
        if self.gemini_key:
            self.ai_client = genai.Client(api_key=self.gemini_key)

        self.naver_headers = {
            "X-Naver-Client-Id": self.naver_id,
            "X-Naver-Client-Secret": self.naver_secret
        }

    def run_pipeline(self, category):
        print(f"\n🚀 [AI Newsroom] Starting Pipeline for category: {category}")
        
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        time_limit = now_kst - timedelta(hours=24) # 💡 정확히 24시간 전 시간 기록
        print(f"  🕒 Current KST Time: {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  ⌛ 24-Hour Limit: Only articles after {time_limit.strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.naver_id or not self.naver_secret:
            print("  ❌ Error: NAVER_CLIENT_ID or NAVER_CLIENT_SECRET missing.")
            return

        # =========================================================
        # Step 1. 🧹 듀얼 DB 청소 (24시간 & 7일 컷오프)
        # =========================================================
        print("  🧹 Step 1: Cleaning up old database records...")
        try:
            one_day_ago = (now_kst - timedelta(days=1)).isoformat()
            seven_days_ago = (now_kst - timedelta(days=7)).isoformat()
            
            self.db.client.table("live_news").delete().lt("created_at", one_day_ago).execute()
            self.db.client.table("search_archive").delete().lt("created_at", seven_days_ago).execute()
            print("    ✅ Cleanup complete.")
        except Exception as e:
            print(f"    ⚠️ DB Cleanup Error: {e}")

        # =========================================================
        # Step 2. 🚫 블랙리스트(최근 20명) 추출
        # =========================================================
        print("  🚫 Step 2: Fetching blacklist (Recent 20 names)...")
        blacklist = []
        try:
            res = self.db.client.table("live_news").select("keyword").eq("category", category).order("created_at", desc=True).limit(20).execute()
            if res.data:
                blacklist = [item['keyword'] for item in res.data if item.get('keyword')]
            print(f"    ✅ Blacklist size: {len(blacklist)} names.")
        except Exception as e:
            print(f"    ⚠️ Blacklist Fetch Error: {e}")

        # =========================================================
        # Step 3. 📡 광역 스캔 및 새로운 10명 발굴 (24시간 필터 & '|' 연산자 적용)
        # =========================================================
        base_queries = {
            'k-pop': '아이돌 | 걸그룹 | 보이그룹 | 컴백 | 신곡',
            'k-movie': '한국영화 | 영화배우 | 박스오피스 | 무대인사 | 극장가',
            'k-drama': '한국드라마 | 드라마배우 | 시청률 | 넷플릭스 | 첫방송',
            'k-entertain': '예능프로그램 | 방송인 | 유재석 | 하차 | 합류'
        }
        query = base_queries.get(category, '연예계')

        print(f"  📡 Step 3: Scanning latest news articles for '{query}'...")
        search_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(query)}&display=100&sort=date"
        
        valid_snippets = []
        try:
            res = requests.get(search_url, headers=self.naver_headers, timeout=10)
            res.raise_for_status()
            raw_news = res.json().get('items', [])
            
            # 100개의 기사 중 정확히 24시간 이내의 기사만 필터링
            for n in raw_news:
                try:
                    pub_date = parsedate_to_datetime(n['pubDate']).astimezone(kst)
                    if pub_date >= time_limit:
                        valid_snippets.append({"title": n['title'], "desc": n['description']})
                except:
                    pass
        except Exception as e:
            print(f"    ❌ Naver API Error: {e}")
            return

        if not valid_snippets:
            print("    ❌ No valid articles found within the last 24 hours.")
            return

        print(f"    🧠 Asking AI to extract 10 NEW celebrities from {len(valid_snippets)} fresh articles...")
        prompt_extract = f"""
        Analyze these recent Korean entertainment news snippets (all within the last 24 hours).
        Extract exactly 10 names of the most trending PEOPLE (celebrities, singers, actors, idol groups).
        
        CRITICAL RULES:
        1. ONLY extract REAL PEOPLE or IDOL GROUPS. Do NOT extract movie titles, drama titles, TV show names, or character names.
        2. EXCLUDE these names entirely (Blacklist): {blacklist}
        3. Return ONLY a valid JSON array of strings. Format: ["Name1", "Name2", ...]
        
        News snippets: {json.dumps(valid_snippets[:100], ensure_ascii=False)}
        """
        try:
            ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt_extract)
            text = ai_res.text.replace("```json", "").replace("```", "").strip()
            candidate_names = json.loads(text)
        except Exception as e:
            print(f"    ❌ AI Extraction Error: {e}")
            return

        # =========================================================
        # Step 3.5. 📚 celebrity_dict 크로스 체크 및 자가 학습
        # =========================================================
        print(f"  📚 Step 3.5: Cross-checking {len(candidate_names)} names with celebrity_dict...")
        validated_names = []
        try:
            dict_res = self.db.client.table("celebrity_dict").select("name").execute()
            existing_celebs = [item['name'] for item in dict_res.data] if dict_res.data else []

            for name in candidate_names[:10]:
                if name in existing_celebs:
                    validated_names.append(name)
                    print(f"    ✔️ [PASS] Existing celebrity: {name}")
                else:
                    verify_prompt = f"Is '{name}' a real, currently active Korean celebrity, singer, actor, or idol group? Answer ONLY with valid JSON: {{\"is_celeb\": true or false}}"
                    v_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=verify_prompt)
                    v_data = json.loads(v_res.text.replace("```json", "").replace("```", "").strip())
                    
                    if v_data.get("is_celeb"):
                        self.db.client.table("celebrity_dict").insert({"name": name, "default_category": "pending"}).execute()
                        validated_names.append(name)
                        print(f"    ✨ [NEW] Learned and added new celebrity: {name}")
                    else:
                        print(f"    🗑️ [DROP] Discarded non-celebrity/trash data: {name}")
        except Exception as e:
            print(f"    ⚠️ Cross-check Error: {e}")
            validated_names = candidate_names[:10]

        if not validated_names:
            print("  ❌ No valid celebrities found to process. Exiting current run.")
            return

        # =========================================================
        # Step 4 & 5. 📝 심층 취재, 채점, 카테고리 검열, 이미지 생존 검증
        # =========================================================
        print(f"  📝 Step 4: Deep Dive & Article Generation for {len(validated_names)} targets...")
        
        # 💡 [확장된 카테고리 룰] 연예계 공식 활동 전반으로 범위 대폭 확대!
        category_rules = {
            'k-pop': 'music releases, concerts, fan meetings, music charts, official idol group activities, agency announcements, music show appearances, and official promotional events (photoshoots, brand endorsements).',
            'k-movie': 'movie casting, film production, box office results, theatrical releases, film festivals, actor interviews, movie promotional events (press cons, red carpets), and official actor activities.',
            'k-drama': 'drama/OTT series casting, TV broadcasting, viewer ratings, plot details, drama awards, script readings, drama OSTs, and actor interviews about their roles.',
            'k-entertain': 'variety shows, reality TV, comedy programs, TV or YouTube talk shows (e.g., web entertainment), MC/hosting activities, and entertainer interviews.'
        }
        strict_rule = category_rules.get(category, 'professional entertainment activities.')

        final_results = []

        for name in validated_names:
            print(f"\n    🔍 Investigating: {name}")
            
            # 넉넉히 10개를 가져와서 24시간 이내 기사만 추려낸 뒤, 상위 3개만 사용
            p_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(name)}&display=10&sort=sim"
            try:
                p_res = requests.get(p_url, headers=self.naver_headers, timeout=10)
                raw_articles = p_res.json().get('items', [])
            except:
                continue

            valid_articles = []
            for art in raw_articles:
                try:
                    pub_date = parsedate_to_datetime(art['pubDate']).astimezone(kst)
                    if pub_date >= time_limit:
                        valid_articles.append(art)
                except:
                    pass
            
            articles = valid_articles[:3]

            if not articles:
                print(f"      ⏭️ No news within 24 hours. Skipping {name}.")
                continue

            content_pool = ""
            best_img_url = ""
            main_link = articles[0]['link']

            headers = {"User-Agent": "Mozilla/5.0"}
            for art in articles:
                try:
                    c_res = requests.get(art['link'], headers=headers, timeout=5, verify=False)
                    soup = BeautifulSoup(c_res.text, 'html.parser')
                    
                    # 💡 [본문 긁어오기 강화] 연예, 스포츠, 일반 뉴스 상자 모두 포함
                    body = soup.select_one("#dic_area, #artc_body, #articleBody, .article_body, .news_end, .end_body_wrp")
                    if body: 
                        content_pool += body.get_text(separator=' ', strip=True)[:1000] + " \n"
                    else:
                        # 💡 [백업 플랜] 상자가 없으면 <p> 태그라도 긁어오기
                        paragraphs = soup.find_all('p')
                        backup_text = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
                        if backup_text:
                            content_pool += backup_text[:1000] + " \n"
                    
                    if not best_img_url:
                        meta_img = soup.find("meta", property="og:image")
                        if meta_img and meta_img.get("content"):
                            candidate_img = meta_img["content"].strip()
                            blacklist_img = ["dummy", "naver_logo", "default", "no_image"]
                            if not any(bad in candidate_img.lower() for bad in blacklist_img):
                                check = requests.head(candidate_img, timeout=1, verify=False)
                                if check.status_code == 200:
                                    best_img_url = candidate_img
                except:
                    continue

            if len(content_pool) < 100:
                print(f"      ⏭️ Not enough content. Skipping {name}.")
                continue

            # 💡 [핵심 프롬프트 업데이트] 한글 강제, 본문 영어 번역, 인지도(Fame) 기반 채점, 사생활/사건사고 배제
            write_prompt = f"""
            You are a strict, factual English K-Entertainment news editor.
            Read the extracted news text about '{name}' and write a summary.
            
            CRITICAL RULES:
            1. Title Format: MUST BE EXACTLY `[{name}] English Title`. Do NOT translate '{name}' in the brackets. Keep the brackets exactly as `[{name}]`.
            2. Language: The summary body MUST be 100% in English. Translate all movie/drama titles and proper nouns to English. DO NOT output any Korean characters in the "summary" field.
            3. Length: 3 to 5 sentences.
            4. SCORING (50-100): Score based PRIMARILY on the GLOBAL FAME/POPULARITY of '{name}'.
               - A-list / World-class stars (e.g., BTS, Top Actors): 90~100
               - Well-known stars: 75~89
               - Rookies, unknown/minor actors: 50~74.
            5. RELEVANCE CHECK (CRITICAL - READ CAREFULLY): 
               The current target category is '{category}'.
               This category accepts news about: {strict_rule}
               If the news is PURELY about unrelated private life (e.g., crimes, home invasions, accidents, real estate) without ANY connection to their professional entertainment career, or entirely about a different field (e.g., a singer acting in a movie but the category is k-pop), you MUST set "is_valid_category": false. Otherwise, true.
            6. Output valid JSON ONLY.
            
            Content:
            {content_pool}
            
            JSON Format:
            {{
                "is_valid_category": true,
                "title": "[{name}] Title in English...",
                "summary": "Summary in English...",
                "score": 85
            }}
            """
            try:
                ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=write_prompt)
                data = json.loads(ai_res.text.replace("```json", "").replace("```", "").strip())
                
                # 카테고리에 안 맞거나 단순 사생활이면 가차 없이 스킵!
                if not data.get("is_valid_category", True):
                    print(f"      ⏭️ Irrelevant to {category} (e.g. Personal life, CF, wrong field). Skipping {name}.")
                    continue
                
                score = int(data.get("score", 70))
                score = max(50, min(100, score))

                final_results.append({
                    "category": category,
                    "keyword": name,
                    "title": data.get("title", f"[{name}] Untitled"),
                    "summary": data.get("summary", ""),
                    "link": main_link,
                    "image_url": best_img_url,
                    "score": score,
                    "likes": 0
                })
                print(f"      ✅ Generated: {data.get('title')} (Score: {score})")
            except Exception as e:
                print(f"      ❌ Article Gen Error for {name}: {e}")

        # =========================================================
        # Step 6. 💾 듀얼 DB 저장 및 '최대 50개' 용량 통제
        # =========================================================
        if final_results:
            print(f"  💾 Step 6: Saving {len(final_results)} articles to databases...")
            try:
                self.db.client.table("search_archive").insert(final_results).execute()
                self.db.client.table("live_news").insert(final_results).execute()
                print("    ✅ Insertion complete.")

                count_res = self.db.client.table("live_news").select("id", count="exact").eq("category", category).execute()
                total_count = count_res.count

                if total_count and total_count > 50:
                    excess = total_count - 50
                    print(f"    ⚠️ Capacity limit exceeded ({total_count}/50). Purging {excess} lowest scored items...")
                    
                    low_res = self.db.client.table("live_news").select("id").eq("category", category).order("score", asc=True).limit(excess).execute()
                    if low_res.data:
                        drop_ids = [item['id'] for item in low_res.data]
                        self.db.client.table("live_news").delete().in_("id", drop_ids).execute()
                        print(f"    🗑️ Purged {len(drop_ids)} low-score items.")

            except Exception as e:
                print(f"    ❌ DB Save/Purge Error: {e}")

        print(f"🎉 [AI Newsroom] Pipeline for '{category}' successfully completed!")
