import os
import json
import requests
from datetime import datetime, timedelta
from tavily import TavilyClient
import google.generativeai as genai

# 모델 선택 권한을 가진 매니저 호출
from model_manager import ModelManager 

class ChartEngine:
    def __init__(self):
        # 1. Tavily 검색 엔진 초기화 (최신 한국어 검색 담당)
        tavily_key = os.environ.get("TAVILY_API_KEY")
        self.tavily = TavilyClient(api_key=tavily_key) if tavily_key else None
        if self.tavily:
            print("✅ Tavily Search API Initialized.", flush=True)
        else:
            print("❌ CRITICAL: TAVILY_API_KEY is missing!", flush=True)

        # 2. KOBIS (영화 전용 API)
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

        # 3. Gemini 초기화 (AI 모델 선택은 ModelManager에게 100% 위임)
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            
            # [핵심] 여기서 모델 리스트를 조회하고 최적의 이름을 가져옴
            manager = ModelManager(provider="gemini")
            best_model_name = manager.get_best_model()
            
            if best_model_name:
                print(f"✨ ChartEngine successfully received model: {best_model_name}", flush=True)
                # 받아온 이름 그대로 AI 모델 세팅 (하드코딩 없음)
                self.model = genai.GenerativeModel(best_model_name)
            else:
                print("❌ CRITICAL: ModelManager failed to provide a model.", flush=True)
                self.model = None
        else:
            print("❌ CRITICAL: GEMINI_API_KEY is missing!", flush=True)
            self.model = None

    def get_top10_chart(self, category):
        print(f"\n📊 --- Processing {category} ---", flush=True)

        # [1단계: 데이터 수집]
        if category == "k-movie":
            raw_context = self._get_kobis_data()
            source_type = "Official KOBIS API Data"
        else:
            raw_context = self._search_tavily(category)
            source_type = "Tavily Web Search Results"

        if not raw_context:
            print(f"⚠️ [Skip] No raw data found for {category}.", flush=True)
            return json.dumps({"top10": []})

        print(f"  > Context gathered ({len(raw_context)} chars). Passing to Gemini...", flush=True)

        # [2단계: AI 번역 및 포맷팅]
        return self._process_with_gemini(category, raw_context, source_type)

    def _get_kobis_data(self):
        """KOBIS 박스오피스 데이터 추출"""
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

    def _search_tavily(self, category):
        """Tavily를 활용한 한국어 로컬 트렌드 검색"""
        if not self.tavily: return None
        
        queries = {
            "k-pop": "오늘 한국 멜론(Melon) 차트 TOP 10 순위",
            "k-drama": "오늘 네이버(Naver) 한국 인기 드라마 시청률 순위",
            "k-entertain": "오늘 네이버(Naver) 한국 인기 예능 화제성 순위",
            "k-culture": "요즘 네이버(Naver) 블로그 서울 성수동 한남동 핫플레이스 유행 트렌드"
        }
        query = queries.get(category, f"한국 {category} 최신 인기 트렌드")
        
        try:
            print(f"  > Tavily Searching: '{query}'", flush=True)
            response = self.tavily.search(query=query, topic="news", days=2, max_results=5)
            context = ""
            for result in response.get('results', []):
                context += f"- Title: {result['title']}\n  Content: {result['content']}\n\n"
            return context if context else None
        except Exception as e:
            print(f"❌ Tavily Error: {e}", flush=True)
            return None

    def _process_with_gemini(self, category, context, source_type):
        """Gemini를 활용한 영어 번역 및 JSON 포맷팅"""
        if not self.model:
            return json.dumps({"top10": []})

        today = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""
        Today is {today}.
        Task: Create a Top 10 ranking chart for '{category}'.
        
        Source Data ({source_type}):
        {context}
        
        Rules:
        1. Extract exactly the Top 10 items from the source data provided above.
        2. Translate all Korean titles and descriptions naturally into English.
        3. 'info' should be a concise 1-sentence English description based on the source data.
        4. Output STRICTLY as a JSON object without any markdown blocks (` ```json `).
        
        Required Format:
        {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief description" }} ] }}
        """

        try:
            # 외부 검색 도구 없이 순수 텍스트 처리만 진행 (에러 방지)
            response = self.model.generate_content(prompt)
            content = response.text.strip()
            
            # 마크다운 방어 로직 (JSON 형식만 파싱되도록)
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            print("  ✅ Gemini JSON processing successful.", flush=True)
            return content

        except Exception as e:
            print(f"❌ Gemini API Error: {e}", flush=True)
            return json.dumps({"top10": []})
