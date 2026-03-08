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
        self.db = db_client  # database.py의 인스턴스
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
                # 네이버 기본 로고나 더미 이미지는 걸러냅니다.
                if "dummy" in img_url or "naver_logo" in img_url:
                    return None
                return img_url
        except Exception:
            pass
        return None
        
    def fetch_smart_news(self):
        """역방향 매칭 + 나이 맞춤 필터링 + 이미지 필수 로직"""
        if not self.client_id:
            print("❌ Naver API Keys not found!")
            return []

        # 1. DB에서 명단 모두 불러오기 (SQL 필터링 대신 파이썬 내부 필터링 사용)
        try:
            res = self.db.client.table("celebrity_dict").select("*").execute()
            celebrities = res.data
        except Exception as e:
            print(f"❌ DB 연예인 명단 로드 실패: {e}")
            return []

        # 2. 핫한 기사 뭉텅이로 긁어오기 (카테고리별 100개)
        bulk_news = []
        queries = ["예능 OR 방송 OR 유재석", "드라마 OR 영화 OR 배우", "아이돌 OR 컴백 OR 신곡"]
        for q in queries:
            bulk_news.extend(self._search_naver_keyword(q, display=100))

        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        processed_news = []

        # 3. 파이썬 내부에서 초고속 매칭 및 깐깐한 조건 검사
        for celeb in celebrities:
            category = celeb.get('default_category', '')
            birth_year = celeb.get('birth_year')

            # 💡 [핵심] K-Pop 카테고리만 50세 이상(1976년 이전 출생) 스킵
            if category == 'k-pop' and birth_year:
                if int(birth_year) <= 1976:
                    continue 
            
            name = celeb['name']
            matched_articles = [n for n in bulk_news if name in n['title'] or name in n['description']]
            
            if matched_articles:
                target_link = matched_articles[0]['link']
                
                # 💡 [핵심] 썸네일 이미지가 없으면 기사 가차없이 폐기
                image_url = self._extract_image(target_link)
                if not image_url:
                    continue # 이미지가 없으므로 이번 연예인은 패스

                articles_text = "\n".join([f"- {a['title']}: {a['description']}" for a in matched_articles[:5]])
                
                # 4. 제미나이 교통정리 및 점수 평가
                prompt = f"""
                Current Time: {now_kst}
                Subject: '{name}' (Original Category: {category})
                News: {articles_text}
                
                CRITICAL TRAFFIC CONTROL:
                Read the news context and ASSIGN the CORRECT category:
                - If the news is about starring in a Variety Show (예능, 유튜브 방송, 런닝맨 등), category MUST BE 'k-entertain'.
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
                            "image_url": image_url, # 정상 추출된 이미지만 저장
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

        # 💡 [핵심] K-Culture 역시 이미지가 존재하는 기사가 나올 때까지 찾습니다
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
            Extract the SINGLE most viral K-Culture trend (Food, Place, Meme) from these articles.
            STRICTLY EXCLUDE: Politics, ordinary news.
            Score freely between 50 and 80. (DO NOT EXCEED 80).
            Format EXACTLY as JSON: {{ "category": "k-culture", "title": "English Headline", "summary": "...", "score": 75 }}
            News: {culture_text}
            """
            try:
                culture_res = self.model.generate_content(culture_prompt)
                culture_data = json.loads(culture_res.replace("```json", "").replace("```", "").strip())
                culture_data["link"] = culture_target_link
                culture_data["image_url"] = culture_image_url # 정상 이미지 저장
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
            print(f"❌ Naver Search Error ({query}): {e}")
            return []
