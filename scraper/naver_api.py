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

    # 🛡️ Step 4: 팩트 체크망 (생존 서바이벌)
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
            print(f"    ❌ 탈락 [{name}]: 연예인 활동 증거(키워드) 없음")
            return False
            
        return True

    def run_8_step_pipeline(self):
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🕒 [Step 1] 시스템 KST 시간 설정 완료: {now_kst}")

        # 🌟 [핵심 보완] 5시간 쿨타임 및 자동 삭제 시스템
        # Supabase는 UTC 기준이므로 UTC로 5시간 전 계산
        five_hours_ago = datetime.utcnow() - timedelta(hours=5)
        try:
            # 1. 5시간 이전 데이터(오래된 기사)는 DB에서 완전히 삭제
            self.db.client.table("live_news").delete().lt("created_at", five_hours_ago.isoformat()).execute()
            print("🧹 [DB 정리] 5시간이 지난 오래된 기사를 삭제 완료했습니다.")
        except Exception as e:
            print(f"⚠️ DB 정리 실패: {e}")

        try:
            # 2. 최근 5시간 이내(1~4시간 전)에 작성된 기사의 주인공 명단 불러오기 (쿨타임 대상자)
            recent_res = self.db.client.table("live_news").select("keyword").gte("created_at", five_hours_ago.isoformat()).execute()
            cooldown_names = {row['keyword'] for row in recent_res.data if row.get('keyword')}
            print(f"⏳ [쿨타임 시스템] 최근 5시간 내 기사화되어 배제될 인물 수: {len(cooldown_names)}명")
        except:
            cooldown_names = set()

        categories_config = {
            "k-pop": "아이돌 OR 컴백 OR 보이그룹 OR 걸그룹 OR 솔로가수",
            "k-actor": "드라마 OR 영화 OR 배우",
            "k-entertain": "예능 OR 방송 OR MC OR 유재석"
        }
        
        final_results = {"k-pop": [], "k-actor": [], "k-entertain": [], "k-culture": []}

        # 🔄 카테고리별 독립 루프
        for cat_key, cat_query in categories_config.items():
            print(f"\n{'='*50}")
            print(f"🚀 [카테고리: {cat_key}] 10개 강제 할당 파이프라인 구동!")
            print(f"{'='*50}")
            
            bulk_news = self._search_naver_keyword(cat_query, display=100, sort="date")
            if not bulk_news:
                continue

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
                if len(valid_candidates) >= 40: # 할당량 10개를 위해 예비 후보를 40명까지 넉넉히 확보
                    break 
                
                # 💡 5시간 쿨타임 필터링 작동!
                if name in cooldown_names:
                    print(f"  ⏳ [쿨타임 배제] {name}: 최근 5시간 내 등록됨. 다양성 확보를 위해 스킵합니다.")
                    continue
                
                if name in existing_names:
                    print(f"  🟢 [유지] DB 존재: {name}")
                    valid_candidates.append(name)
                else:
                    print(f"  🔴 [검증] DB 없음, 팩트 체크 진입: {name}")
                    if self._is_valid_new_celeb(name):
                        try:
                            self.db.client.table("celebrity_dict").insert({
                                "name": name,
                                "default_category": cat_key, 
                                "birth_year": 2000
                            }).execute()
                            existing_names.add(name)
                            valid_candidates.append(name)
                            print(f"    🎉 [승인] 신규 연예인 DB 업데이트: {name}")
                        except Exception as e:
                            pass

            print(f"🚦 [Step 6 & 7] {cat_key} 10개 강제 할당 및 썸네일/트래픽 검증...")
            current_cat_quota = 0
            
            for name in valid_candidates:
                if current_cat_quota >= 10:
                    print(f"🎯 [{cat_key}] 목표 할당량 10개 완벽 달성! 루프 종료.")
                    break 
                
                rank = current_cat_quota + 1
                article_count = 3 if rank <= 5 else 2 
                target_news = self._search_naver_keyword(name, display=article_count, sort="sim")
                if not target_news: continue
                
                # 이미지 필터링 로직
                valid_img_url = None
                valid_link = None
                for article in target_news:
                    extracted_img = self._extract_image(article['link'])
                    if extracted_img:
                        valid_img_url = extracted_img
                        valid_link = article['link']
                        break 
                
                if not valid_img_url:
                    print(f"  ⏭️ [스킵] {name}: 썸네일 없음. 다음 후보로 넘어갑니다.")
                    continue 

                articles_text = "\n".join([f"- {a['title']}: {a['description']}" for a in target_news])
                
                summary_prompt = f"""
                Current Time: {now_kst}. Subject: '{name}' (Target Rank: {rank})
                News: {articles_text}
                
                CRITICAL RULES:
                1. FACT ONLY SUMMARY. Do NOT add expert analysis. Keep original proper nouns/numbers.
                2. Translate summary naturally to English.
                3. TRAFFIC CONTROL:
                   - Action = Variety show, YouTube guest, MC -> 'k-entertain'
                   - Action = Drama casting, movie release, acting -> 'k-actor'
                   - Action = Album release, concert, music charts -> 'k-pop'
                
                JSON Format EXACTLY:
                {{
                    "category": "determined_category",
                    "keyword": "{name}",
                    "rank": {rank},
                    "title": "[{name}] English Translated Headline", 
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
                        
                        raw_title = data.get("title", data.get("headline", "Untitled"))
                        if not raw_title.startswith(f"[{name}]"):
                            clean_title = raw_title.replace(f"[{name}]", "").strip()
                            raw_title = f"[{name}] {clean_title}"
                            
                        data['title'] = raw_title
                        data['category'] = assigned_cat
                        data['keyword'] = name # DB의 keyword 컬럼용 명시
                        data['link'] = valid_link
                        data['image_url'] = valid_img_url
                            
                        final_results[assigned_cat].append(data)
                        
                        if assigned_cat == cat_key:
                            current_cat_quota += 1
                            print(f"  ✅ [Rank {current_cat_quota}/10] {data['title']} ➔ [{assigned_cat}] 할당 성공")
                        else:
                            print(f"  🔄 [스필오버] {data['title']} ➔ [{assigned_cat}] 로드맵 변경! 빈자리 10개 채우기를 계속합니다.")
                except:
                    pass

        # 🎨 K-Culture 트렌드 트랙 (10개 강제 할당)
        print("\n🎨 [K-Culture] 순수 트렌드 포착 파이프라인 구동 (목표: 10개)...")
        culture_news = self._search_naver_keyword("MZ세대 트렌드 OR 팝업스토어 OR 디저트 밈 OR 챌린지", display=60)
        final_results["k-culture"] = []
        c_quota = 0
        
        for c_art in culture_news:
            if c_quota >= 10:
                print(f"🎯 [k-culture] 목표 할당량 10개 완벽 달성! 루프 종료.")
                break

            img = self._extract_image(c_art['link'])
            if not img:
                continue

            c_prompt = f"""
            Extract ONE viral K-Culture trend from this news.
            News: {c_art['title']} - {c_art['description']}
            
            CRITICAL RULE:
            EXCLUDE any news where a specific celebrity, actor, or idol group is the main subject. Focus ONLY on lifestyle, memes, food, or general trends.
            If the news is just about a celebrity, return an empty JSON {{}}.
            
            JSON Format:
            {{
                "keyword": "Trend Name",
                "title": "[Trend Name] English Headline",
                "summary": "Fact only summary."
            }}
            """
            try:
                c_res = self.ai_client.models.generate_content(model=self.model_name, contents=c_prompt)
                c_data = json.loads(c_res.text.replace("```json", "").replace("```", "").strip())
                
                if c_data and c_data.get("keyword"):
                    trend_name = c_data["keyword"]
                    
                    # 컬처도 쿨타임 검증 적용
                    if trend_name in cooldown_names:
                        continue

                    raw_title = c_data.get("title", c_data.get("headline", "Untitled"))
                    if not raw_title.startswith(f"[{trend_name}]"):
                        raw_title = f"[{trend_name}] {raw_title}"
                        
                    c_data.update({"category": "k-culture", "link": c_art['link'], "image_url": img, "rank": c_quota+1, "title": raw_title})
                    final_results["k-culture"].append(c_data)
                    c_quota += 1
                    cooldown_names.add(trend_name) # 같은 루프 내 중복 방지
                    print(f"  ✅ [k-culture Rank {c_quota}/10] 순수 트렌드 기사화 완료: {c_data['title']}")
            except:
                pass

        print("\n💾 [Step 8] 8단계 파이프라인 (10개 할당 보장) 완료. DB 저장 프로세스로 데이터를 넘깁니다.")
        return final_results
