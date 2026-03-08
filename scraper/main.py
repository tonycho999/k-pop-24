import os
import requests
import json
from datetime import datetime
import urllib.parse
import pytz
from bs4 import BeautifulSoup

class NaverNewsAPI:
    def __init__(self, db_client, model_manager):
        self.client_id = os.environ.get("NAVER_CLIENT_ID")
        self.client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        self.db = db_client
        self.model = model_manager

    def _extract_image(self, url):
        """기사 원본 링크에 접속하여 고화질 썸네일(og:image)을 추출합니다."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            meta_img = soup.find("meta", property="og:image")
            if meta_img and meta_img.get("content"):
                img_url = meta_img["content"]
                if "dummy" in img_url or "naver_logo" in img_url:
                    return None
                return img_url
        except Exception:
            pass
        return None
        
    def _discover_and_add_rookies(self, bulk_news, existing_names):
        """💡 [핵심 추가] AI가 뉴스를 읽고 DB에 없는 신인을 발굴해 자동으로 추가합니다."""
        print("🕵️‍♂️ AI가 새로운 라이징 스타(신인)를 탐색 중입니다...")
        
        # 토큰 절약을 위해 가장 화제성 높은 상위 50개 기사만 샘플링
        sample_news = "\n".join([f"- {a['title']}: {a['description']}" for a in bulk_news[:50]])
        
        prompt = f"""
        Task: Identify NEW rising Korean celebrities (Actors, Idols, Entertainers) from the news.
        
        Recent News:
        {sample_news}
        
        Existing Database Names (DO NOT INCLUDE THESE):
        {existing_names}
        
        CRITICAL RULES:
        1. Find proper names of REAL celebrities who are currently trending but NOT in the existing list.
        2. Must be UNDER 50 years old (born after 1976). If exact age is unknown but context implies they are young (e.g., rookie idol, young actor), estimate the birth year (e.g., 2000).
        3. 'category' MUST BE strictly one of: 'k-pop', 'k-actor', 'k-entertain'.
        4. Return ONLY a JSON array. If no new celebrities are found, return [].
        
        Format EXACTLY like this:
        [
            {{"name": "NewJeans", "category": "k-pop", "birth_year": 2004}},
            {{"name": "Lee Do-hyun", "category": "k-actor", "birth_year": 1995}}
        ]
        """
        try:
            res_text = self.model.generate_content(prompt)
            if not res_text: return
            
            json_str = res_text.replace("```json", "").replace("```", "").strip()
            new_celebs = json.loads(json_str)
            
            if new_celebs and len(new_celebs) > 0:
                print(f"🎉 [신인 발견!] AI가 {len(new_celebs)}명의 새로운 스타를 찾았습니다: {[c['name'] for c in new_celebs]}")
                for celeb in new_celebs:
                    # DB에 새 연예인 이름, 카테고리, 추정 출생연도 자동 Insert
                    self.db.client.table("celebrity_dict").insert({
                        "name": celeb['name'],
                        "default_category": celeb['category'],
                        "birth_year": celeb['birth_year']
                    }).execute()
        except Exception as e:
            print(f"⚠️ Rookie Discovery Error: {e}")

    def fetch_smart_news(self):
        """역방향 매칭 + 신인 자동 발굴 + 이미지/나이 필터링 로직"""
        if not self.client_id:
            print("❌ Naver API Keys not found!")
            return []

        # 1. DB에서 명단 불러오기
        try:
            res = self.db.client.table("celebrity_dict").select("*").execute()
            celebrities = res.data
            existing_names = [c['name'] for c in celebrities]
        except Exception as e:
            print(f"❌ DB 연예인 명단 로드 실패: {e}")
            return []

        # 2. 핫한 기사 뭉텅이로 긁어오기
        bulk_news = []
        queries = ["예능 OR 방송 OR 유재석", "드라마 OR 영화 OR 배우", "아이돌 OR 컴백 OR 신곡"]
        for q in queries:
            bulk_news.extend(self._search_naver_keyword(q, display=100))

        # 💡 [핵심 적용] 기존 매칭을 시작하기 전에, AI에게 먼저 훑어보고 신인이 있으면 DB에 넣으라고 지시
        self._discover_and_add_rookies(bulk_news, existing_names)
        
        # 신인이 방금 막 DB에 추가되었을 수 있으므로 명단을 최신화하여 다시 불러옴
        res = self.db.client.table("celebrity_dict").select("*").execute()
        celebrities = res.data

        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        processed_news = []

        # 3. 파이썬 내부에서 초고속 매칭 및 깐깐한 조건 검사
        for celeb in celebrities:
            category = celeb.get('default_category', '')
            birth_year = celeb.get('birth_year')

            # K-Pop 카테고리만 50세 이상(1976년 이전 출생) 스킵
            if category == 'k-pop' and birth_year:
                if int(birth_year) <= 1976:
                    continue 
            
            name = celeb['name']
            matched_articles = [n for n in bulk_news if name in n['title'] or name in n['description']]
            
            if matched_articles:
                target_link = matched_articles[0]['link']
                
                # 썸네일 이미지가 없으면 기사 가차없이 폐기
                image_url = self._extract_image(target_link)
                if not image_url:
                    continue 

                articles_text = "\n".join([f"- {a['title']}: {a['description']}" for a in matched_articles[:5]])
                
                # 4. 제미나이 교통정리 및 점수 평가
                prompt = f"""
                Current Time: {now_kst}
                Subject: '{name}' (Original Category: {category})
                News: {articles_text}
                
                CRITICAL TRAFFIC CONTROL:
                - If the news is about starring in a Variety Show (예능, 방송 등), category MUST BE 'k-entertain'.
                - If about acting (Drama/Movie), category MUST BE 'k-actor'.
                - If about singing/music chart/album, category MUST BE 'k-pop'.
                
                SCORING (50~100):
                Freely evaluate the buzz. DO NOT give everyone the same score.
                
                Format EXACTLY as JSON:
                {{
                    "category": "determined_category",
                    "title": "[{name}] English Headline",
                    "summary": "English Factual Summary",
                    "score": 85
                }}
                """
                
                try:
                    result_text = self.model.generate_content(prompt)
                    if result_text:
                        json_str = result_text.replace("```json", "").replace("```", "").strip()
                        ai_data = json.loads(json_str)
                        
                        processed_news.append({
                            "category": ai_data.get("category", category),
                            "title": ai_data.get("title", f"[{name}] News Update"),
                            "summary": ai_data.get("summary", ""),
                            "score": ai_data.get("score", 70),
                            "link": target_link,
                            "image_url": image_url,
                            "created_at": datetime.utcnow().isoformat()
                        })
                        
                        # DB의 마지막 노출일 업데이트
                        self.db.client.table("celebrity_dict").update({"last_seen_at": "now()"}).eq("id", celeb['id']).execute()
                        
                except Exception as e:
                    print(f"⚠️ Gemini Processing Error for {name}: {e}")

        # 5. K-Culture 처리 (이미지 있는 기사 찾기)
        culture_news = self._search_naver_keyword("팝업스토어 OR 트렌드 OR 핫플 OR 바이럴", display=20)
        culture_target_link = None
        culture_image_url = None
        culture_articles_to_use = []

        for article in culture_news:
            img = self._extract_image(article['link'])
            if img:
                culture_target_link = article['link']
                culture_image_url = img
                culture_articles_to_use.append(article)
                break 

        if culture_image_url and culture_articles_to_use:
            culture_text = "\n".join([f"- {a['title']}: {a['description']}" for a in culture_articles_to_use])
            culture_prompt = f"""
            Extract the SINGLE most viral K-Culture trend from these articles.
            Score freely between 50 and 80. (DO NOT EXCEED 80).
            Format EXACTLY as JSON: {{ "category": "k-culture", "title": "English Headline", "summary": "...", "score": 75 }}
            News: {culture_text}
            """
            try:
                culture_res = self.model.generate_content(culture_prompt)
                culture_data = json.loads(culture_res.replace("```json", "").replace("```", "").strip())
                culture_data["link"] = culture_target_link
                culture_data["image_url"] = culture_image_url
                culture_data["created_at"] = datetime.utcnow().isoformat()
                processed_news.append(culture_data)
            except:
                pass
                
        return processed_news

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
        except Exception as e:
            return []
