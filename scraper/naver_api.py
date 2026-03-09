import os
import requests
import json
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

    def _search_naver_keyword(self, query, display=10):
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        params = {"query": query, "display": display, "sort": "sim"}
        try:
            res = requests.get(url, headers=headers, params=params, timeout=30)
            res.raise_for_status()
            return res.json().get('items', [])
        except Exception:
            return []

    def _discover_and_add_rookies(self, bulk_news, existing_names):
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
        4. ALIASES: If known by multiple names (Korean and English), COMBINE with a comma (e.g., "방탄소년단, BTS").
        5. Provide the exact Korean sentence from the news as 'evidence'.
        
        Format EXACTLY as a JSON array:
        [
            {{
                "name": "방탄소년단, BTS", 
                "category": "k-pop", 
                "birth_year": 2013,
                "evidence": "그룹 방탄소년단(BTS)이 차트에 진입했다."
            }}
        ]
        If no new real names are found, return [].
        """
        try:
            # 💡 신형 generate_content 호출 방식 적용
            response = self.ai_client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            res_text = response.text
            if not res_text: return
            
            new_celebs = json.loads(res_text.replace("```json", "").replace("```", "").strip())
            forbidden_words = ["역", "배역", "캐릭터", "분한", "극중", "극 중", "세계관", "맡은"]
            
            for celeb in new_celebs:
                raw_name = celeb.get("name")
                evidence = celeb.get("evidence", "")
                
                if any(word in evidence for word in forbidden_words):
                    continue
                
                primary_name = raw_name.split(',')[0].strip()
                validation_query = f"{primary_name} 소속사 OR 데뷔 OR 프로필 OR 멤버"
                validation_results = self._search_naver_keyword(validation_query, display=3)
                
                if not validation_results:
                    continue
                
                print(f"🎉 [신인 검증 완료] '{raw_name}' ({celeb['category']}) DB 추가 완료.")
                self.db.client.table("celebrity_dict").insert({
                    "name": raw_name,
                    "default_category": celeb.get('category', 'k-pop'),
                    "birth_year": celeb.get('birth_year', 2000)
                }).execute()
        except Exception as e:
            print(f"⚠️ Rookie Discovery Error: {e}")

    def fetch_smart_news(self):
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
            aliases = [alias.strip() for alias in raw_name.split(',')]
            primary_name = aliases[0]
            
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
                1. FACT ONLY SUMMARY. NO expert analysis.
                2. EXACT MATCH: Keep all numbers and proper nouns EXACTLY as in original text. Translate naturally to English.
                3. TRAFFIC CONTROL:
                   - Variety Shows/YouTube -> 'k-entertain'
                   - Acting/Drama/Movie -> 'k-actor'
                   - Singing/Album/Concert -> 'k-pop'
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
                    # 💡 신형 generate_content 호출 방식 적용
                    response = self.ai_client.models.generate_content(
                        model=self.model_name,
                        contents=prompt
                    )
                    res_text = response.text
                    
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
                        # 💡 신형 generate_content 호출 방식 적용
                        c_res = self.ai_client.models.generate_content(
                            model=self.model_name,
                            contents=c_prompt
                        )
                        c_data = json.loads(c_res.text.replace("```json", "").replace("```", "").strip())
                        c_data.update({"category": "k-culture", "link": c_art['link'], "image_url": img})
                        results["k-culture"].append(c_data)
                        break
                    except:
                        pass
                
        return results
