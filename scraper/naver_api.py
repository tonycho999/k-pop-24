import os
import requests
import json
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
import google.generativeai as genai

class NaverNewsAPI:
    def __init__(self, db_client, model_name):
        self.client_id = os.environ.get("NAVER_CLIENT_ID")
        self.client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        self.db = db_client
        
        # ModelManager에서 받아온 최적의 모델명으로 세팅
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(model_name)

    def _extract_image(self, url):
        """기사 원본 링크에 접속하여 고화질 썸네일(og:image)을 추출합니다."""
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

    def _search_naver_keyword(self, query, display=10):
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        params = {"query": query, "display": display, "sort": "sim"}
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            return res.json().get('items', [])
        except Exception:
            return []

    def _discover_and_add_rookies(self, bulk_news, existing_names):
        """🛡️ [3중 방어망 적용] 완벽한 무인 신인 발굴 시스템"""
        print("🕵️‍♂️ AI 스카우터가 새로운 라이징 스타를 탐색 중입니다...")
        
        sample_news = "\n".join([f"- {a['title']}: {a['description']}" for a in bulk_news[:50]])
        
        # [1차 방어] 증거(Evidence) 제출 의무화
        prompt = f"""
        Task: Identify NEW rising Korean celebrities (Actors, Idols, Entertainers) from the news.
        Recent News: {sample_news}
        Existing Database Names: {existing_names}
        
        CRITICAL RULES:
        1. Find proper names of REAL celebrities who are trending but NOT in the existing list.
        2. Must be UNDER 50 years old (born after 1976).
        3. STRICT: NO fictional character names from dramas/movies.
        4. You MUST provide the exact Korean sentence from the news as 'evidence' proving they are a real human actor/singer.
        
        Format EXACTLY as a JSON array:
        [
            {{
                "name": "RealName", 
                "category": "k-actor", 
                "birth_year": 1999,
                "evidence": "소속사 측은 배우 OOO의 데뷔를 알렸다."
            }}
        ]
        If no real new celebrities are found, return [].
        """
        try:
            res_text = self.model.generate_content(prompt).text
            if not res_text: return
            
            new_celebs = json.loads(res_text.replace("```json", "").replace("```", "").strip())
            
            # 금지어 리스트 (배역을 의미하는 단어들)
            forbidden_words = ["역", "배역", "캐릭터", "분한", "극중", "극 중", "세계관", "맡은"]
            
            for celeb in new_celebs:
                name = celeb.get("name")
                evidence = celeb.get("evidence", "")
                
                # [2차 방어] 파이썬 사형 집행관 (증거 문장에 금지어가 있으면 즉시 폐기)
                if any(word in evidence for word in forbidden_words):
                    print(f"🚫 [차단] '{name}'은(는) 배역 이름일 확률이 높습니다. (증거: {evidence})")
                    continue
                
                # [3차 방어] 네이버 실존 인물 교차 검증 (팩트 체크)
                validation_query = f"{name} 소속사 OR 데뷔 OR 프로필"
                validation_results = self._search_naver_keyword(validation_query, display=3)
                
                if not validation_results:
                    print(f"🚫 [차단] '{name}'에 대한 실존 연예인 정보(소속사/데뷔)가 부족합니다.")
                    continue
                
                # 3중 방어망을 모두 뚫은 진짜 신인만 DB에 저장!
                print(f"🎉 [신인 검증 완료!] AI가 진짜 스타 '{name}' ({celeb['category']})을(를) DB에 추가합니다.")
                self.db.client.table("celebrity_dict").insert({
                    "name": name,
                    "default_category": celeb.get('category', 'k-actor'),
                    "birth_year": celeb.get('birth_year', 2000)
                }).execute()
                
        except Exception as e:
            print(f"⚠️ Rookie Discovery Error: {e}")

    def fetch_smart_news(self):
        """그물망 매칭 + 팩트 체크 요약 + 카테고리 교통정리"""
        if not self.client_id: return {}

        # 1. DB 명단 로드
        try:
            res = self.db.client.table("celebrity_dict").select("*").execute()
            celebrities = res.data
            existing_names = [c['name'] for c in celebrities]
        except Exception:
            return {}

        # 2. 핫한 기사 300개 그물망 수집
        bulk_news = []
        queries = ["예능 OR 방송 OR 유재석", "드라마 OR 영화 OR 배우", "아이돌 OR 컴백 OR 신곡"]
        for q in queries:
            bulk_news.extend(self._search_naver_keyword(q, display=100))

        # 3. 3중 검증 신인 발굴 실행 (발굴 후 명단 새로고침)
        self._discover_and_add_rookies(bulk_news, existing_names)
        celebrities = self.db.client.table("celebrity_dict").select("*").execute().data

        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        results = {"k-pop": [], "k-actor": [], "k-entertain": [], "k-culture": []}

        # 4. 파이썬 초고속 매칭 및 AI 편집국장 요약
        for celeb in celebrities:
            category = celeb.get('default_category', 'k-actor')
            birth_year = celeb.get('birth_year')

            # K-Pop 50세 이하(1976년생 이후) 엄격 필터링
            if category == 'k-pop' and birth_year and int(birth_year) <= 1976:
                continue 
            
            name = celeb['name']
            matched_articles = [n for n in bulk_news if name in n['title'] or name in n['description']]
            
            if matched_articles:
                target_link = matched_articles[0]['link']
                image_url = self._extract_image(target_link)
                if not image_url: continue # 이미지 없으면 가차없이 폐기

                articles_text = "\n".join([f"- {a['title']}: {a['description']}" for a in matched_articles[:3]])
                
                prompt = f"""
                You are the Chief Editor of South Korea's top entertainment news portal.
                Current Time: {now_kst}
                Subject: '{name}'
                News: {articles_text}
                
                CRITICAL RULES:
                1. FACT ONLY SUMMARY: Summarize facts strictly based on text. NO expert analysis, NO extra opinions.
                2. EXACT MATCH: Keep all numbers and proper nouns EXACTLY as in original text. Translate naturally to English.
                3. TRAFFIC CONTROL:
                   - If news is about Variety Shows/YouTube, category MUST BE 'k-entertain'.
                   - If about Acting/Drama/Movie, category MUST BE 'k-actor'.
                   - If about Singing/Album, category MUST BE 'k-pop'.
                4. SCORING: Assign Hotness Score (50-100).
                
                Format EXACTLY as JSON:
                {{
                    "category": "determined_category",
                    "name": "{name}",
                    "title": "[{name}] English Headline",
                    "summary": "Factual English Summary",
                    "score": 85
                }}
                """
                try:
                    res_text = self.model.generate_content(prompt).text
                    if res_text:
                        data = json.loads(res_text.replace("```json", "").replace("```", "").strip())
                        final_cat = data.get("category", category)
                        
                        if len(results.get(final_cat, [])) < 10:
                            data["link"] = target_link
                            data["image_url"] = image_url
                            results[final_cat].append(data)
                            self.db.client.table("celebrity_dict").update({"last_seen_at": "now()"}).eq("id", celeb['id']).execute()
                except Exception:
                    pass

        # 5. K-Culture 처리 (문화 트렌드)
        if len(results["k-culture"]) < 10:
            culture_news = self._search_naver_keyword("팝업스토어 OR 디저트 OR 밈 OR 트렌드", display=15)
            for c_art in culture_news:
                img = self._extract_image(c_art['link'])
                if img:
                    c_prompt = f"""
                    Extract ONE viral K-Culture trend. EXCLUDE people's names. Score 50-80 ONLY.
                    News: {c_art['title']} - {c_art['description']}
                    JSON: {{ "name": "TrendName", "title": "English Headline", "summary": "Fact only summary.", "score": 75 }}
                    """
                    try:
                        c_res = self.model.generate_content(c_prompt).text
                        c_data = json.loads(c_res.replace("```json", "").replace("```", "").strip())
                        c_data.update({"category": "k-culture", "link": c_art['link'], "image_url": img})
                        results["k-culture"].append(c_data)
                        break
                    except:
                        pass
                
        return results
