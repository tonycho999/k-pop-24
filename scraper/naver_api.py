import os
import requests
import json
from collections import Counter
from datetime import datetime
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

    def _extract_image(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            meta_img = soup.find("meta", property="og:image")
            if meta_img and meta_img.get("content"):
                img_url = meta_img["content"]
                if "dummy" not in img_url and "naver_logo" not in img_url:
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

    # 🛡️ Step 4: 팩트 체크망 (가짜 배역명 차단 및 실존 인증)
    def _is_valid_new_celeb(self, name):
        forbidden_words = ["역", "캐릭터", "배역", "분한", "극중", "극 중"]
        if any(word in name for word in forbidden_words) or len(name) < 2:
            print(f"    ❌ 탈락 [{name}]: 금지어 포함 또는 이름이 너무 짧음")
            return False

        role_check = self._search_naver_keyword(f'"{name} 역" OR "{name} 분한"', display=5)
        if len(role_check) >= 3:
            print(f"    ❌ 탈락 [{name}]: 드라마 배역/캐릭터명으로 100% 의심됨")
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
            print(f"    ❌ 탈락 [{name}]: 연예인 활동 증거(키워드) 없음 (일반인/타분야/가명)")
            return False
            
        return True

    def run_8_step_pipeline(self):
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🕒 [Step 1] 시스템 KST 시간 설정 완료: {now_kst}")

        categories_config = {
            "k-pop": "아이돌 OR 컴백 OR 보이그룹 OR 걸그룹 OR 솔로가수",
            "k-actor": "드라마 OR 영화 OR 배우",
            "k-entertain": "예능 OR 방송 OR MC OR 유재석"
        }
        
        final_results = {"k-pop": [], "k-actor": [], "k-entertain": [], "k-culture": []}

        # 🔄 카테고리별 독립 루프 시작
        for cat_key, cat_query in categories_config.items():
            print(f"\n{'='*50}")
            print(f"🚀 [카테고리: {cat_key}] 독립 파이프라인 구동 시작!")
            print(f"{'='*50}")
            
            # Step 2: 해당 카테고리 뉴스만 100개 긁어오기
            bulk_news = self._search_naver_keyword(cat_query, display=100, sort="date")
            if not bulk_news:
                print(f"⚠️ 뉴스를 가져오지 못했습니다. 패스.")
                continue

            # Step 3: AI 이름 추출 & 빈도수 랭킹
            sample_titles = "\n".join([f"- {a['title']}" for a in bulk_news[:60]])
            extract_prompt = f"""
            Extract only REAL proper names of Korean celebrities, actors, or idol groups from these headlines.
            Identify groups and solo acts as distinct entities.
            Headlines: {sample_titles}
            Return EXACTLY a JSON list of strings. Example: ["유재석", "방탄소년단", "차은우"]
            """
            try:
                res = self.ai_client.models.generate_content(model=self.model_name, contents=extract_prompt)
                extracted_names = json.loads(res.text.replace("```json", "").replace("```", "").strip())
            except Exception as e:
                print(f"⚠️ AI Name Extraction Error: {e}")
                extracted_names = []

            name_counter = Counter()
            for name in extracted_names:
                count = sum(1 for n in bulk_news if name in n['title'] or name in n['description'])
                if count > 0:
                    name_counter[name] = count

            sorted_candidates = [name for name, count in name_counter.most_common()]
            
            # Step 4 & 5: 예비 명단 20명 확보 (할당량 보충을 위해 넉넉히)
            try:
                db_res = self.db.client.table("celebrity_dict").select("name").execute()
                existing_names = {row['name'].split(',')[0].strip() for row in db_res.data}
            except:
                existing_names = set()

            valid_candidates = []
            for name in sorted_candidates:
                if len(valid_candidates) >= 20: # 넉넉하게 20명 확보
                    break 
                
                if name in existing_names:
                    print(f"  🟢 [유지] DB 존재: {name} ({name_counter[name]}회)")
                    valid_candidates.append(name)
                else:
                    print(f"  🔴 [검증] DB 없음, 팩트 체크 진입: {name}")
                    if self._is_valid_new_celeb(name):
                        print(f"    🎉 [승인] 신규 연예인 DB 업데이트: {name}")
                        try:
                            self.db.client.table("celebrity_dict").insert({
                                "name": name,
                                "default_category": cat_key, 
                                "birth_year": 2000
                            }).execute()
                            existing_names.add(name)
                            valid_candidates.append(name)
                        except Exception as e:
                            print(f"    ⚠️ DB 저장 실패: {e}")

            # Step 6 & 7: 차등 검색 및 트래픽 컨트롤 (할당량 10개 채우기)
            print(f"🚦 [Step 6 & 7] {cat_key} 할당량 10개 달성을 위한 기사 작성 및 분류...")
            current_cat_quota = 0
            
            for idx, name in enumerate(valid_candidates):
                if current_cat_quota >= 10:
                    print(f"🎯 [{cat_key}] 목표 할당량 10개 달성 완료! 루프를 종료합니다.")
                    break 
                
                # 순위 배정 로직 (1~5위는 3개, 그 외는 2개 참조)
                rank = current_cat_quota + 1
                article_count = 3 if rank <= 5 else 2 
                target_news = self._search_naver_keyword(name, display=article_count, sort="sim")
                if not target_news: continue
                
                articles_text = "\n".join([f"- {a['title']}: {a['description']}" for a in target_news])
                
                # 💡 JSON 키값을 headline에서 title로 수정!
                summary_prompt = f"""
                Current Time: {now_kst}. Subject: '{name}' (Target Rank: {rank})
                News: {articles_text}
                
                CRITICAL RULES:
                1. FACT ONLY SUMMARY. Do NOT add expert analysis or extra opinions. Keep original proper nouns/numbers.
                2. Translate summary naturally to English.
                3. TRAFFIC CONTROL (Categorize by ACTION, not by the person's usual job):
                   - Action = Variety show, YouTube guest, MC, TV Broadcaster -> 'k-entertain'
                   - Action = Drama casting, movie release, acting, pictorials -> 'k-actor'
                   - Action = Album release, concert, music charts, fan meeting -> 'k-pop'
                   Evaluate the main action in the provided news and determine the EXACT category.
                
                JSON Format EXACTLY:
                {{
                    "category": "determined_category",
                    "name": "{name}",
                    "rank": {rank},
                    "title": "[{name}] English Headline", 
                    "summary": "Factual English Summary"
                }}
                """
                try:
                    ai_res = self.ai_client.models.generate_content(model=self.model_name, contents=summary_prompt)
                    if ai_res.text:
                        data = json.loads(ai_res.text.replace("```json", "").replace("```", "").strip())
                        assigned_cat = data.get("category", cat_key)
                        
                        if assigned_cat not in categories_config:
                            assigned_cat = cat_key
                            
                        data['category'] = assigned_cat
                        data['link'] = target_news[0]['link'] 
                        
                        img_url = self._extract_image(target_news[0]['link'])
                        if img_url: 
                            data['image_url'] = img_url
                            
                        final_results[assigned_cat].append(data)
                        
                        # 할당량 체크 로직
                        if assigned_cat == cat_key:
                            current_cat_quota += 1
                            print(f"  ✅ [Rank {current_cat_quota}] {name} ➔ [{assigned_cat}] 정상 할당 완료 (참고 기사: {article_count}개)")
                        else:
                            print(f"  🔄 [스필오버 발생] {name} 기사는 [{assigned_cat}] 카테고리로 이동! [{cat_key}] 할당량(현재 {current_cat_quota}개) 보충을 위해 다음 후보를 계속 탐색합니다...")
                except Exception as e:
                    pass

        # 🎨 K-Culture 트렌드 트랙 (동일)
        print("\n🎨 [K-Culture] 순수 트렌드 포착 파이프라인 구동...")
        culture_news = self._search_naver_keyword("MZ세대 트렌드 OR 팝업스토어 OR 디저트 밈 OR 챌린지", display=15)
        final_results["k-culture"] = []
        
        for c_art in culture_news:
            img = self._extract_image(c_art['link'])
            if img:
                c_prompt = f"""
                Extract ONE viral K-Culture trend from this news.
                News: {c_art['title']} - {c_art['description']}
                
                CRITICAL RULE:
                EXCLUDE any news where a specific celebrity, actor, or idol group is the main subject. Focus ONLY on lifestyle, memes, food, or general trends.
                If the news is just about a celebrity, return an empty JSON {{}}.
                
                JSON Format:
                {{
                    "name": "Trend Name",
                    "title": "English Headline",
                    "summary": "Fact only summary."
                }}
                """
                try:
                    c_res = self.ai_client.models.generate_content(model=self.model_name, contents=c_prompt)
                    c_data = json.loads(c_res.text.replace("```json", "").replace("```", "").strip())
                    
                    if c_data and c_data.get("name"):
                        c_data.update({"category": "k-culture", "link": c_art['link'], "image_url": img, "rank": 1})
                        final_results["k-culture"].append(c_data)
                        print(f"  ✅ [k-culture] 순수 트렌드 기사화 완료: {c_data.get('name')}")
                        break 
                except:
                    pass

        print("\n💾 [Step 8] 8단계 파이프라인 완료. 메인 DB 저장 프로세스로 데이터를 넘깁니다.")
        return final_results
