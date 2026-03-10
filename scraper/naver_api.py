import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import urllib3
from urllib.parse import quote
from google import genai

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
        
        # 1. 시간 인지
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        print(f"  🕒 Current KST Time: {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")

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
            
            # live_news: 24시간 지난 데이터 삭제
            self.db.client.table("live_news").delete().lt("created_at", one_day_ago).execute()
            # search_archive: 7일 지난 데이터 삭제
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
        # Step 3. 📡 광역 스캔 및 새로운 10명 발굴 (작품명 금지)
        # =========================================================
        base_queries = {
            'k-pop': '아이돌 OR 걸그룹 OR 보이그룹 OR 가요계 OR K팝',
            'k-movie': '한국영화 OR 영화배우 OR 충무로 OR 극장가',
            'k-drama': '한국드라마 OR 드라마배우 OR 넷플릭스 한국',
            'k-entertain': '예능프로그램 OR 방송인 OR 코미디언'
        }
        query = base_queries.get(category, '연예계')

        print(f"  📡 Step 3: Scanning latest 100 news articles for '{query}'...")
        search_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(query)}&display=100&sort=date"
        try:
            res = requests.get(search_url, headers=self.naver_headers, timeout=10)
            res.raise_for_status()
            raw_news = res.json().get('items', [])
        except Exception as e:
            print(f"    ❌ Naver API Error: {e}")
            return

        snippets = [{"title": n['title'], "desc": n['description']} for n in raw_news]

        print("    🧠 Asking AI to extract 10 NEW celebrities...")
        prompt_extract = f"""
        Analyze these 100 recent Korean entertainment news snippets.
        Extract exactly 10 names of the most trending PEOPLE (celebrities, singers, actors, groups).
        
        CRITICAL RULES:
        1. ONLY extract REAL PEOPLE or IDOL GROUPS. Do NOT extract movie titles, drama titles, TV show names, or character names.
        2. EXCLUDE these names entirely (Blacklist): {blacklist}
        3. Return ONLY a valid JSON array of strings. Format: ["Name1", "Name2", ...]
        
        News snippets: {json.dumps(snippets[:100], ensure_ascii=False)}
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
                    # DB에 없는 이름 -> AI 검증
                    verify_prompt = f"Is '{name}' a real, currently active Korean celebrity, singer, actor, or idol group? Answer ONLY with valid JSON: {{\"is_celeb\": true or false}}"
                    v_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=verify_prompt)
                    v_data = json.loads(v_res.text.replace("```json", "").replace("```", "").strip())
                    
                    if v_data.get("is_celeb"):
                        # 신규 연예인으로 판명 -> pending 상태로 DB 추가
                        self.db.client.table("celebrity_dict").insert({"name": name, "default_category": "pending"}).execute()
                        validated_names.append(name)
                        print(f"    ✨ [NEW] Learned and added new celebrity: {name}")
                    else:
                        print(f"    🗑️ [DROP] Discarded non-celebrity/trash data: {name}")
        except Exception as e:
            print(f"    ⚠️ Cross-check Error: {e}")
            validated_names = candidate_names[:10] # 에러 시 일단 진행

        if not validated_names:
            print("  ❌ No valid celebrities found to process. Exiting current run.")
            return

        # =========================================================
        # Step 4 & 5. 📝 심층 취재, 50~100점 채점, 이미지 생존 검증
        # =========================================================
        print(f"  📝 Step 4: Deep Dive & Article Generation for {len(validated_names)} targets...")
        final_results = []

        for name in validated_names:
            print(f"\n    🔍 Investigating: {name}")
            # 해당 인물로 네이버 뉴스 핀포인트 검색 (최신 3개)
            p_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(name)}&display=3&sort=sim"
            try:
                p_res = requests.get(p_url, headers=self.naver_headers, timeout=10)
                articles = p_res.json().get('items', [])
            except:
                continue

            if not articles:
                continue

            content_pool = ""
            best_img_url = ""
            main_link = articles[0]['link']

            # 본문 텍스트와 이미지 추출 (BeautifulSoup)
            headers = {"User-Agent": "Mozilla/5.0"}
            for art in articles:
                try:
                    c_res = requests.get(art['link'], headers=headers, timeout=5, verify=False)
                    soup = BeautifulSoup(c_res.text, 'html.parser')
                    
                    # 텍스트 추출
                    body = soup.select_one("#dic_area, #articeBody, .article_body")
                    if body: content_pool += body.get_text(separator=' ', strip=True)[:1000] + " \n"
                    
                    # 🛡️ Step 5. 이미지 핑 테스트
                    if not best_img_url:
                        meta_img = soup.find("meta", property="og:image")
                        if meta_img and meta_img.get("content"):
                            candidate_img = meta_img["content"].strip()
                            blacklist_img = ["dummy", "naver_logo", "default", "no_image"]
                            if not any(bad in candidate_img.lower() for bad in blacklist_img):
                                # 핑 테스트 (0.5초)
                                check = requests.head(candidate_img, timeout=1, verify=False)
                                if check.status_code == 200:
                                    best_img_url = candidate_img
                except:
                    continue

            if len(content_pool) < 100:
                print(f"      ⏭️ Not enough content. Skipping {name}.")
                continue

            # AI 편집장 기사 작성 및 채점
            write_prompt = f"""
            You are a strict, factual English K-Entertainment news editor.
            Read the extracted news text about '{name}' and write a summary.
            
            RULES:
            1. Title Format MUST BE: `[Korean Name, Group Name (if any)] English Title`
            2. Fact ONLY: No expert analysis, no opinions. Keep proper nouns and numbers exactly as in the original.
            3. Length: 3 to 6 sentences.
            4. Assign a Score (50 to 100) based on the impact/importance of the news (100 = huge scandal/mega hit, 50 = daily SNS update).
            5. Output valid JSON ONLY.
            
            Content:
            {content_pool}
            
            JSON Format:
            {{
                "title": "[Name, Group] Title...",
                "summary": "Summary...",
                "score": 85
            }}
            """
            try:
                ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=write_prompt)
                data = json.loads(ai_res.text.replace("```json", "").replace("```", "").strip())
                
                score = int(data.get("score", 70))
                # 점수 보정 (50~100)
                score = max(50, min(100, score))

                final_results.append({
                    "category": category,
                    "keyword": name, # 블랙리스트 추출용 기준
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
                # 1. search_archive 저장 (역사 보관용)
                self.db.client.table("search_archive").insert(final_results).execute()
                
                # 2. live_news 저장 (메인용)
                self.db.client.table("live_news").insert(final_results).execute()
                print("    ✅ Insertion complete.")

                # 3. 최대 50개 용량 통제 로직
                count_res = self.db.client.table("live_news").select("id", count="exact").eq("category", category).execute()
                total_count = count_res.count

                if total_count and total_count > 50:
                    excess = total_count - 50
                    print(f"    ⚠️ Capacity limit exceeded ({total_count}/50). Purging {excess} lowest scored items...")
                    
                    # 점수가 가장 낮은 기사들 조회
                    low_res = self.db.client.table("live_news").select("id").eq("category", category).order("score", asc=True).limit(excess).execute()
                    if low_res.data:
                        drop_ids = [item['id'] for item in low_res.data]
                        self.db.client.table("live_news").delete().in_("id", drop_ids).execute()
                        print(f"    🗑️ Purged {len(drop_ids)} low-score items.")

            except Exception as e:
                print(f"    ❌ DB Save/Purge Error: {e}")

        print(f"🎉 [AI Newsroom] Pipeline for '{category}' successfully completed!")
