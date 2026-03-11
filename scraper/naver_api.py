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
        print(f"\n🚀 [AI Newsroom] Starting Ultimate 8-Step Pipeline (Base: {target_category})")
        
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst)
        time_limit = now_kst - timedelta(hours=24)
        print(f"  🕒 Current KST Time: {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.naver_id or not self.naver_secret:
            print("  ❌ Error: NAVER API keys missing.")
            return

        # =========================================================
        # Step 1. 🧹 DB 청소 및 '4시간 쿨타임' 명단 확보
        # =========================================================
        print("  🧹 Step 1: Cleaning DB and Fetching 4-Hour Cooldown List...")
        cooldown_list = []
        try:
            # 1) 24시간/7일 지난 옛날 기사 삭제
            one_day_ago = (now_kst - timedelta(days=1)).isoformat()
            seven_days_ago = (now_kst - timedelta(days=7)).isoformat()
            self.db.client.table("live_news").delete().lt("created_at", one_day_ago).execute()
            self.db.client.table("search_archive").delete().lt("created_at", seven_days_ago).execute()

            # 2) 💡 최근 4시간 이내에 작성된 연예인 명단 (도배 방지 블랙리스트)
            four_hours_ago = (now_kst - timedelta(hours=4)).isoformat()
            cooldown_res = self.db.client.table("live_news").select("keyword").gte("created_at", four_hours_ago).execute()
            if cooldown_res.data:
                cooldown_list = list(set([item['keyword'] for item in cooldown_res.data if item.get('keyword')]))
            print(f"    🛡️ 4-Hour Cooldown active for {len(cooldown_list)} celebrities.")
        except Exception as e:
            print(f"    ⚠️ DB Cleanup/Cooldown Error: {e}")

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
        
        prompt_frequency = f"""
        Analyze the following Korean news article titles.
        Extract all REAL Korean celebrity names (actors, singers, idols) mentioned in these titles and count exactly how many titles each name appears in.
        - IMPORTANT: Extract the group name and individual name in the title separately.
        
        Return a valid JSON array of the top 20 most frequently mentioned names, sorted by count (highest first).
        Format: [{{"name": "Celebrity Name", "count": 10}}, ...]
        
        Titles to analyze:
        {json.dumps(title_list, ensure_ascii=False)}
        """
        
        try:
            ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt_frequency)
            top_20_data = json.loads(ai_res.text.replace("```json", "").replace("```", "").strip())
        except Exception as e:
            print(f"    ❌ Frequency Analysis Error: {e}")
            return

        # =========================================================
        # Step 5. 🛡️ 쿨타임 필터링 및 최종 Top 10 확정
        # =========================================================
        print(f"  🛡️ Step 5: Applying Cooldown Filter & Selecting Top 10...")
        final_targets = []
        
        for item in top_20_data:
            name = item.get("name")
            count = item.get("count")
            if not name: continue
            
            if name in cooldown_list:
                print(f"    ⏭️ Skipping '{name}' (On 4-hour cooldown)")
                continue
                
            final_targets.append(name)
            if len(final_targets) == 10: 
                break

        print(f"    🎯 Final Top 10 Targets: {final_targets}")

        # =========================================================
        # Step 6. 🔍 핀셋 심층 검색 (Deep Search - 링크, 이미지, 본문 확보)
        # =========================================================
        print(f"  🔍 Step 6: Deep Searching for {len(final_targets)} Final Targets...")
        final_results = []

        for name in final_targets:
            print(f"\n    🔎 Deep Dive: {name}")
            p_url = f"https://openapi.naver.com/v1/search/news.json?query={quote(name)}&display=5&sort=sim"
            try:
                p_res = requests.get(p_url, headers=self.naver_headers, timeout=10)
                raw_articles = p_res.json().get('items', [])
            except:
                continue

            valid_articles = [art for art in raw_articles if parsedate_to_datetime(art['pubDate']).astimezone(kst) >= time_limit][:3]

            if not valid_articles:
                print(f"      ⏭️ No deep articles found. Skipping.")
                continue

            content_pool = ""
            best_img_url = ""
            
            main_link = valid_articles[0]['link'] 

            headers = {"User-Agent": "Mozilla/5.0"}
            for art in valid_articles:
                try:
                    c_res = requests.get(art['link'], headers=headers, timeout=5, verify=False)
                    soup = BeautifulSoup(c_res.text, 'html.parser')
                    body = soup.select_one("#dic_area, #artc_body, #articleBody, .article_body, .news_end, .end_body_wrp")
                    if body: 
                        content_pool += body.get_text(separator=' ', strip=True)[:1000] + " \n"
                    else:
                        paragraphs = soup.find_all('p')
                        backup_text = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
                        if backup_text: content_pool += backup_text[:1000] + " \n"
                    
                    if not best_img_url: 
                        meta_img = soup.find("meta", property="og:image")
                        if meta_img and meta_img.get("content"):
                            candidate_img = meta_img["content"].strip()
                            blacklist_img = ["dummy", "naver_logo", "default", "no_image"]
                            if not any(bad in candidate_img.lower() for bad in blacklist_img) and requests.head(candidate_img, timeout=1, verify=False).status_code == 200:
                                best_img_url = candidate_img
                except:
                    continue

            if len(content_pool) < 100 or not best_img_url:
                print(f"      ⏭️ Insufficient content or no image. Skipping.")
                continue

            # =========================================================
            # Step 7. 🤖 AI 철통 검증 및 정밀 영문 요약 (엄격한 팩트 제어)
            # =========================================================
            write_prompt = f"""
            You are a rigorous and objective K-entertainment news reporter analyzing news about '{name}'.

            Do not include any AI-generated translations in your article.

            (Valid news articles only) Article Writing Rules:
            1. Title Format: Must use the following format: `[{{Korean_Name}}] English Title`
                - Example: `[지민] Dominates Global Charts with New Song`

            2. Summary: Summarize only the facts in the text (3-10 lines).
                - Expert interpretations, opinions, and nonsense (meaningless or irrelevant content) are strictly prohibited.

            3. Data Preservation: Retain all numbers (dates, amounts, rankings) and proper nouns exactly as they appear in the original text.
            
            4. CATEGORY: '{target_category}'
               - It doesn't matter which category the person is in, but rather classify the article by checking which category it is in..
            
            Content to summarize:
            {content_pool}
            
            Output valid JSON ONLY:
            {{
                "main_subject": "True Korean Name",
                "category": "{target_category}" | "k-movie" | "k-drama" | "discard",
                "title": "[{{main_subject}}] ...",
                "summary": "...",
                "score": 85
            }}
            """
            try:
                ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=write_prompt)
                data = json.loads(ai_res.text.replace("```json", "").replace("```", "").strip())
                
                assigned_cat = data.get("category", target_category).lower()
                actual_subject = data.get("main_subject", "").strip()
                title = data.get("title", "").strip()
                summary = data.get("summary", "").strip()

                # 💡 [철통 방어 로직] 쓰레기 판정, 키워드 누락, 제목/내용 누락 시 DB 진입 차단!
                if assigned_cat == "discard" or not actual_subject or not title or not summary:
                    print(f"      ⏭️ [DISCARDED] System text or missing data. Dropping fake article.")
                    continue
                
                score = max(50, min(100, int(data.get("score", 70))))

                final_results.append({
                    "category": assigned_cat,
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
        # Step 8. 💾 DB 저장 및 UI 최적화 ([이름] 기준 덮어쓰기)
        # =========================================================
        if final_results:
            print(f"  💾 Step 8: Saving to DB and Deduplicating based on [Name]...")
            try:
                incoming_subjects = list(set([item['keyword'] for item in final_results]))
                
                if incoming_subjects:
                    print(f"    🗑️ Deleting existing articles for names: {incoming_subjects}")
                    self.db.client.table("live_news").delete().in_("keyword", incoming_subjects).execute()

                self.db.client.table("search_archive").insert(final_results).execute()
                self.db.client.table("live_news").insert(final_results).execute()
                print("    ✅ Insertion complete.")

                count_res = self.db.client.table("live_news").select("id", count="exact").eq("category", target_category).execute()
                total_count = count_res.count

                if total_count and total_count > 50:
                    excess = total_count - 50
                    print(f"    ⚠️ Capacity exceeded. Purging {excess} oldest items...")
                    low_res = self.db.client.table("live_news").select("id").eq("category", target_category).order("created_at", asc=True).limit(excess).execute()
                    if low_res.data:
                        drop_ids = [item['id'] for item in low_res.data]
                        self.db.client.table("live_news").delete().in_("id", drop_ids).execute()

            except Exception as e:
                print(f"    ❌ DB Save Error: {e}")

        print(f"🎉 [AI Newsroom] Ultimate Pipeline (Base: {target_category}) successfully completed!")
