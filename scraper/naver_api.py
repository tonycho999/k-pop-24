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
        
        # 💡 신형 Client + 30초 타임아웃 방어막
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
            res = requests.get(url, headers=headers, params=params, timeout=10)
            res.raise_for_status()
            return res.json().get('items', [])
        except Exception as e:
            print(f"⚠️ Naver API Search Error ({query}): {e}")
            return []

    # 💡 하이브리드 고속 파이프라인의 핵심 오케스트레이터 (기존 로직 통합 변경)
    def fetch_smart_news(self):
        print("🚀 [Phase 1] 뉴스 데이터 그물망 스크래핑 시작...")
        bulk_news = []
        queries = ["예능 OR 방송 OR 유재석", "드라마 OR 영화 OR 배우", "아이돌 OR 컴백 OR 걸그룹 OR 보이그룹"]
        for q in queries:
            bulk_news.extend(self._search_naver_keyword(q, display=100))
        
        if not bulk_news:
            print("⚠️ 뉴스를 가져오지 못했습니다.")
            return {}

        # AI에게 던질 기사 샘플 (문맥 과부하를 막기 위해 상위 60개만 요약본으로 추출)
        sample_news = "\n".join([f"- {a['title']}: {a['description']}" for a in bulk_news[:60]])
        
        print("🕵️‍♂️ [Phase 2] AI 단기 속성 과외 (이름만 싹 다 뽑아내는 중!)...")
        extraction_prompt = f"""
        Task: Extract proper names of Korean celebrities (Actors, Idols, IDOL GROUPS, Entertainers) from the news.
        News: {sample_news}
        
        CRITICAL RULES:
        1. Extract ONLY proper names of real people or groups. NO fictional characters.
        2. ALIASES: Combine known aliases with a comma (e.g., "방탄소년단, BTS").
        3. Provide a brief evidence sentence from the news.
        
        Format EXACTLY as a JSON array:
        [
            {{
                "name": "Celebrity Name",
                "category": "k-pop",
                "birth_year": 2000,
                "evidence": "Factual sentence from news"
            }}
        ]
        If none found, return [].
        """
        
        extracted_celebs = []
        try:
            response = self.ai_client.models.generate_content(
                model=self.model_name,
                contents=extraction_prompt
            )
            if response.text:
                extracted_celebs = json.loads(response.text.replace("```json", "").replace("```", "").strip())
        except Exception as e:
            print(f"⚠️ AI Name Extraction Error: {e}")
            return {}

        print(f"🔍 AI가 기사에서 총 {len(extracted_celebs)}명의 연예인을 포착했습니다.")

        print("⚡ [Phase 3] DB 일괄 대조 (초고속 인덱스 스캔)...")
        # 💡 전체 DB가 아닌 '이름' 컬럼만 가볍게 가져와 파이썬의 Set(집합)으로 변환하여 O(1) 빛의 속도로 검색합니다.
        try:
            res = self.db.client.table("celebrity_dict").select("name").execute()
            existing_primary_names = {row['name'].split(',')[0].strip() for row in res.data}
        except Exception as e:
            print(f"⚠️ DB 명단 조회 실패: {e}")
            existing_primary_names = set()

        print("🛤️ [Phase 4] 투 트랙(Two-Track) 팩트 체크 및 신인 발굴...")
        validated_celebs = []
        forbidden_words = ["역", "배역", "캐릭터", "분한", "극중", "극 중", "세계관", "맡은"]

        for celeb in extracted_celebs:
            raw_name = celeb.get("name")
            if not raw_name: continue
            
            primary_name = raw_name.split(',')[0].strip()
            evidence = celeb.get("evidence", "")

            # 트랙 1: 이미 DB에 있는 경우 (프리패스)
            if primary_name in existing_primary_names:
                print(f"  🟢 [기존 인물] 프리패스: {primary_name}")
                validated_celebs.append(celeb)
            
            # 트랙 2: DB에 없는 경우 (신규 발굴 팩트 체크)
            else:
                print(f"  🔴 [신규 후보] 팩트 체크 진입: {raw_name}")
                if any(word in evidence for word in forbidden_words):
                    print(f"    ❌ 탈락: 배역/캐릭터명 금지어 감지")
                    continue
                
                # 네이버에 실존 여부 검색
                val_query = f"{primary_name} 소속사 OR 데뷔 OR 프로필 OR 멤버"
                val_res = self._search_naver_keyword(val_query, display=3)
                
                if not val_res:
                    print(f"    ❌ 탈락: 네이버 검색 결과 없음 (허구 인물 가능성)")
                    continue
                
                print(f"    🎉 [신인 등록] '{raw_name}' 실존 확인! DB에 정식 추가합니다.")
                try:
                    self.db.client.table("celebrity_dict").insert({
                        "name": raw_name,
                        "default_category": celeb.get('category', 'k-actor'),
                        "birth_year": celeb.get('birth_year', 2000)
                    }).execute()
                    
                    validated_celebs.append(celeb)
                    existing_primary_names.add(primary_name) # 방금 추가된 신인도 메모리에 업데이트
                except Exception as e:
                    print(f"    ⚠️ DB 신인 추가 실패: {e}")

        print("📝 [Phase 5] 검증된 명단을 바탕으로 맞춤형 영문 기사 작성 및 점수 부여...")
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        results = {"k-pop": [], "k-actor": [], "k-entertain": [], "k-culture": []}

        # 검증된 연예인들(기존+신규)에 대해서만 기사 생성
        for celeb in validated_celebs:
            raw_name = celeb.get("name")
            aliases = [alias.strip() for alias in raw_name.split(',')]
            primary_name = aliases[0]
            category = celeb.get('category', 'k-actor')
            
            matched_articles = [n for n in bulk_news if any(alias in n['title'] or alias in n['description'] for alias in aliases)]
            
            if matched_articles:
                target_link = matched_articles[0]['link']
                image_url = self._extract_image(target_link)
                if not image_url: continue 

                articles_text = "\n".join([f"- {a['title']}: {a['description']}" for a in matched_articles[:3]])
                
                summary_prompt = f"""
                You are the Chief Editor of a K-pop news portal.
                Current Time: {now_kst}. Subject: '{primary_name}'
                News: {articles_text}
                
                RULES: 1. FACT ONLY SUMMARY. NO expert analysis. 2. EXACT MATCH numbers/nouns. Translate to English. 3. Assign Hotness Score (50-100).
                
                JSON Format EXACTLY:
                {{
                    "category": "{category}",
                    "name": "{primary_name}",
                    "title": "[{primary_name}] English Headline",
                    "summary": "Factual English Summary",
                    "score": 85
                }}
                """
                try:
                    res = self.ai_client.models.generate_content(model=self.model_name, contents=summary_prompt)
                    if res.text:
                        data = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                        final_cat = data.get("category", category)
                        
                        if len(results.get(final_cat, [])) < 10:
                            data["link"] = target_link
                            data["image_url"] = image_url
                            results[final_cat].append(data)
                            print(f"  ✅ [{final_cat}] '{primary_name}' 기사화 및 점수 부여 완료!")
                except Exception:
                    pass

        # K-Culture 트렌드 (동일)
        if len(results["k-culture"]) < 10:
            print("🎨 [Phase 6] K-Culture 트렌드 포착 중...")
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
                        c_res = self.ai_client.models.generate_content(model=self.model_name, contents=c_prompt)
                        c_data = json.loads(c_res.text.replace("```json", "").replace("```", "").strip())
                        c_data.update({"category": "k-culture", "link": c_art['link'], "image_url": img})
                        results["k-culture"].append(c_data)
                        print(f"  ✅ [k-culture] 최신 트렌드 기사화 완료: {c_data.get('name')}")
                        break
                    except:
                        pass
                
        print("🎉 [완료] 무인화 포털 엔진 1사이클이 성공적으로 종료되었습니다.")
        return results
