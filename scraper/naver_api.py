import os
import json
import requests
import html
import re
from datetime import datetime, timedelta
import pytz
import urllib3
from urllib.parse import quote
from google import genai
from email.utils import parsedate_to_datetime

# ✅ ModelManager 임포트
from model_manager import ModelManager

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
            self.model_manager = ModelManager(client=self.ai_client, provider="gemini")

        self.naver_headers = {
            "X-Naver-Client-Id": self.naver_id,
            "X-Naver-Client-Secret": self.naver_secret
        }

    def run_pipeline(self, target_category):
        print(f"\n🚀 [AI Newsroom] Starting Ultra-Fast Snippet Pipeline (Base: {target_category})")
        
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        time_limit = now_kst - timedelta(hours=24)
        print(f"  🕒 Current KST Time: {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.naver_id or not self.naver_secret:
            print("  ❌ Error: NAVER API keys missing.")
            return

        self.best_model = self.model_manager.get_best_model() if hasattr(self, 'model_manager') else 'gemini-2.5-flash'
        print(f"  🤖 Loaded Dynamic AI Model: {self.best_model}")

        # =========================================================
        # Step 1. 🕒 현재 시간 출력 및 🧹 DB 청소
        # =========================================================
        print("  🧹 Step 1: Cleaning up old archive data (7 days)...")
        try:
            seven_days_ago = (now_kst - timedelta(days=7)).isoformat()
            self.db.client.table("search_archive").delete().lt("created_at", seven_days_ago).execute()
            print("    ✅ 7일 지난 아카이브 데이터 정리 완료.")
        except Exception as e:
            print(f"    ⚠️ DB Cleanup Error: {e}")

        # =========================================================
        # Step 2. 📡 다중 키워드 광역 스캔
        # =========================================================
        print(f"  📡 Step 2: Multi-Query Broad Scan for '{target_category}'...")
        multi_queries_map = {
            'k-pop': ['보이그룹', '걸그룹', '아이돌', '솔로가수', '신인그룹'],
            'k-movie': ['영화', '배우', '영화감독'],
            'k-drama': ['드라마', '안방극장'],
            'k-entertain': ['예능']
        }
        queries_to_run = multi_queries_map.get(target_category, ['연예계'])
        unique_titles = set()

        for q in queries_to_run:
            search_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(q)}&display=100&sort=date"
            try:
                res = requests.get(search_url, headers=self.naver_headers, timeout=5)
                raw_news = res.json().get('items', [])
                for n in raw_news:
                    pub_date = parsedate_to_datetime(n['pubDate']).astimezone(kst)
                    if pub_date >= time_limit:
                        clean_title = re.sub(r'<[^>]+>', '', html.unescape(n['title']))
                        unique_titles.add(clean_title)
            except:
                continue
        
        title_list = list(unique_titles)
        if not title_list:
            print("    ⏭️ No titles collected. Skipping.")
            return
        print(f"    ✅ Collected {len(title_list)} unique article titles in the last 24h.")

        # =========================================================
        # Step 3 & 4. 📊 기사 제목 빈도수 추출 및 타겟 선정 (인물, 작품, 방송 포함)
        # =========================================================
        print(f"  📊 Step 3 & 4: Extracting Major Subjects (People, Movies, Dramas, Shows)...")
        # 💡 [수정] 인물 외에도 영화/드라마/프로그램/노래 제목도 타겟으로 잡도록 프롬프트 강화
        prompt_frequency = f"""
        Analyze the following Korean news article titles.
        Extract the most prominent MAIN SUBJECTS mentioned in these titles. 
        A "Main Subject" can be:
        1. A celebrity name (Actor, Singer, Idol, Director).
        2. A content title (Movie, K-Drama, TV Variety Show, Song title).

        CRITICAL RULES:
        1. Base Score: 1 mention in a title = 1 score. 
        2. Merge Aliases: If a subject is mentioned by different names (e.g., "BTS" and "방탄소년단"), merge their scores under the most common KOREAN official name.
        3. Do NOT extract generic words like "컴백", "방송", "결혼". Extract ONLY proper nouns (Specific people or specific titles).
        
        Return a valid JSON array of the top 20 most frequently mentioned subjects, sorted by score (highest first).
        Format: [{{"name": "Official Korean Subject Name", "score": 19}}, ...]
        
        Titles to analyze:
        {json.dumps(title_list, ensure_ascii=False)}
        """
        
        try:
            ai_res = self.ai_client.models.generate_content(
                model=self.best_model, 
                contents=prompt_frequency,
                config={"response_mime_type": "application/json"} 
            )
            top_20_data = json.loads(ai_res.text)
            for item in top_20_data:
                item['score'] = int(item.get('score', 0)) + 10
                print(f"  - {item['name']}: {item['score']}점")
        except Exception as e:
            print(f"    ❌ Frequency Analysis Error: {e}")
            return

        # =========================================================
        # Step 5 & 6. 🔍 고속 요약본 풀링 & 100% 팩트 필터링 & 🚫 이미지 중복 방지
        # =========================================================
        print(f"  🔍 Step 5 & 6: High-Speed Snippet Pooling & Strict Image Deduplication...")
        final_results = []
        used_image_urls = set() # 💡 [추가] 이번 런(run)에서 사용된 이미지를 모두 기록하는 저장소

        for item in top_20_data:
            name = item.get("name")
            score = item.get("score")
            if not name: continue

            print(f"\n    🔎 Deep Dive: {name} (Score: {score})")
            
            # 요약본을 넉넉하게 50개 호출
            p_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(name)}&display=50&sort=sim"
            try:
                p_res = requests.get(p_url, headers=self.naver_headers, timeout=10)
                raw_articles = p_res.json().get('items', [])
            except Exception as e:
                print(f"      ⏭️ API Error. Skipping. ({e})")
                continue

            valid_articles = [art for art in raw_articles if parsedate_to_datetime(art['pubDate']).astimezone(kst) >= time_limit]

            if not valid_articles:
                print(f"      ⏭️ No recent valid articles (within 24h) found. Skipping.")
                continue

            # 💡 [핵심 수정] 파이썬 단계에서 '주제(name)'가 없는 요약본은 쓰레기통으로 직행
            snippets_pool = []
            main_link = ""

            for art in valid_articles:
                clean_title = re.sub(r'<[^>]+>', '', html.unescape(art['title']))
                clean_desc = re.sub(r'<[^>]+>', '', html.unescape(art['description']))
                
                # 타겟 이름/제목이 기사 제목이나 요약본에 진짜로 들어있는지 검사 (필터링)
                if name.lower() in clean_title.lower() or name.lower() in clean_desc.lower():
                    snippets_pool.append(f"[Title]: {clean_title}\n[Summary]: {clean_desc}")
                    if not main_link: 
                        main_link = art['link'] # 가장 관련성 높은 첫 기사 링크 저장

            if len(snippets_pool) < 2:
                print(f"      ⏭️ Not enough relevant snippets specifically about '{name}'. Dropping.")
                continue

            # 관련 있는 요약본만 하나로 뭉침
            final_combined_content = "\n\n".join(snippets_pool[:20]) # 최대 20개의 핵심 팩트만 전달
            
            # 💡 [이미지 추출 및 중복 검사 로직] 크롤링 대신 네이버 이미지 API 사용
            best_img_url = ""
            img_search_url = f"https://openapi.naver.com/v1/search/image?query={quote(name)}&display=10&sort=sim"
            try:
                img_res = requests.get(img_search_url, headers=self.naver_headers, timeout=5)
                if img_res.status_code == 200:
                    img_items = img_res.json().get('items', [])
                    for img_item in img_items:
                        candidate_url = img_item.get('link', '')
                        
                        # 🚫 [핵심] 다른 기사에서 쓴 이미지라면 가차 없이 패스!
                        if candidate_url in used_image_urls:
                            continue
                            
                        # 이미지 링크 유효성 검사
                        try:
                            check = requests.head(candidate_url, timeout=2, verify=False)
                            if check.status_code == 200 and check.headers.get('Content-Type', '').startswith('image/'):
                                best_img_url = candidate_url
                                used_image_urls.add(candidate_url) # 💡 사용된 이미지 목록에 등록!
                                break 
                        except:
                            continue
            except Exception as e:
                pass

            if not best_img_url:
                print(f"      ⏭️ No unique/valid image found. Skipping.")
                continue

            print(f"      ✅ Validated! (Used {len(snippets_pool)} pure snippets, Unique Image: OK)")
            final_results.append({
                "name": name,
                "score": score,
                "content": final_combined_content,
                "image": best_img_url,
                "link": main_link
            })

        # =========================================================
        # Step 7. 📊 살아남은 키워드 최종 정렬
        # =========================================================
        final_results = sorted(final_results, key=lambda x: x["score"], reverse=True)

        print(f"\n  🎯 Final Extracted Valid Targets: {len(final_results)} items")
        for res in final_results:
            print(f"    - {res['name']} (Score: {res['score']})")

        # =========================================================
        # Step 8. 🤖 AI 정밀 영문 요약
        # =========================================================
        print(f"\n  🤖 Step 8: AI Summary & Formatting for {len(final_results)} targets...")
        ai_summarized_results = []

        for item in final_results:
            name = item["name"]
            score = item["score"] 
            content_pool = item["content"]
            best_img_url = item["image"]
            main_link = item["link"]

            print(f"    📝 Generating AI summary for: {name}...")

            # 💡 [프롬프트 완벽 수정] 이 데이터는 이미 파이썬이 검증한 '순도 100%' 팩트이므로 무조건 쓰도록 유도
            write_prompt = f"""
            You are a rigorous and objective K-entertainment news reporter.
            I have gathered multiple verified news snippets specifically about '{name}'.

            Article Writing Rules:
            1. Title Format: MUST use the exact format: `[{name}] Catchy English Title`
            2. Summary: Synthesize the provided news snippets into a single, cohesive English news summary (3-10 lines). Focus strictly on the facts presented about '{name}'.
            3. Data Preservation: Retain all numbers (dates, rankings, amounts) and proper nouns exactly as they appear.
            4. Categorize the article based on content, not on individuals: '{target_category}'

            Verified News Snippets to analyze:
            {content_pool}

            Output valid JSON ONLY:
            {{
                "main_subject": "{name}",
                "category": "{target_category}",
                "title": "[{name}] ...",
                "summary": "..."
            }}
            """
            
            try:
                ai_res = self.ai_client.models.generate_content(
                    model=self.best_model, 
                    contents=write_prompt,
                    config={"response_mime_type": "application/json"} 
                )
                data = json.loads(ai_res.text)
                
                actual_subject = data.get("main_subject", name).strip()
                title = data.get("title", "").strip()
                summary = data.get("summary", "").strip()

                if not title or not summary:
                    print(f"      ⏭️ [DISCARDED] AI failed to generate content.")
                    continue
                
                ai_summarized_results.append({
                    "category": target_category,
                    "keyword": actual_subject,
                    "title": title,
                    "summary": summary,
                    "link": main_link,
                    "image_url": best_img_url,
                    "score": score, 
                    "likes": 0
                })
                print(f"      ✅ AI Generated: {title} (Score: {score})")
                
            except Exception as e:
                print(f"      ❌ AI Generation Error for {name}: {e}")

        # =========================================================
        # Step 9. 💾 DB 저장 및 UI 최적화 ([카테고리+이름] 기준 덮어쓰기)
        # =========================================================
        if ai_summarized_results: 
            print(f"  💾 Step 9: Saving to DB and Deduplicating based on [Name]...")
            try:
                incoming_subjects = list(set([item['keyword'] for item in ai_summarized_results]))
                
                if incoming_subjects:
                    print(f"    🗑️ Deleting existing articles in '{target_category}' for names: {incoming_subjects}")
                    self.db.client.table("live_news").delete().eq("category", target_category).in_("keyword", incoming_subjects).execute()

                self.db.client.table("search_archive").insert(ai_summarized_results).execute()
                self.db.client.table("live_news").insert(ai_summarized_results).execute()
                print("    ✅ Insertion complete.")

                count_res = self.db.client.table("live_news").select("id", count="exact").eq("category", target_category).execute()
                total_count = count_res.count

                if total_count and total_count > 50:
                    excess = total_count - 50
                    print(f"    ⚠️ Capacity exceeded ({total_count}/50). Purging {excess} oldest items...")
                    
                    low_res = self.db.client.table("live_news").select("id").eq("category", target_category).order("created_at", desc=False).limit(excess).execute()
                    
                    if low_res.data:
                        drop_ids = [item['id'] for item in low_res.data]
                        self.db.client.table("live_news").delete().in_("id", drop_ids).execute()
                        print(f"    🧹 Purged {len(drop_ids)} old articles successfully.")

            except Exception as e:
                print(f"    ❌ DB Save Error: {e}")

        print(f"🎉 [AI Newsroom] Ultimate Pipeline (Base: {target_category}) successfully completed!")
