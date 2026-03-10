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

    def run_pipeline(self, target_category):
        print(f"\n🚀 [AI Newsroom] Starting Pipeline (Search base: {target_category})")
        
        # =========================================================
        # Step 0. 🕒 한국 표준시(KST) 인지 및 24시간 데드라인 설정
        # =========================================================
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        time_limit = now_kst - timedelta(hours=24) # 정확히 24시간 전
        
        print(f"  🕒 Current KST Time: {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  ⌛ 24-Hour Limit: Only articles after {time_limit.strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.naver_id or not self.naver_secret:
            print("  ❌ Error: NAVER API keys missing.")
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
        # Step 2. 🚫 글로벌 블랙리스트 장착 (최근 40명 통합)
        # =========================================================
        print("  🚫 Step 2: Fetching global blacklist (Recent 40 names)...")
        blacklist = []
        try:
            # 💡 카테고리 상관없이 전체 DB에서 최신 40명 추출 (턴 간 중복 완벽 방어)
            res = self.db.client.table("live_news").select("keyword").order("created_at", desc=True).limit(40).execute()
            if res.data:
                blacklist = [item['keyword'] for item in res.data if item.get('keyword')]
            print(f"    ✅ Global Blacklist size: {len(blacklist)} names.")
        except Exception as e:
            print(f"    ⚠️ Blacklist Fetch Error: {e}")

        # =========================================================
        # Step 3. 📡 맞춤 스캔 및 15명 후보 발굴 (24시간 필터)
        # =========================================================
        base_queries = {
            'k-pop': '아이돌 | 걸그룹 | 보이그룹 | 컴백 | 신곡 | 콘서트',
            'k-movie': '한국영화 | 영화배우 | 박스오피스 | 무대인사 | 시사회',
            'k-drama': '한국드라마 | 드라마배우 | 시청률 | 넷플릭스 | 캐스팅',
            'k-entertain': '예능프로그램 | 예능인 | 코미디언 | 유재석 | 관찰예능'
        }
        query = base_queries.get(target_category, '연예계')

        print(f"  📡 Step 3: Scanning latest news articles for '{query}'...")
        search_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(query)}&display=100&sort=date"
        
        valid_snippets = []
        try:
            res = requests.get(search_url, headers=self.naver_headers, timeout=10)
            res.raise_for_status()
            raw_news = res.json().get('items', [])
            
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

        print(f"    🧠 Asking AI to extract 15 NEW celebrities from {len(valid_snippets)} fresh articles...")
        prompt_extract = f"""
        Extract exactly 15 names of trending PEOPLE (celebrities, singers, actors) from these snippets.
        RULES:
        1. REAL PEOPLE ONLY. Do NOT extract movie/drama titles.
        2. EXCLUDE BLACKLIST: {blacklist}
        3. OUTPUT FORMAT: valid JSON array of strings `["Name1", "Name2", ...]`
        
        Snippets: {json.dumps(valid_snippets[:100], ensure_ascii=False)}
        """
        try:
            ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt_extract)
            text = ai_res.text.replace("```json", "").replace("```", "").strip()
            candidate_names = json.loads(text)
        except Exception as e:
            print(f"    ❌ AI Extraction Error: {e}")
            return

        # =========================================================
        # Step 3.5. 📚 celebrity_dict 크로스 체크 (인물사전 검증)
        # =========================================================
        print(f"  📚 Step 3.5: Cross-checking {len(candidate_names)} names with celebrity_dict...")
        validated_names = []
        try:
            dict_res = self.db.client.table("celebrity_dict").select("name").execute()
            existing_celebs = [item['name'] for item in dict_res.data] if dict_res.data else []

            for name in candidate_names[:15]:
                if name in existing_celebs:
                    validated_names.append(name)
                else:
                    verify_prompt = f"Is '{name}' a real Korean celebrity? Answer ONLY with valid JSON: {{\"is_celeb\": true or false}}"
                    v_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=verify_prompt)
                    v_data = json.loads(v_res.text.replace("```json", "").replace("```", "").strip())
                    
                    if v_data.get("is_celeb"):
                        self.db.client.table("celebrity_dict").insert({"name": name, "default_category": "pending"}).execute()
                        validated_names.append(name)
        except Exception as e:
            print(f"    ⚠️ Cross-check Error: {e}")
            validated_names = candidate_names[:15]

        if not validated_names:
            print("  ❌ No valid celebrities found to process. Exiting current run.")
            return

        # =========================================================
        # Step 4. 📝 심층 취재 및 썸네일 검증, AI 투트랙 라우팅
        # =========================================================
        print(f"  📝 Step 4: Deep Dive & AI Smart Routing for {len(validated_names)} targets...")
        final_results = []

        for name in validated_names:
            print(f"\n    🔍 Investigating: {name}")
            
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
                    
                    # 💡 본문 상자 통합 추출 & 백업 플랜
                    body = soup.select_one("#dic_area, #artc_body, #articleBody, .article_body, .news_end, .end_body_wrp")
                    if body: 
                        content_pool += body.get_text(separator=' ', strip=True)[:1000] + " \n"
                    else:
                        paragraphs = soup.find_all('p')
                        backup_text = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
                        if backup_text: 
                            content_pool += backup_text[:1000] + " \n"
                    
                    # 💡 이미지 생존(핑) 테스트
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

            # 💡 [핵심 프롬프트] 비용 방어 + 투트랙(업무 크로스오버 & 사생활 본업회귀) 라우팅
            write_prompt = f"""
            You are a K-Entertainment news editor analyzing news about '{name}'.
            
            STEP 1: FILTERING GARBAGE (COST SAVING)
            If the news is purely a product advertisement (CF), SEO spam, or non-celebrity corporate/stock news, output ONLY: {{"category": "discard"}}
            
            STEP 2: SMART CATEGORY ASSIGNMENT (ALLOW PRIVATE LIFE & CROSSOVER)
            If it's valid entertainment news (INCLUDING dating, marriage, scandals, crimes, military enlistment, etc.), assign the BEST category:
            - TRACK A (Project-based Crossover): If the news is about a specific project, use its category (e.g., Singer appearing on a Variety Show -> "k-entertain").
            - TRACK B (Personal Life / Scandals fallback): If the news is about their private life/scandal, assign it to the category of their MAIN PROFESSION (e.g., an Idol's dating news -> "k-pop", an Actor's scandal -> "k-movie" or "k-drama", an MC's real estate -> "k-entertain").
            
            STEP 3: WRITING & SCORING
            Write an English title EXACTLY as `[{name}] English Title` (Do not translate the name inside the brackets).
            Write a 3-5 sentence English summary (NO Korean characters allowed).
            Score 50-100 based on GLOBAL FAME and SHOCK VALUE (Major scandals/dating of famous stars get 90-100).
            
            Content:
            {content_pool}
            
            Output valid JSON ONLY:
            {{
                "category": "k-pop" | "k-movie" | "k-drama" | "k-entertain" | "discard",
                "title": "[{name}] ...",
                "summary": "...",
                "score": 85
            }}
            """
            try:
                ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=write_prompt)
                data = json.loads(ai_res.text.replace("```json", "").replace("```", "").strip())
                
                assigned_cat = data.get("category", "discard").lower()
                
                # 쓰레기 기사 가차 없이 컷! (비용 절약)
                if assigned_cat not in ['k-pop', 'k-movie', 'k-drama', 'k-entertain']:
                    print(f"      ⏭️ [DISCARDED] Garbage/CF filtered. Tokens saved!")
                    continue
                
                score = int(data.get("score", 70))
                score = max(50, min(100, score))

                final_results.append({
                    "category": assigned_cat, # AI가 배정해준 진짜 카테고리
                    "keyword": name,
                    "title": data.get("title", f"[{name}] Untitled"),
                    "summary": data.get("summary", ""),
                    "link": main_link,
                    "image_url": best_img_url,
                    "score": score,
                    "likes": 0
                })
                print(f"      ✅ Saved to [{assigned_cat.upper()}]: {data.get('title')} (Score: {score})")
            except Exception as e:
                print(f"      ❌ Article Gen Error for {name}: {e}")

        # =========================================================
        # Step 6. 💾 듀얼 DB 저장 및 '각 카테고리별 최대 50개' 용량 통제
        # =========================================================
        if final_results:
            print(f"  💾 Step 6: Saving {len(final_results)} articles to databases...")
            try:
                self.db.client.table("search_archive").insert(final_results).execute()
                self.db.client.table("live_news").insert(final_results).execute()
                print("    ✅ Insertion complete.")

                # 💡 데이터가 추가된 모든 카테고리를 추적하여 각각 50개 통제 가동
                affected_categories = set([item['category'] for item in final_results])
                
                for cat in affected_categories:
                    count_res = self.db.client.table("live_news").select("id", count="exact").eq("category", cat).execute()
                    total_count = count_res.count

                    if total_count and total_count > 50:
                        excess = total_count - 50
                        print(f"    ⚠️ [{cat.upper()}] Capacity limit exceeded ({total_count}/50). Purging {excess} lowest scored items...")
                        
                        low_res = self.db.client.table("live_news").select("id").eq("category", cat).order("score", asc=True).limit(excess).execute()
                        if low_res.data:
                            drop_ids = [item['id'] for item in low_res.data]
                            self.db.client.table("live_news").delete().in_("id", drop_ids).execute()
                            print(f"    🗑️ [{cat.upper()}] Purged {len(drop_ids)} low-score items.")

            except Exception as e:
                print(f"    ❌ DB Save/Purge Error: {e}")

        print(f"🎉 [AI Newsroom] Pipeline (Base: {target_category}) successfully completed!")
