import os
import json
import requests
from datetime import datetime, timedelta
import google.generativeai as genai

class ChartEngine:
    def __init__(self):
        # 1. Groq 키 로드 (향후 번역용으로 보존)
        self.groq_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key:
                self.groq_keys.append(key)
        
        if self.groq_keys:
            print(f"✅ Loaded {len(self.groq_keys)} Groq API Keys (Reserved for future use).", flush=True)

        # 2. KOBIS (영화 전용 데이터)
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

        # 3. Gemini 초기화 (메인 검색/분석 AI)
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            print("✅ Gemini API Initialized.", flush=True)
        else:
            print("❌ CRITICAL: GEMINI_API_KEY is missing!", flush=True)
            self.model = None

    def get_top10_chart(self, category):
        print(f"\n📊 --- Processing {category} ---", flush=True)

        if category == "k-movie":
            # 영화는 KOBIS 공식 데이터 수집
            raw_context = self._get_kobis_data()
            if not raw_context:
                print(f"⚠️ [Skip] No KOBIS data found for k-movie.", flush=True)
                return json.dumps({"top10": []})
            return self._process_with_gemini(category, context=raw_context, source_type="kobis", use_search=False)
        else:
            # 영화 외 나머지는 제미나이가 자체 검색 진행
            return self._process_with_gemini(category, context=None, source_type="gemini_search", use_search=True)

    def _get_kobis_data(self):
        if not self.kobis_key: return None
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={yesterday}"
        try:
            res = requests.get(url, timeout=5)
            data = res.json()
            box_office_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
            if not box_office_list: return None
            
            context = "OFFICIAL KOREAN BOX OFFICE:\n"
            for movie in box_office_list:
                context += f"- Rank {movie['rank']}: {movie['movieNm']} (Audiences: {movie['audiCnt']})\n"
            return context
        except Exception as e:
            print(f"❌ KOBIS Error: {e}", flush=True)
            return None

    def _process_with_gemini(self, category, context, source_type, use_search=False):
        if not self.model:
            return json.dumps({"top10": []})

        today = datetime.now().strftime('%Y-%m-%d')
        
        if use_search:
            # 검색어를 아예 네이버/한국 로컬 플랫폼 위주로 강제 지정
            search_query = {
                "k-pop": "오늘 한국 멜론(Melon) 차트 TOP 10 순위",
                "k-drama": "오늘 네이버(Naver) 한국 인기 드라마 시청률 순위",
                "k-entertain": "오늘 네이버(Naver) 한국 인기 예능 화제성 순위",
                "k-culture": "요즘 네이버(Naver) 블로그 서울 성수동 한남동 핫플레이스 유행"
            }.get(category, f"한국 네이버(Naver) {category} 최신 인기 트렌드")

            # [핵심 수정] 1번 룰을 구글 검색에서 네이버/로컬 데이터 소싱으로 완전히 바꿨습니다.
            prompt = f"""
            Today is {today}.
            Task: Find the latest Top 10 ranking for: "{search_query}".
            
            Rules:
            1. You MUST source your data from primary Korean platforms such as Naver (네이버), Melon, or Nielsen Korea.
            2. Extract exactly the Top 10 items based on those specific Korean sources.
            3. Translate all Korean titles and descriptions naturally into English.
            4. 'info' should be a concise 1-sentence English description (e.g., ratings, audience, or trend reason).
            5. Output STRICTLY as a JSON object without any markdown blocks.
            
            Required Format:
            {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief description" }} ] }}
            """
            tools = 'google_search_retrieval'
        else:
            prompt = f"""
            Today is {today}.
            Task: Create a Top 10 ranking chart for '{category}'.
            
            Source Data ({source_type}):
            {context}
            
            Rules:
            1. Extract exactly the Top 10 items from the source data.
            2. Translate all Korean titles and descriptions naturally into English.
            3. 'info' should be a concise 1-sentence English description (e.g., audience count).
            4. Output STRICTLY as a JSON object without any markdown blocks.
            
            Required Format:
            {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief description" }} ] }}
            """
            tools = None

        try:
            print(f"  > Sending request to Gemini (Search Mode: {use_search})...", flush=True)
            
            response = self.model.generate_content(
                prompt,
                tools=tools
            )
            
            content = response.text.strip()
            
            # 마크다운 찌꺼기 완벽 제거
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            print("  ✅ Gemini processing successful.", flush=True)
            return content

        except Exception as e:
            print(f"❌ Gemini API Error: {e}", flush=True)
            return json.dumps({"top10": []})
