import os
import json
import requests
import html
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import urllib3
from urllib.parse import quote
from google import genai
from email.utils import parsedate_to_datetime

# ✅ ModelManager 임포트 추가 (경로는 프로젝트 구조에 맞게 유지)
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
            # ✅ ModelManager 초기화 추가
            self.model_manager = ModelManager(client=self.ai_client, provider="gemini")

        self.naver_headers = {
            "X-Naver-Client-Id": self.naver_id,
            "X-Naver-Client-Secret": self.naver_secret
        }

    def run_pipeline(self, target_category):
        print(f"\n🚀 [AI Newsroom] Starting Ultimate 8-Step Pipeline (Base: {target_category})")
        
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        time_limit = now_kst - timedelta(hours=24)
        print(f"  🕒 Current KST Time: {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.naver_id or not self.naver_secret:
            print("  ❌ Error: NAVER API keys missing.")
            return

        # ✅ 파이프라인 시작 시 최적의 모델을 한 번 가져와서 저장
        self.best_model = self.model_manager.get_best_model() if hasattr(self, 'model_manager') else 'gemini-2.5-flash'
        print(f"  🤖 Loaded Dynamic AI Model: {self.best_model}")

        # =========================================================
        # Step 1. 🕒 현재 시간 출력 및 🧹 DB 청소 (search_archive 7일 경과 데이터 삭제)
        # =========================================================
        print(f"  🕒 한국 현재 시간: {now_kst.strftime('%Y년 %m월 %d일 %H시 %M분 %S초')}")
        print("  🧹 Step 1: Cleaning up old archive data (7 days)...")
        
        try:
            # search_archive 테이블에서 7일 지난 기사만 삭제
            seven_days_ago = (now_kst - timedelta(days=7)).isoformat()
            self.db.client.table("search_archive").delete().lt("created_at", seven_days_ago).execute()
            print("    ✅ 7일 지난 아카이브 데이터 정리 완료.")
        except Exception as e:
            print(f"    ⚠️ DB Cleanup Error: {e}")

        # =========================================================
        # Step 2. 📡 다중 키워드 광역 스캔 (제목만 싹쓸이 & 중복 제거)
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
        # Step 3 & 4. 📊 기사 제목 빈도수 추출 및 트렌드 Top 20 선정
        # =========================================================
        print(f"  📊 Step 3 & 4: Analyzing Title Frequencies for Top 20 Trend...")
        
        # Updated prompt to handle alias merging and scoring
        prompt_frequency = f"""
        Analyze the following Korean news article titles.
        Extract all REAL Korean celebrity names (actors, singers, idols) mentioned in these titles and calculate a total exposure 'score' for each.
        
        CRITICAL RULES:
        1. Base Score: 1 mention in a title = 1 score. 
        2. Merge Aliases: If a celebrity or group is mentioned by different names (e.g., "BTS" and "방탄소년단", "RM" and "알엠", "NewJeans" and "뉴진스"), merge their scores under the most common/official KOREAN name (e.g., "방탄소년단", "뉴진스").
        3. Group vs Individual: Extract group names and individual member names separately, unless the title refers to them collectively as one entity.
        
        Return a valid JSON array of the top 20 most frequently mentioned names (or merged names), sorted by score (highest first).
        Format: [{{"name": "Official Korean Name", "score": 19}}, ...]
        
        Titles to analyze:
        {json.dumps(title_list, ensure_ascii=False)}
        """
        
        try:
            ai_res = self.ai_client.models.generate_content(
                model=self.best_model, 
                contents=prompt_frequency,
                config={"response_mime_type": "application/json"} 
            )
            # Since we forced application/json, we can safely load it directly
            top_20_data = json.loads(ai_res.text)
            
            # Print the results to verify
            for item in top_20_data:
                print(f"  - {item['name']}: {item['score']}점")
                
        except Exception as e:
            print(f"    ❌ Frequency Analysis Error: {e}")
            return

        # =========================================================
        # Step 5 & 6. 🔍 핀셋 심층 검색 및 유효성 필터링 (기사, 이미지, 글자수)
        # =========================================================
        print(f"  🔍 Step 5 & 6: Deep Searching & Filtering Top 20 Targets...")
        final_results = []

        # 1. 각 카테고리별 1위부터 20위까지 반복 탐색
        for item in top_20_data:
            name = item.get("name")
            score = item.get("score") # Step 3&4에서 부여된 최종 점수
            if not name: continue

            print(f"\n    🔎 Deep Dive: {name} (Score: {score})")
            
            # 네이버 뉴스 API 검색 (넉넉하게 10개를 불러와서 시간 필터링)
            p_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(name)}&display=10&sort=sim"
            try:
                p_res = requests.get(p_url, headers=self.naver_headers, timeout=10)
                raw_articles = p_res.json().get('items', [])
            except Exception as e:
                print(f"      ⏭️ API Error. Skipping. ({e})")
                continue

            # 2. 24시간 이내의 최신 기사만 필터링 후 최대 3개 추출
            valid_articles = [art for art in raw_articles if parsedate_to_datetime(art['pubDate']).astimezone(kst) >= time_limit][:3]

            if not valid_articles:
                print(f"      ⏭️ No recent valid articles (within 24h) found. Skipping.")
                continue

            content_pool = ""
            best_img_url = ""
            main_link = valid_articles[0]['link'] 

            headers = {"User-Agent": "Mozilla/5.0"}
            
            # 3. 확보된 기사(1~3개)를 모두 돌며 본문을 최대한 누적 수집
            for art in valid_articles:
                try:
                    c_res = requests.get(art['link'], headers=headers, timeout=5, verify=False)
                    soup = BeautifulSoup(c_res.text, 'html.parser')
                    
                    # 💡 [정제 1] 불필요한 노이즈 태그들(광고, 스크립트, 메뉴, 푸터 등) 먼저 싹둑 자르기
                    for unwanted in soup.select('script, style, iframe, header, footer, nav, aside, .aside, .ad, .share_btn, .reporter_area, .copyright, #footer'):
                        unwanted.decompose()
                    
                    # 💡 [정제 2] 본문 영역을 나타내는 CSS 선택자를 대폭 강화
                    body = soup.select_one("""
                        #dic_area, #artc_body, #articleBody, .article_body, .news_end, .end_body_wrp,
                        .article_view, .news_view, .content_area, #newsEndContents, .news_contents,
                        [itemprop="articleBody"]
                    """)
                    
                    if body: 
                        content_pool += body.get_text(separator=' ', strip=True)[:1000] + " \n"
                    else:
                        # 💡 [정제 3] 플랜 B: p태그 추출 시 짧은 시스템 텍스트 버리고, 50자 이상의 '긴 문단'만 취합
                        paragraphs = soup.find_all('p')
                        backup_text = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
                        if backup_text: content_pool += backup_text[:1000] + " \n"
                    
                    # 이미지 추출 (아직 유효한 이미지를 못 찾았을 경우에만 탐색)
                    if not best_img_url: 
                        meta_img = soup.find("meta", property="og:image")
                        if meta_img and meta_img.get("content"):
                            candidate_img = meta_img["content"].strip()
                            blacklist_img = ["dummy", "naver_logo", "default", "no_image"]
                            
                            if not any(bad in candidate_img.lower() for bad in blacklist_img):
                                try:
                                    img_check = requests.head(candidate_img, timeout=2, verify=False)
                                    if img_check.status_code == 200:
                                        best_img_url = candidate_img
                                except:
                                    pass
                except Exception as e:
                    continue

            # 4. 최종 유효성 검증
            if len(content_pool) < 100:
                print(f"      ⏭️ Insufficient content length ({len(content_pool)} chars). Skipping.")
                continue
                
            if not best_img_url:
                print(f"      ⏭️ No valid image found. Skipping.")
                continue

            # 모든 조건을 통과한 키워드만 리스트에 추가 (원래 스코어 유지)
            print(f"      ✅ Validated! ({len(valid_articles)} articles used, Content: {len(content_pool)} chars, Image: OK)")
            final_results.append({
                "name": name,
                "score": score,
                "content": content_pool,
                "image": best_img_url,
                "link": main_link
            })

        # =========================================================
        # Step 7. 📊 살아남은 키워드 최종 정렬
        # =========================================================
        # 5. 수집된 기사와 이미지가 있는 키워드만 스코어 기준으로 다시 내림차순 정렬
        final_results = sorted(final_results, key=lambda x: x["score"], reverse=True)

        print(f"\n  🎯 Final Extracted Valid Targets: {len(final_results)} items")
        for res in final_results:
            print(f"    - {res['name']} (Score: {res['score']})")

        # =========================================================
        # Step 8. 🤖 AI 철통 검증 및 정밀 영문 요약 (엄격한 팩트 제어)
        # =========================================================
        print(f"\n  🤖 Step 8: AI Summary & Verification for {len(final_results)} targets...")
        ai_summarized_results = []

        # Step 5 & 6에서 통과된 final_results를 순회
        for item in final_results:
            name = item["name"]
            score = item["score"] # 🎯 이전 단계에서 정해진 스코어 유지!
            content_pool = item["content"]
            best_img_url = item["image"]
            main_link = item["link"]

            print(f"    📝 Generating AI summary for: {name}...")

            # AI 프롬프트 (점수 평가 제거, 카테고리/제목/요약만 요구)
            write_prompt = f"""
            You are a rigorous and objective K-entertainment news reporter analyzing news about '{name}'.

            Do not include any AI-generated translations in your article. Write a fresh English summary based on the facts.

            (Valid news articles only) Article Writing Rules:
            1. Title Format: Must use the following format: `[{name}] English Title`
            2. Summary: Summarize only the facts in the text (3-10 lines).
                - Expert interpretations, opinions, and nonsense (meaningless or irrelevant content) are strictly prohibited.
            3. Data Preservation: Retain all numbers (dates, amounts, rankings) and proper nouns exactly as they appear in the original text.
            4. CATEGORY: '{target_category}'
               - Classify the article based on its content. If it's pure garbage/system text, classify as 'discard'.
            5. Strict Subject Validation: Evaluate if '{name}' is the actual main subject of the text. If '{name}' is merely mentioned in passing, or if the article is primarily about someone else, you MUST classify the category as 'discard'. Do not force a summary about '{name}' if they are not the central focus.

            Content to summarize:
            {content_pool}

            Output valid JSON ONLY:
            {{
                "main_subject": "{name}",
                "category": "determined category or 'discard'",
                "title": "[{name}] ...",
                "summary": "..."
            }}
            """
            
            try:
                # JSON 응답 강제 (파싱 에러 방지)
                ai_res = self.ai_client.models.generate_content(
                    model=self.best_model, 
                    contents=write_prompt,
                    config={"response_mime_type": "application/json"} 
                )
                data = json.loads(ai_res.text)
                
                assigned_cat = data.get("category", target_category).lower()
                actual_subject = data.get("main_subject", name).strip()
                title = data.get("title", "").strip()
                summary = data.get("summary", "").strip()

                # 💡 [철통 방어 로직] 쓰레기 판정, 제목/내용 누락 시 DB 진입 차단!
                if assigned_cat == "discard" or not title or not summary:
                    print(f"      ⏭️ [DISCARDED] System text or missing data. Dropping fake article.")
                    continue
                
                # ✅ 수정 적용 1: AI가 착각했더라도 타겟 카테고리로 강제 고정
                safe_category = target_category

                # 최종 결과 리스트에 추가 (기존 스코어 적용)
                ai_summarized_results.append({
                    "category": safe_category,
                    "keyword": actual_subject,
                    "title": title,
                    "summary": summary,
                    "link": main_link,
                    "image_url": best_img_url,
                    "score": score, # 수정 불가능한 고정 스코어
                    "likes": 0
                })
                print(f"      ✅ AI Generated: {title} (Score: {score})")
                
            except Exception as e:
                print(f"      ❌ AI Generation Error for {name}: {e}")

        # =========================================================
        # Step 9. 💾 DB 저장 및 UI 최적화 ([카테고리+이름] 기준 덮어쓰기)
        # =========================================================
        # ✅ 수정 적용 2: Step 8의 for문 바깥(동일 들여쓰기 라인)에 배치
        if ai_summarized_results: # 앞선 AI 요약 단계의 결과물 리스트
            print(f"  💾 Step 9: Saving to DB and Deduplicating based on [Name]...")
            try:
                # 1. 새로 들어갈 기사들의 키워드(이름) 목록 추출
                incoming_subjects = list(set([item['keyword'] for item in ai_summarized_results]))
                
                if incoming_subjects:
                    print(f"    🗑️ Deleting existing articles in '{target_category}' for names: {incoming_subjects}")
                    # 💡 [핵심 수정] 타 카테고리 침범 방지! 현재 'target_category' 안에서만 중복 키워드 삭제
                    self.db.client.table("live_news").delete().eq("category", target_category).in_("keyword", incoming_subjects).execute()

                # 2. Archive(기록용 DB)와 Live News(실제 서비스용 DB)에 모두 새 기사 추가
                self.db.client.table("search_archive").insert(ai_summarized_results).execute()
                self.db.client.table("live_news").insert(ai_summarized_results).execute()
                print("    ✅ Insertion complete.")

                # 3. 50개 유지 규칙 적용 (오래된 순으로 삭제)
                count_res = self.db.client.table("live_news").select("id", count="exact").eq("category", target_category).execute()
                total_count = count_res.count

                if total_count and total_count > 50:
                    excess = total_count - 50
                    print(f"    ⚠️ Capacity exceeded ({total_count}/50). Purging {excess} oldest items...")
                    
                    # 가장 오래된(created_at 오름차순) 기사를 초과분만큼 조회
                    low_res = self.db.client.table("live_news").select("id").eq("category", target_category).order("created_at", desc=False).limit(excess).execute()
                    
                    if low_res.data:
                        drop_ids = [item['id'] for item in low_res.data]
                        # 조회된 오래된 기사들 삭제
                        self.db.client.table("live_news").delete().in_("id", drop_ids).execute()
                        print(f"    🧹 Purged {len(drop_ids)} old articles successfully.")

            except Exception as e:
                print(f"    ❌ DB Save Error: {e}")

        print(f"🎉 [AI Newsroom] Ultimate Pipeline (Base: {target_category}) successfully completed!")
