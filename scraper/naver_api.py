import os
import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup
import google.generativeai as genai

class NaverNewsAPI:
    def __init__(self, db_client, model_name):
        self.client_id = os.environ.get("NAVER_CLIENT_ID")
        self.client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        self.db = db_client
        
        # Gemini API 초기화 (model_manager에서 받아온 최적 모델 사용)
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(model_name)

    def _extract_image(self, url):
        """기사 원본 접속 -> og:image 고화질 썸네일 추출"""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            meta_img = soup.find("meta", property="og:image")
            if meta_img and meta_img.get("content"):
                img_url = meta_img["content"]
                if "dummy" not in img_url and "naver_logo" not in img_url:
                    return img_url
        except:
            pass
        return None
        
    def _discover_and_add_rookies(self, bulk_news, existing_names):
        """[AI 엔진] 신인 자동 발굴 및 드라마 배역명 철저 필터링"""
        print("🕵️‍♂️ AI 편집국장이 새로운 라이징 스타(신인)를 탐색합니다...")
        sample_news = "\n".join([f"- {a['title']}: {a['description']}" for a in bulk_news[:50]])
        
        prompt = f"""
        Task: Identify NEW rising Korean celebrities (Actors, Idols, Entertainers) from the news.
        News: {sample_news}
        Existing Database: {existing_names}
        
        CRITICAL RULES:
        1. Find proper names of REAL celebrities NOT in the existing list.
        2. STRICT FILTER: NEVER include character/role names from dramas or movies. Only real human names.
        3. Must be UNDER 50 years old (born after 1976).
        4. 'category' MUST BE strictly one of: 'k-pop', 'k-actor', 'k-entertain'.
        
        Format EXACTLY as JSON array: [{{"name": "RealName", "category": "k-actor", "birth_year": 1999}}]
        If none, return [].
        """
        try:
            res_text = self.model.generate_content(prompt).text
            new_celebs = json.loads(res_text.replace("```json", "").replace("```", "").strip())
            
            for celeb in new_celebs:
                print(f"🎉 [신인 발견] {celeb['name']} ({celeb['category']}) 명단 추가 완료!")
                self.db.client.table("celebrity_dict").insert({
                    "name": celeb['name'],
                    "default_category": celeb['category'],
                    "birth_year": celeb['birth_year']
                }).execute()
        except:
            pass

    def fetch_smart_news(self):
        """기사를 수집하고 카테고리별로 분류하여 반환합니다."""
        if not self.client_id: return {}

        # 1. DB 인물 사전 로드
        res = self.db.client.table("celebrity_dict").select("*").execute()
        celebrities = res.data
        existing_names = [c['name'] for c in celebrities]

        # 2. 최신 뉴스 100개씩 대량 수집
        bulk_news = []
        for q in ["예능 OR 유재석", "드라마 OR 배우", "아이돌 OR 신곡"]:
            url = "https://openapi.naver.com/v1/search/news.json"
            res_api = requests.get(url, headers={"X-Naver-Client-Id": self.client_id, "X-Naver-Client-Secret": self.client_secret}, params={"query": q, "display": 100, "sort": "sim"})
            if res_api.status_code == 200:
                bulk_news.extend(res_api.json().get('items', []))

        # 3. 신인 발굴 실행 및 명단 새로고침
        self._discover_and_add_rookies(bulk_news, existing_names)
        celebrities = self.db.client.table("celebrity_dict").select("*").execute().data

        # 결과를 카테고리별로 담을 딕셔너리 준비
        results = {"k-pop": [], "k-actor": [], "k-entertain": [], "k-culture": []}
        
        # 4. 인물 매칭 및 요약 (카테고리별 최대 10개 제한)
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
                
                # 편집국장 AI 프롬프트 (건조한 팩트 요약, 숫자/고유명사 원문 유지, 부서 이동)
                prompt = f"""
                You are the Chief Editor of a top Korean entertainment portal.
                Subject: '{name}'
                News: {articles_text}
                
                CRITICAL RULES:
                1. FACT ONLY: Summarize the facts strictly based on the text. NO expert analysis, NO extra opinions.
                2. EXACT MATCH: Keep all numbers (sales, ratings, etc.) and proper nouns EXACTLY as in the original text.
                3. TRAFFIC CONTROL:
                   - If news is about Variety Shows, category MUST BE 'k-entertain'.
                   - If about Acting/Drama/Movie, category MUST BE 'k-actor'.
                   - If about Music/Idols, category MUST BE 'k-pop'.
                4. SCORING: Assign a Hotness Score (50-100) based on actual buzz.
                
                Format EXACTLY as JSON:
                {{
                    "category": "determined_category",
                    "name": "{name}",
                    "title": "[{name}] English Headline",
                    "summary": "English Factual Summary",
                    "score": 85
                }}
                """
                try:
                    res_text = self.model.generate_content(prompt).text
                    data = json.loads(res_text.replace("```json", "").replace("```", "").strip())
                    
                    final_cat = data.get("category", category)
                    
                    # 각 카테고리당 10개까지만 수집하도록 속도 조절
                    if len(results.get(final_cat, [])) < 10:
                        data["link"] = target_link
                        data["image_url"] = image_url
                        results[final_cat].append(data)
                        
                        # 인물 노출일 최신화
                        self.db.client.table("celebrity_dict").update({"last_seen_at": "now()"}).eq("id", celeb['id']).execute()
                except:
                    pass

        # 5. K-Culture (고유명사 트렌드)
        if len(results["k-culture"]) < 10:
            try:
                url = "https://openapi.naver.com/v1/search/news.json"
                c_res = requests.get(url, headers={"X-Naver-Client-Id": self.client_id, "X-Naver-Client-Secret": self.client_secret}, params={"query": "팝업스토어 OR 디저트 OR 밈", "display": 15}).json().get('items', [])
                for c_art in c_res:
                    img = self._extract_image(c_art['link'])
                    if img:
                        c_prompt = f"""
                        Extract the SINGLE most viral K-Culture trend. EXCLUDE people's names. Score 50-80 ONLY.
                        News: {c_art['title']} - {c_art['description']}
                        JSON: {{ "name": "TrendName", "title": "Headline", "summary": "Fact only.", "score": 75 }}
                        """
                        c_data = json.loads(self.model.generate_content(c_prompt).text.replace("```json", "").replace("```", "").strip())
                        c_data.update({"link": c_art['link'], "image_url": img})
                        results["k-culture"].append(c_data)
                        break
            except:
                pass
                
        return results
