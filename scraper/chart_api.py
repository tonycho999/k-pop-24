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
            # 영화는 KOBIS 공식 데이터 수집 후 제미나이로 번역/가공
            raw_context = self._get_kobis_data()
            if not raw_context:
                print(f"⚠️ [Skip] No KOBIS data found for k-movie.", flush=True)
                return json.dumps({"top10": []})
            return self._process_with_gemini(category, context=raw_context, source_type="kobis", use_search=False)
        else:
            # 영화 외 나머지는 제미나이가 '직접' 구글 검색하도록 위임
            return self._process_with_gemini(category, context=None, source_type="gemini_search", use_search=True)

    def _get_kobis_data(self):
        """KOBIS 박스오피스 API (영화 데이터 전용)"""
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
        """제미나이를 이용한 데이터 수집 및 파싱"""
        if not self.model:
            return json.dumps({"top10": []})

        today = datetime.now().strftime('%Y-%m-%d')
        
        if use_search:
            # 제미나이가 정확히 구글 검색을 하도록 명확한 키워드 제공
            search_query = {
                "k-pop": "최신 한국 멜론 차트 TOP 10 순위",
                "k-drama": "최신 한국 인기 드라마 시청률 순위",
                "k-entertain": "최신 한국 예능 프로그램 화제성 순위",
                "k-culture": "최신 서울 성수동 한남동 핫플레이스 유행 트렌드"
            }.get(category, f"한국 {category} 최신 인기 트렌드")

            prompt = f"""
            Today is {today}.
            Task: Using Google Search, find the latest Top 10 ranking for: "{search_query}".
            
            Rules:
            1. You MUST use Google Search to get the most up-to-date and accurate information.
            2. Extract exactly the Top 10 items based on your search results.
            3. Translate all Korean titles and descriptions naturally into English.
            4. 'info' should be a concise 1-sentence English description.
            5. Output STRICTLY as a JSON object without any markdown blocks (` ```json `).
            
            Required Format:
            {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief description" }} ] }}
            """
            # 제미나이의 자체 구글 검색 기능 활성화 플래그
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
            4. Output STRICTLY as a JSON object without any markdown blocks (` ```json `).
            
            Required Format:
            {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief description" }} ] }}
            """
            tools = None

        try:
            print(f"  > Sending request to Gemini (Google Search Mode: {use_search})...", flush=True)
            
            # 구글 검색(Grounding)과 JSON 모드를 동시에 쓸 때 발생하는 충돌 방지를 위해,
            # 포맷팅은 프롬프트로 강제하고 Python에서 마크다운 찌꺼기를 지우는 방식을 사용합니다.
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
