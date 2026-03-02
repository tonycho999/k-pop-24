import os
import json
import requests
from datetime import datetime, timedelta
from tavily import TavilyClient
from groq import Groq

class ChartEngine:
    def __init__(self):
        # 1. Tavily (검색 엔진)
        tavily_key = os.environ.get("TAVILY_API_KEY")
        self.tavily = TavilyClient(api_key=tavily_key) if tavily_key else None
        
        # 2. Groq (AI 엔진)
        groq_key = os.environ.get("GROQ_API_KEY1")
        self.groq = Groq(api_key=groq_key) if groq_key else None
        
        # 3. KOBIS (영화 API)
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

    def get_top10_chart(self, category):
        print(f"📊 Processing {category}...")

        # [데이터 수집]
        if category == "k-movie":
            print(f"🎬 Fetching KOBIS Data...")
            raw_context = self._get_kobis_data()
            source_type = "kobis"
        else:
            print(f"🔎 Fetching Tavily Data...")
            raw_context = self._search_tavily(category)
            source_type = "search"

        # 데이터 없음 처리
        if not raw_context:
            print(f"⚠️ No raw data found for {category}")
            return json.dumps({"top10": []})

        # Groq로 가공
        return self._process_with_groq(category, raw_context, source_type)

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
            print(f"❌ KOBIS Error: {e}")
            return None

    def _search_tavily(self, category):
        if not self.tavily: return None
        queries = {
            "k-pop": "Melon Chart Top 10 ranking today 2026",
            "k-drama": "Nielsen Korea Drama ratings ranking yesterday 2026",
            "k-entertain": "Nielsen Korea Variety Show ratings ranking yesterday 2026",
            "k-culture": "Seoul Seongsu-dong Hannam-dong hot places pop-up store trends 2026"
        }
        query = queries.get(category, f"South Korea {category} trends 2026")
        
        try:
            # days=2로 설정하여 최신 뉴스만 확보
            response = self.tavily.search(query=query, topic="news", days=2, max_results=5)
            context = ""
            for result in response.get('results', []):
                context += f"- Title: {result['title']}\n  Content: {result['content']}\n\n"
            return context if context else None
        except Exception as e:
            print(f"❌ Tavily Error: {e}")
            return None

    def _process_with_groq(self, category, context, source_type):
        today = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""
        Current Date: {today}
        Task: Create a Top 10 ranking for '{category}'.
        Source: {source_type}.
        Data: {context}
        
        Rules:
        1. Extract Top 10.
        2. Translate titles to English.
        3. Output strictly JSON.
        
        Format: {{ "top10": [ {{ "rank": 1, "title": "...", "info": "..." }} ] }}
        """

        try:
            # Groq API 호출
            chat_completion = self.groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # [핵심 수정] 객체 속성 접근 방식 포기 -> 딕셔너리로 변환
            # model_dump()를 사용하면 Pydantic 객체가 순수 dict로 변합니다.
            try:
                if hasattr(chat_completion, 'model_dump'):
                    response_dict = chat_completion.model_dump()
                else:
                    response_dict = chat_completion.dict() # 구버전 호환
            except Exception:
                # 변환 실패 시 속성을 강제로 dict로 취급 시도
                response_dict = chat_completion if isinstance(chat_completion, dict) else {}

            # 이제 무조건 딕셔너리 키 접근 (인덱스 에러 방지)
            choices = response_dict.get('choices', [])
            
            if not choices or not isinstance(choices, list):
                print(f"⚠️ Unexpected Groq Response format: {response_dict}")
                return json.dumps({"top10": []})

            # choices 접근
            first_choice = choices
            message = first_choice.get('message', {})
            content = message.get('content', '')
            
            # 마크다운 제거
            content = content.replace("```json", "").replace("```", "").strip()
            
            return content
                
        except Exception as e:
            print(f"❌ Groq Parsing Error: {e}")
            return json.dumps({"top10": []})
