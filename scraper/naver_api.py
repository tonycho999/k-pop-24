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

    # 🛡️ [핵심 보완] 4번 단계: 신인 검증 철통 방어망
    def _is_valid_new_celeb(self, name):
        forbidden_words = ["역", "캐릭터", "배우", "가수", "감독", "멤버", "분한"]
        if any(word in name for word in forbidden_words) or len(name) < 2:
            print(f"    ❌ 탈락 [{name}]: 금지어 포함 또는 이름이 너무 짧음")
            return False, "k-actor"

        # 방어망 1: 배역명 역방향 검증 (함정 수사)
        # "선재 역", "백현우 역" 등으로 검색해서 결과가 우수수 나오면 캐릭터 이름임!
        role_check = self._search_naver_keyword(f'"{name} 역" OR "{name} 분한"', display=5)
        if len(role_check) >= 3:
            print(f"    ❌ 탈락 [{name}]: 드라마 배역/캐릭터명으로 강하게 의심됨")
            return False, "k-actor"

        # 방어망 2: 소속사/데뷔 필수 인증 (결정적 증거)
        # 진짜 연예인이라면 프로필이나 소속사 기사가 무조건 있어야 함
        agency_check = self._search_naver_keyword(f"{name} 소속사 OR {name} 프로필 OR {name} 데뷔", display=3)
        if not agency_check:
            print(f"    ❌ 탈락 [{name}]: 소속사/데뷔 정보 없음 (일반인/가명 가능성)")
            return False, "k-actor"
        
        return True, "k-actor" # 기본 카테고리 지정

    def run_7_step_pipeline(self):
        # 🕒 Step 1: 봇과 AI에게 한국 날짜/시간 인지
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🕒 [Step 1] 시스템 KST 시간 설정 완료: {now_kst}")

        # 📰 Step 2: 네이버 뉴스 스크래핑 (데이터 싹쓸이)
        print("📰 [Step 2] 네이버 뉴스 긁어오기 시작...")
        queries = ["예능 OR 방송", "드라마 OR 영화 OR 배우", "아이돌 OR 컴백 OR 보이그룹 OR 걸그룹"]
        bulk_news = []
        for q in queries:
            bulk_news.extend(self._search_naver_keyword(q, display=100, sort="date")) # 최신순
        
        if not bulk_news:
            return {}

        # 🤖 Step 3: 기사 이름 추출 및 파이썬 빈도수 랭킹
        print("🤖 [Step 3] AI 이름 추출 및 파이썬 빈도수 카운팅...")
        # AI 소화불량을 막기 위해 '제목'만 50개 추려서 이름만 뽑게 시킴
        sample_titles = "\n".join([f"- {a['title']}" for a in bulk_news[:50]])
        extract_prompt = f"""
        Extract only REAL proper names of Korean celebrities/groups from these headlines.
        Headlines: {sample_titles}
        Return EXACTLY a JSON list of strings. Example: ["유재석", "방탄소년단", "김지원"]
        """
        try:
            res = self.ai_client.models.generate_content(model=self.model_name, contents=extract_prompt)
            extracted_names = json.loads(res.text.replace("```json", "").replace("```", "").strip())
        except Exception as e:
            print(f"⚠️ AI Name Extraction Error: {e}")
            extracted_names = []

        # 💡 [초고속 최적화] AI가 찾은 이름을 바탕으로 파이썬이 전체 뉴스에서 언급 횟수를 직접 셉니다!
        name_counter = Counter()
        for name in extracted_names:
            count = sum(1 for n in bulk_news if name in n['title'] or name in n['description'])
            if count > 0:
                name_counter[name] = count

        # 많이 언급된 순서대로 정렬 (이름 A: 10회, 이름 B: 9회...)
        sorted_candidates = [name for name, count in name_counter.most_common()]
        
        # 🛡️ Step 4 & 5: DB 대조 및 Top 10 최종 완성
        print("🛡️ [Step 4 & 5] DB 대조 및 Top 10 랭킹 확정 중...")
        try:
            db_res = self.db.client.table("celebrity_dict").select("name").execute()
            existing_names = {row['name'].split(',')[0].strip() for row in db_res.data}
        except:
            existing_names = set()

        final_top_10 = []
        for name in sorted_candidates:
            if len(final_top_10) >= 10: 
                break # 딱 10명만 채우면 멈춤
            
            if name in existing_names:
                print(f"  🟢 [유지] DB 존재: {name} ({name_counter[name]}회)")
                final_top_10.append(name)
            else:
                print(f"  🔴 [검증] DB 없음, 팩트 체크 진입: {name}")
                is_valid, category = self._is_valid_new_celeb(name)
                
                if is_valid:
                    print(f"    🎉 [승인] 신규 연예인 DB 업데이트: {name}")
                    try:
                        self.db.client.table("celebrity_dict").insert({
                            "name": name,
                            "default_category": category,
                            "birth_year": 2000
                        }).execute()
                        existing_names.add(name)
                        final_top_10.append(name)
                    except Exception as e:
                        print(f"    ⚠️ DB 저장 실패: {e}")

        # 📝 Step 6: 1~10위 차등 기사 검색 및 팩트 요약
        print("📝 [Step 6] Top 10 차등 기사 검색 및 AI 팩트 요약...")
        final_results = {"k-pop": [], "k-actor": [], "k-entertain": []} # 편의상 분배
        
        for idx, name in enumerate(final_top_10):
            rank = idx + 1
            # 1~5위는 3개, 6~10위는 2개 검색
            article_count = 3 if rank <= 5 else 2 
            
            target_news = self._search_naver_keyword(name, display=article_count)
            if not target_news: continue
            
            articles_text = "\n".join([f"- {a['title']}: {a['description']}" for a in target_news])
            
            summary_prompt = f"""
            Current Time: {now_kst}. Subject: '{name}' (Rank: {rank})
            News: {articles_text}
            
            CRITICAL RULES:
            1. FACT ONLY SUMMARY. Do NOT add expert analysis or extra opinions.
            2. Summarize ONLY the important parts from the text provided.
            3. Keep numbers and proper nouns EXACTLY as in the original text. Translate naturally to English.
            
            JSON Format EXACTLY:
            {{
                "name": "{name}",
                "rank": {rank},
                "headline": "[{name}] English Headline",
                "summary": "Factual English Summary"
            }}
            """
            try:
                ai_res = self.ai_client.models.generate_content(model=self.model_name, contents=summary_prompt)
                if ai_res.text:
                    data = json.loads(ai_res.text.replace("```json", "").replace("```", "").strip())
                    data['link'] = target_news[0]['link'] # 첫 번째 기사 링크 첨부
                    # 임의로 k-actor 카테고리에 넣음 (이후 분류 로직 필요시 추가)
                    final_results["k-actor"].append(data)
                    print(f"  ✅ [Rank {rank}] {name} 기사 요약 완료 (참고 기사: {article_count}개)")
            except:
                pass

        # 💾 Step 7: DB 저장
        print("💾 [Step 7] 요약 완료. 메인 DB 저장 프로세스로 데이터를 넘깁니다.")
        return final_results
