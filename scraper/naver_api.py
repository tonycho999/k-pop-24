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
        print(f"\n🚀 [AI Newsroom] Starting Ultimate 8-Step Pipeline (Base: {target_category})")
        
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
        # Step 3 & 4. 📊 기사 제목 빈도수 추출 및 트렌드 Top 20 선정
        # =========================================================
        print(f"  📊 Step 3 & 4: Analyzing Title Frequencies for Top 20 Trend...")
        prompt_frequency = f"""
        Analyze the following Korean news article titles.
        Extract all REAL Korean celebrity names (actors, singers, idols) mentioned in these titles and calculate a total exposure 'score' for each.
        
        CRITICAL RULES:
        1. Base Score: 1 mention in a title = 1 score. 
        2. Merge Aliases: If a celebrity or group is mentioned by different names (e.g., "BTS" and "방탄소년단"), merge their scores under the most common/official KOREAN name.
        3. Group vs Individual: Extract group names and individual member names separately, unless the title refers to them collectively as one entity.
        
        Return a valid JSON array of the top 20 most frequently mentioned names, sorted by score (highest first).
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
            top_20_data = json.loads(ai_res.text)
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

        for item in top_20_data:
            name = item.get("name")
            score = item.get("score")
            if not name: continue

            print(f"\n    🔎 Deep Dive: {name} (Score: {score})")
            
            p_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(name)}&display=10&sort=sim"
            try:
                p_res = requests.get(p_url, headers=self.naver_headers, timeout=10)
                raw_articles = p_res.json().get('items', [])
            except Exception as e:
                print(f"      ⏭️ API Error. Skipping. ({e})")
                continue

            valid_articles = [art for art in raw_articles if parsedate_to_datetime(art['pubDate']).astimezone(kst) >= time_limit][:3]

            if not valid_articles:
                print(f"      ⏭️ No recent valid articles (within 24h) found. Skipping.")
                continue

            content_pool = ""
            naver_snippets_pool = "" # 💡 [대안 2 적용] 실패를 대비한 네이버 요약본 백업
            best_img_url = ""
            main_link = valid_articles[0]['link'] 

            headers = {"User-Agent": "Mozilla/5.0"}
            
            for art in valid_articles:
                # 💡 [플랜 C 준비] 네이버 API가 준 기본 제목과 요약본 미리 저장
                clean_art_title = re.sub(r'<[^>]+>', '', html.unescape(art['title']))
                clean_art_desc = re.sub(r'<[^>]+>', '', html.unescape(art['description']))
                naver_snippets_pool += f"[News Title]: {clean_art_title}\n[News Summary]: {clean_art_desc}\n\n"

                try:
                    c_res = requests.get(art['link'], headers=headers, timeout=5, verify=False)
                    soup = BeautifulSoup(c_res.text, 'html.parser')
                    
                    for unwanted in soup.select('script, style, iframe, header, footer, nav, aside, .aside, .ad, .share_btn, .reporter_area, .copyright, #footer'):
                        unwanted.decompose()
                    
                    body = soup.select_one("""
                        #dic_area, #artc_body, #articleBody, .article_body, .news_end, .end_body_wrp,
                        .article_view, .news_view, .content_area, #newsEndContents, .news_contents,
                        [itemprop="articleBody"]
                    """)
                    
                    if body: 
                        content_pool += body.get_text(separator=' ', strip=True)[:1000] + " \n"
                    else:
                        paragraphs = soup.find_all('p')
                        backup_text = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
                        if backup_text: content_pool += backup_text[:1000] + " \n"
                    
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

            # 💡 [플랜 C 발동] 크롤링한 본문이 쓰레기거나 너무 짧으면 네이버 요약본으로 전격 교체!
            if len(content_pool) < 100:
                print(f"      ⚠️ Crawled content too short/empty. Falling back to Naver snippets!")
                content_pool = naver_snippets_pool
                
            if not best_img_url:
                print(f"      ⏭️ No valid image found. Skipping.")
                continue

            print(f"      ✅ Validated! (Content: {len(content_pool)} chars, Image: OK)")
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
        final_results = sorted(final_results, key=lambda x: x["score"], reverse=True)

        print(f"\n  🎯 Final Extracted Valid Targets: {len(final_results)} items")
        for res in final_results:
            print(f"    - {res['name']} (Score: {res['score']})")

        # =========================================================
        # Step 8. 🤖 AI 철통 검증 및 정밀 영문 요약
        # =========================================================
        print(f"\n  🤖 Step 8: AI Summary & Verification for {len(final_results)} targets...")
        ai_summarized_results = []

        for item in final_results:
            name = item["name"]
            score = item["score"] 
            content_pool = item["content"]
            best_img_url = item["image"]
            main_link = item["link"]

            print(f"    📝 Generating AI summary for: {name}...")

            # 💡 [프롬프트 최적화] AI에게 이 텍스트가 뉴스 본문일 수도 있고, 요약본 뭉치일 수도 있다고 알려줌
            write_prompt = f"""
            You are a rigorous and objective K-entertainment news reporter analyzing news about '{name}'.

            Do not include any AI-generated translations in your article. Write a fresh English summary based on the facts.

            (Valid news articles only) Article Writing Rules:
            1. Title Format: Must use the following format: `[{name}] English Title`
            2. Summary: Summarize only the facts in the text (3-10 lines).
                - Expert interpretations, opinions, and nonsense are strictly prohibited.
            3. Data Preservation: Retain all numbers (dates, amounts, rankings) and proper nouns exactly as they appear in the original text.
            4. CATEGORY: '{target_category}'
               - Classify the article based on its content. If it's pure garbage/system text, classify as 'discard'.
            5. Strict Subject Validation: Evaluate if '{name}' is the actual main subject of the text. If '{name}' is merely mentioned in passing, or if the article is primarily about someone else, you MUST classify the category as 'discard'. Do not force a summary about '{name}' if they are not the central focus.

            Content to summarize (may be full article text OR multiple short news snippets):
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

                if assigned_cat == "discard" or not title or not summary:
                    print(f"      ⏭️ [DISCARDED] System text, missing data, or wrong subject. Dropping article.")
                    continue
                
                safe_category = target_category

                ai_summarized_results.append({
                    "category": safe_category,
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
