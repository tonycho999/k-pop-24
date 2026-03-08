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
        
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(model_name)

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
        """🛡️ [그룹명 & 동의어 처리 추가] 신인 발굴 시스템"""
        print("🕵️‍♂️ AI 스카우터가 새로운 라이징 스타/아이돌 그룹을 탐색 중입니다...")
        
        sample_news = "\n".join([f"- {a['title']}: {a['description']}" for a in bulk_news[:50]])
        
        prompt = f"""
        Task: Identify NEW rising Korean celebrities (Actors, Idols, IDOL GROUPS, Entertainers) from the news.
        Recent News: {sample_news}
        Existing Database Names: {existing_names}
        
        CRITICAL RULES:
        1. Find proper names of REAL celebrities or GROUPS who are trending but NOT in the existing list.
        2. Must be UNDER 50 years old. For IDOL GROUPS, use their debut year as 'birth_year'.
        3. STRICT: NO fictional character names.
        4. ALIASES (IMPORTANT): If a group/person is known by multiple names (Korean and English), COMBINE them with a comma in the 'name' field. (e.g., "방탄소년단, BTS", "블랙핑크, BLACKPINK").
        5. Provide the exact Korean sentence from the news as 'evidence'.
        
        Format EXACTLY as a JSON array:
        [
            {{
                "name": "방탄소년단, BTS", 
                "category": "k-pop", 
                "birth_year": 2013,
                "evidence": "그룹 방탄소년단(BTS)이 빌보드 차트에 진입했다."
            }}
        ]
        If no new real names are found, return [].
        """
        try:
            res_text = self.model.generate_content(prompt).text
            if not res_text: return
            
            new_celebs = json.loads(res_text.replace("```json", "").replace("```", "").strip())
            forbidden_words = ["역", "배역", "캐릭터", "분한", "극중", "극 중", "세계관", "맡은"]
            
            for celeb in new_celebs:
                raw_name = celeb.get("name")
                evidence = celeb.get("evidence", "")
                
                if any(word in evidence for word in forbidden_words):
                    continue
                
                # 그룹/인물 첫 번째 이름을 대표 이름으로 삼아 교차 검증
                primary_name = raw_name.split(',')[0].strip()
                validation_query = f"{primary_name} 소속사 OR 데뷔 OR 프로필 OR 멤버"
                validation_results = self._search_naver_keyword(validation_query, display=3)
                
                if not validation_results:
                    continue
                
                print(f"🎉 [신인/그룹 검증 완료!] '{raw_name}' ({celeb['category']}) DB 추가 완료.")
                self.db.client.table("celebrity_dict").insert({
                    "name": raw_name,
                    "default_category": celeb.get('category', 'k-pop'),
                    "birth_year": celeb.get('birth_year', 2000)
                }).execute()
                
        except Exception as e:
            print(f"⚠️ Rookie Discovery Error: {e}")

    def fetch_smart_news(self):
        """다중 이름(쉼표) 스플릿 매칭 엔진 적용"""
        if not self.client_id: return {}

        try:
            res = self.db.client.table("celebrity_dict").select("*").execute()
            celebrities = res.data
            existing_names = [c['name'] for c in celebrities]
        except Exception:
            return {}

        bulk_news = []
        queries = ["예능 OR 방송 OR 유재석", "드라마 OR 영화 OR 배우", "아이돌 OR 컴백 OR 걸그룹 OR 보이그룹"]
        for q in queries:
            bulk_news.extend(self._search_naver_keyword(q, display=100))

        self._discover_and_add_rookies(bulk_news, existing_names)
        celebrities = self.db.client.table("celebrity_dict").select("*").execute().data

        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        results = {"k-pop": [], "k-actor": [], "k-entertain": [], "k-culture": []}

        for celeb in celebrities:
            category = celeb.get('default_category', 'k-actor')
            birth_year = celeb.get('birth_year')

            if category == 'k-pop' and birth_year and int(birth_year) <= 1976:
                continue 
            
            raw_name = celeb['name']
            
            # 💡 [핵심] 쉼표로 이름을 분리하여 리스트로 만듭니다. (예: ["방탄소년단", "BTS"])
            aliases = [alias.strip() for alias in raw_name.split(',')]
            primary_name = aliases[0] # 기사에 노출될 대표 이름
            
            # 기사 제목/내용에 여러 이름 중 하나라도 포함되어 있으면 매칭 성공!
            matched_articles = [
                n for n in bulk_news 
                if any(alias in n['title'] or alias in n['description'] for alias in aliases)
            ]
            
            if matched_articles:
                target_link = matched_articles[0]['link']
                image_url = self._extract_image(target_link)
                if not image_url: continue 

                articles_text = "\n".join([f"- {a['title']}: {a['description']}" for a in matched_articles[:3]])
                
                prompt = f"""
                You are the Chief Editor of South Korea's top entertainment news portal.
                Current Time: {now_kst}
                Subject: '{primary_name}'
                News: {articles_text}
                
                CRITICAL RULES:
                1. FACT ONLY SUMMARY: Summarize facts strictly based on text. NO expert analysis.
                2. EXACT MATCH: Keep all numbers and proper nouns EXACTLY as in original text. Translate naturally to English.
                3. TRAFFIC CONTROL:
                   - If news is about Variety Shows/YouTube, category MUST BE 'k-entertain'.
                   - If about Acting/Drama/Movie, category MUST BE 'k-actor'.
                   - If about Singing/Album/Concert, category MUST BE 'k-pop'.
                4. SCORING: Assign Hotness Score (50-100).
                
                Format EXACTLY as JSON:
                {{
                    "category": "determined_category",
                    "name": "{primary_name}",
                    "title": "[{primary_name}] English Headline",
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

        # 5. K-Culture 처리 
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
