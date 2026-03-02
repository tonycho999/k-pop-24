import os
import json
import requests
from datetime import datetime, timedelta
from tavily import TavilyClient
from groq import Groq

class ChartEngine:
    def __init__(self):
        # 1. Tavily (검색용)
        tavily_key = os.environ.get("TAVILY_API_KEY")
        if not tavily_key:
            print("⚠️ Warning: TAVILY_API_KEY is missing.")
        self.tavily = TavilyClient(api_key=tavily_key)
        
        # 2. Groq (요약 및 번역용) - 테스트용으로 1번 키 고정
        groq_key = os.environ.get("GROQ_API_KEY1")
        if not groq_key:
             print("⚠️ Warning: GROQ_API_KEY1 is missing.")
        self.groq = Groq(api_key=groq_key)
        
        # 3. KOBIS (영화용)
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

    def get_top10_chart(self, category):
        print(f"📊 Processing {category}...")

        # [분기 처리] 영화는 KOBIS API, 나머지는 Tavily 검색
        if category == "k-movie":
            print(f"🎬 Fetching Official KOBIS Box Office Data...")
            raw_context = self._get_kobis_data()
            source_type = "kobis"
        else:
            print(f"🔎 Fetching Tavily Search Data...")
            raw_context = self._search_tavily(category)
            source_type = "search"

        # 데이터가 없으면 빈 리스트 반환
        if not raw_context:
            print(f"⚠️ No raw context found for {category}")
            return json.dumps({"top10": []})

        # Groq에게 데이터 정제 및 JSON 변환 요청
        return self._process_with_groq(category, raw_context, source_type)

    def _get_kobis_data(self):
        """영진위 API에서 어제 날짜 박스오피스 가져오기"""
        if not self.kobis_key:
            print("❌ KOBIS Key missing")
            return None

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={yesterday}"
        
        try:
            res = requests.get(url, timeout=5)
            data = res.json()
            box_office_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
            
            if not box_office_list:
                return None

            # AI가 읽기 편한 텍스트로 변환
            context = "OFFICIAL KOREAN BOX OFFICE DATA (YESTERDAY):\n"
            for movie in box_office_list:
                context += f"- Rank {movie['rank']}: {movie['movieNm']} (Audiences: {movie['audiCnt']})\n"
            
            return context
        except Exception as e:
            print(f"❌ KOBIS API Error: {e}")
            return None

    def _search_tavily(self, category):
        """Tavily로 최신 뉴스 검색 (2026년 데이터 강제)"""
        queries = {
            "k-pop": "Melon Chart Top 10 ranking today 2026",
            "k-drama": "Nielsen Korea Drama ratings ranking yesterday 2026",
            "k-entertain": "Nielsen Korea Variety Show ratings ranking yesterday 2026",
            "k-culture": "Seoul Seongsu-dong Hannam-dong hot places pop-up store trends 2026"
        }
        query = queries.get(category, f"South Korea {category} trends 2026")
        
        try:
            response = self.tavily.search(
                query=query,
                topic="news",
                days=2, # 최신 2일만 검색
                max_results=5
            )
            
            context = ""
            for result in response.get('results', []):
                context += f"- Title: {result['title']}\n  Content: {result['content']}\n\n"
            
            if not context:
                return None
                
            return context
        except Exception as e:
            print(f"❌ Tavily Search Error: {e}")
            return None

    def _process_with_groq(self, category, context, source_type):
        """Groq(Llama3)를 사용해 JSON 변환"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        prompt = f"""
        Current Date: {today}
        Task: Create a Top 10 ranking for '{category}'.
        Source Type: {source_type} (If 'kobis', rely 100% on the data provided).
        
        [Data Source]
        {context}
        
        [Instructions]
        1. Extract the Top 10 items.
        2. Translate titles to English.
        3. Return JSON object ONLY.
        
        Format: {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief info" }}, ... ] }}
        """

        try:
            # Groq 호출
            chat = self.groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # [🔥 중요 수정] 리스트 인덱스 명시
            return chat.choices.message.content
                
        except Exception as e:
            print(f"❌ Groq Generation Error: {e}")
            return json.dumps({"top10": []})
