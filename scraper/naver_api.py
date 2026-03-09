import os
import requests
import json
from collections import Counter
from datetime import datetime, timedelta
import pytz
from bs4 import BeautifulSoup

from google import genai 
from google.genai import types

class NaverNewsAPI:
    def __init__(self, db_client, model_name):
        self.client_id = os.environ.get("NAVER_CLIENT_ID")
        self.client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        self.db = db_client
        self.model_name = model_name
        
        self.ai_client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
            http_options=types.HttpOptions(timeout=30000)
        )

    # 💡 [보완 완료] 장갑차 버전 이미지 추출 함수
    def _extract_image(self, url):
        try:
            # 1. 완벽한 크롬 브라우저 위장 (네이버 봇 차단 회피)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            # allow_redirects=True 로 네이버 단축 URL이 원본으로 이동하는 것까지 추적
            res = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
            soup = BeautifulSoup(res.text, 'html.parser')
            meta_img = soup.find("meta", property="og:image")
            
            if meta_img and meta_img.get("content"):
                img_url = meta_img["content"].strip()
                
                # 2. 네이버 기본 로고, 언론사 디폴트 이미지 철저한 블랙리스트 컷오프
                blacklist = ["dummy", "naver_logo", "navernews", "default", "blank", "no_image", "news_logo"]
                
                # img_url 안에 블랙리스트 단어가 단 하나라도 포함되어 있지 않아야만 합격!
                if not any(bad_word in img_url.lower() for bad_word in blacklist):
                    return img_url
                    
        except Exception:
            pass
        
        return None

    def _search_naver_keyword(self, query, display=10, sort="sim"):
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        params = {"query": query, "display": display, "sort": sort}
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            res.raise_for_status()
            return res.json().get('items', [])
        except Exception as e:
            return []

    # 🛡️ Step 4: 팩트 체크망 (생존 서바이벌, 직업 구분 X)
    def _is_valid_new_celeb(self, name):
        forbidden_words = ["역", "캐릭터", "배역", "분한", "극중", "극 중"]
        if any(word in name for word in forbidden_words) or len(name) < 2:
            print(f"    ❌ 탈락 [{name}]: 금지어 포함 또는 너무 짧음")
            return False

        # 함정 수사: 배역명 걸러내기
        role_check = self._search_naver_keyword(f'"{name} 역" OR "{name} 분한"', display=5)
        if len(role_check) >= 3:
            print(f"    ❌ 탈락 [{name}]: 드라마 배역/캐릭터명 의심")
            return False

        positive_keywords = ["가수", "배우", "아이돌", "그룹", "멤버", "앨범", "방송", "출연", "소속사", "콘서트", "드라마", "영화", "예능", "컴백", "스타", "엔터테인먼트", "데뷔", "솔로"]
        general_check = self._search_naver_keyword(name, display=10, sort="sim")
        
        is_real = False
        for article in general_check:
            text = article['title'] + " " + article['description']
            if any(pk in text for pk in positive_keywords):
                is_real = True
                break
                
        if not is_real:
            print(f"    ❌ 탈락 [{name}]: 연예 활동 증거 없음")
            return False
            
        return True

    # 🧹 Step 8 일부: DB 자가 세척 (24시간 경과 및 최저점 50개 제한)
    def _clean_database_limits(self):
        print("🧹 [DB 최적화] 24시간 초과 기사 및 50개 초과분(최저점) 삭제 시작...")
        try:
            # 1. 24시간 지난 기사 무조건 삭제 (Supabase UTC 시간 호환용 'Z' 추가)
            twenty_four_hours_ago = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
            self.db.client.table("live_news").delete().lt("created_at", twenty_four_hours_ago).execute()
            
            # 2. 각 카테고리별로 50개가 넘으면, 점수가 낮은 순서대로 삭제하여 40개(새로운 10개 자리 확보)로 맞춤
            categories = ["k-pop", "k-actor", "k-entertain", "k-culture"]
            for cat in categories:
                res = self.db.client.table("live_news").select("id, score").eq("category", cat).order("score", desc=False).execute()
                if res.data and len(res.data) > 40: # 10개가 새로 들어올 것이므로 40개만 남김
                    excess_count = len(res.data) - 40
                    ids_to_delete = [item['id'] for item in res.data[:excess_count]]
                    if ids_to_delete:
                        self.db.client.table("live_news").delete().in_("id", ids_to_delete).execute()
        except Exception as e:
            print(f"⚠️ DB 최적화 실패: {e}")

    def run_8_step_pipeline(self):
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🕒 [Step 1] 시스템 KST 시간 설정: {now_kst}")

        # 🚀 파이프라인 시작 전 DB 청소 (50개 초과 방지)
        self._clean_database_limits()

        # 🌟 Step 5-1: 5시간 쿨타임 대상자 확보
        five_hours_ago = (datetime.utcnow() - timedelta(hours=5)).isoformat() + "Z"
        try:
            recent_res = self.db.client.table("live_news").select("keyword").gte("created_at", five_hours_ago).execute()
            cooldown_names = {row['keyword'] for row in recent_res.data if row.get('keyword')}
            print(f"⏳ [쿨타임 시스템] 최근 5시간 내 생성되어 이번 턴에서 배제될 인물 수: {len(cooldown_names)}명")
        except:
            cooldown_names = set()

        categories_config = {
            "k-pop": "아이돌 OR 컴백 OR 보이그룹 OR 걸그룹 OR 솔로가수",
            "k-actor": "드라마 OR 영화 OR 배우",
            "k-entertain": "예능 OR 방송 OR MC OR 유재석"
        }
        
        final_results = {"k-pop": [], "k-actor": [], "k-entertain": [], "k-culture": []}

        # 🔄 카테고리별 독립 루프 (각각 10명 강제 할당)
        for cat_key, cat_query in categories_config.items():
            print(f"\n{'='*50}")
            print(f"🚀 [카테고리: {cat_key}] 10개 강제 할당 파이프라인 구동!")
            print(f"{'='*50}")
            
            bulk_news = self._search_naver_keyword(cat_query, display=100, sort="date")
            if not bulk_news: continue

            # 💡 [핵심 보완] 그룹/솔로 분리 추출 강력 지시
            sample_titles = "\n".join([f"- {a['title']}" for a in bulk_news[:60]])
            extract_prompt = f"""
            Extract only REAL proper names of Korean celebrities, actors, or idol groups from these headlines.
            CRITICAL: Group names (e.g., "엑소") and solo artist names (e.g., "백현") MUST be extracted as COMPLETELY separate, distinct entities.
            Headlines: {sample_titles}
            Return EXACTLY a JSON list of strings. Example: ["유재석", "블랙핑크", "로제"]
            """
            try:
                res = self.ai_client.models.generate_content(model=self.model_name, contents=extract_prompt)
                extracted_names = json.loads(res.text.replace("```json", "").replace("```", "").strip())
            except:
                extracted_names = []

            name_counter = Counter()
            for name in extracted_names:
                count = sum(1 for n in bulk_news if name in n['title'] or name in n['description'])
                if count > 0:
                    name_counter[name] = count

            sorted_candidates = [name for name, count in name_counter.most_common()]
            
            try:
                db_res = self.db.client.table("celebrity_dict").select("name").execute()
                existing_names = {row['name'].split(',')[0].strip() for row in db_res.data}
            except:
                existing_names = set()

            valid_candidates = []
            for name in sorted_candidates:
                if len(valid_candidates) >= 40: 
                    break 
                
                # 🌟 Step 5-2: 쿨타임 배제 발동
                if name in cooldown_names:
                    print(f"  ⏳ [쿨타임 배제] {name}: 최근 5시간 내 등록됨. 다양성을 위해 스킵!")
                    continue
                
                if name in existing_names:
                    valid_candidates.append(name)
                else:
                    if self._is_valid_new_celeb(name):
                        try:
                            self.db.client.table("celebrity_dict").insert({
                                "name": name, "default_category": cat_key, "birth_year": 2000
                            }).execute()
                            existing_names.add(name)
                            valid_candidates.append(name)
                            print(f"    🎉 [승인] 신규 연예인 DB 업데이트: {name}")
                        except:
                            pass

            print(f"🚦 [Step 6 & 7] {cat_key} 10개 강제 할당, 요약 및 트래픽 컨트롤...")
            current_cat_quota = 0
            
            for name in valid_candidates:
                if current_cat_quota >= 10:
                    print(f"🎯 [{cat_key}] 목표 할당량 10개 완벽 달성! 루프 종료.")
                    break 
                
                rank = current_cat_quota + 1
                article_count = 3 if rank <= 5 else 2 
                target_news = self._search_naver_keyword(name, display=article_count, sort="sim")
                if not target_news: continue
                
                # 썸네일 검증
                valid_img_url = None
                valid_link = None
                for article in target_news:
                    extracted_img = self._extract_image(article['link'])
                    if extracted_img:
                        valid_img_url = extracted_img
                        valid_link = article['link']
                        break 
                
                if not valid_img_url:
                    continue # 썸네일 없으면 조용히 다음 후보로 패스

                articles_text = "\n".join([f"- {a['title']}: {a['description']}" for a in target_news])
                
                # 💡 [핵심 보완] 트래픽 컨트롤 + 50~100점 점수 부여
                summary_prompt = f"""
                Current Time: {now_kst}. Subject: '{name}' (Target Rank: {rank})
                News: {articles_text}
                
                CRITICAL RULES:
                1. FACT ONLY SUMMARY. NO expert analysis. Keep original proper nouns/numbers.
                2. Translate summary naturally to English.
                3. TRAFFIC CONTROL: Categorize by ACTION in the news, not by their usual job:
                   - Action = Variety show, YouTube guest, MC -> 'k-entertain'
                   - Action = Drama casting, movie release, acting -> 'k-actor'
                   - Action = Album release, concert, music charts -> 'k-pop'
                4. Assign a 'score' between 50 and 100 based on the news impact (Rank 1 should be closer to 100).
                
                JSON Format EXACTLY:
                {{
                    "category": "determined_category",
                    "keyword": "{name}",
                    "rank": {rank},
                    "title": "[{name}] English Translated Headline", 
                    "summary": "Factual English Summary",
                    "score": 85
                }}
                """
                try:
                    ai_res = self.ai_client.models.generate_content(model=self.model_name, contents=summary_prompt)
                    if ai_res.text:
                        data = json.loads(ai_res.text.replace("```json", "").replace("```", "").strip())
                        
                        assigned_cat = data.get("category", cat_key)
                        if assigned_cat not in categories_config: assigned_cat = cat_key
                        
                        raw_title = data.get("title", data.get("headline", "Untitled"))
                        if not raw_title.startswith(f"[{name}]"):
                            raw_title = f"[{name}] {raw_title.replace(f'[{name}]', '').strip()}"
                            
                        data['title'] = raw_title
                        data['category'] = assigned_cat
                        data['keyword'] = name 
                        data['link'] = valid_link
                        data['image_url'] = valid_img_url
                        data['score'] = data.get('score', 50) # 예외 대비 기본값 설정
                            
                        final_results[assigned_cat].append(data)
                        
                        if assigned_cat == cat_key:
                            current_cat_quota += 1
                            print(f"  ✅ [Rank {current_cat_quota}/10] {data['title']} ➔ [{assigned_cat}] 할당 (Score: {data['score']})")
                        else:
                            print(f"  🔄 [스필오버] {data['title']} ➔ [{assigned_cat}] 로드맵 변경! 빈자리 보충 탐색 재개.")
                except:
                    pass

        # 🎨 K-Culture 트렌드 트랙 (강력한 인물 배제 및 50~80점 룰)
        print("\n🎨 [K-Culture] 순수 트렌드 포착 파이프라인 (목표: 10개)...")
        culture_news = self._search_naver_keyword("MZ세대 트렌드 OR 팝업스토어 OR 디저트 밈 OR 챌린지", display=60)
        final_results["k-culture"] = []
        c_quota = 0
        
        for c_art in culture_news:
            if c_quota >= 10: break

            img = self._extract_image(c_art['link'])
            if not img: continue

            c_prompt = f"""
            Extract ONE viral K-Culture trend from this news.
            News: {c_art['title']} - {c_art['description']}
            
            CRITICAL RULE:
            EXCLUDE any news where a specific celebrity, actor, or idol group is the main subject. Focus ONLY on lifestyle, memes, food, or general trends.
            If the news is just about a celebrity, return an empty JSON {{}}.
            Assign a 'score' between 50 and 80 ONLY.
            
            JSON Format:
            {{
                "keyword": "Trend Name",
                "title": "[Trend Name] English Headline",
                "summary": "Fact only summary.",
                "score": 75
            }}
            """
            try:
                c_res = self.ai_client.models.generate_content(model=self.model_name, contents=c_prompt)
                c_data = json.loads(c_res.text.replace("```json", "").replace("```", "").strip())
                
                if c_data and c_data.get("keyword"):
                    trend_name = c_data["keyword"]
                    if trend_name in cooldown_names: continue

                    raw_title = c_data.get("title", c_data.get("headline", "Untitled"))
                    if not raw_title.startswith(f"[{trend_name}]"):
                        raw_title = f"[{trend_name}] {raw_title}"
                        
                    c_data.update({"category": "k-culture", "link": c_art['link'], "image_url": img, "rank": c_quota+1, "title": raw_title})
                    c_data['score'] = c_data.get('score', 50)
                    
                    final_results["k-culture"].append(c_data)
                    c_quota += 1
                    cooldown_names.add(trend_name)
                    print(f"  ✅ [k-culture Rank {c_quota}/10] 트렌드 기사화: {c_data['title']} (Score: {c_data['score']})")
            except:
                pass

        print("\n💾 [Step 8] 무결점 8단계 파이프라인 완료. DB 저장 프로세스로 데이터를 넘깁니다.")
        return final_results
