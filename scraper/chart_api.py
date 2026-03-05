import os
import json
import requests
from datetime import datetime, timedelta
import google.generativeai as genai

# 모델 매니저 호출 (AI 모델 동적 할당용)
from model_manager import ModelManager 

class ChartEngine:
    def __init__(self):
        # 1. Groq 키 보존 (향후 다른 용도로 사용)
        self.groq_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key:
                self.groq_keys.append(key)
        
        if self.groq_keys:
            print(f"✅ Loaded {len(self.groq_keys)} Groq API Keys (Reserved).", flush=True)

        # 2. KOBIS (영화 박스오피스 전용)
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

        # 3. Gemini 초기화 (자체 검색 기능 사용)
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            
            manager = ModelManager(provider="gemini")
            best_model_name = manager.get_best_model()
            
            if best_model_name:
                print(f"✨ ChartEngine received model: {best_model_name}", flush=True)
                self.model = genai.GenerativeModel(best_model_name)
            else:
                print("❌ CRITICAL: ModelManager failed to provide a model.", flush=True)
                self.model = None
        else:
            print("❌ CRITICAL: GEMINI_API_KEY is missing!", flush=True)
            self.model = None

    def get_top10_chart(self, category):
        print(f"\n📊 --- Processing {category} ---", flush=True)

        if category == "k-movie":
            raw_context = self._get_kobis_data()
            if not raw_context:
                print(f"⚠️ [Skip] No KOBIS data found for k-movie.", flush=True)
                return json.dumps({"top10": []})
            return self._process_with_gemini(category, context=raw_context, source_type="kobis", use_search=False)
        else:
            # 영화 외 모든 카테고리는 제미나이가 자체적으로 검색 수행
            return self._process_with_gemini(category, context=None, source_type="gemini_search", use_search=True)

    def _get_kobis_data(self):
        if not self.kobis_key: return None
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={yesterday}"
        try:
            res = requests.get(url, timeout=15)
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
            # 제미나이가 정확히 한국 데이터를 긁어오도록 한국어로 꽉 찬 검색어 지시
            search_query = {
                "k-pop": "오늘 한국 멜론(Melon) 차트 실시간 TOP 10 순위",
                "k-drama": "오늘 닐슨코리아 기준 한국 방영중 드라마 시청률 순위 TOP 10",
                "k-entertain": "오늘 한국 화제성 1위~10위 예능 프로그램 순위",
                "k-culture": "오늘 한국 서울 2030 성수동 한남동 핫플레이스 유행 트렌드 TOP 10"
            }.get(category, f"오늘 한국 {category} 최신 인기 트렌드 TOP 10")

            prompt = f"""
            Today is {today}.
            Task: Use your Google Search tool to find the absolute latest Top 10 ranking for: "{search_query}".
            
            CRITICAL RULES:
            1. You MUST search the Korean web (e.g., Naver, Melon, Nielsen Korea). Do not return US/Global data (like Billboard, US Netflix, or US stocks).
            2. Extract exactly 10 items based on CURRENT real-world data in South Korea.
            3. Translate all Korean titles and descriptions naturally into English.
            4. 'info' should be a concise 1-sentence English description (e.g., ratings, audience, or reason for trending).
            5. Output STRICTLY as a valid JSON object without any markdown formatting.
            
            Required Format:
            {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief description" }} ] }}
            """
            
            # [핵심] 최신 API 규격에 맞춘 올바른 검색 도구 이름 할당
            tools = 'google_search' 
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
            4. Output STRICTLY as a valid JSON object without any markdown formatting.
            
            Required Format:
            {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief description" }} ] }}
            """
            tools = None

        try:
            print(f"  > Sending request to Gemini (Search Mode: {use_search})...", flush=True)
            
            if tools:
                response = self.model.generate_content(prompt, tools=tools)
            else:
                response = self.model.generate_content(prompt)
            
            content = response.text.strip()
            
            # JSON 외의 쓰레기 마크다운 찌꺼기 방어
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            print("  ✅ Gemini processing successful.", flush=True)
            return content

        except Exception as e:
            print(f"❌ Gemini API Error: {e}", flush=True)
            return json.dumps({"top10": []})
