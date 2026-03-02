import os
import json
import requests
from datetime import datetime, timedelta
from tavily import TavilyClient
from groq import Groq

class ChartEngine:
    def __init__(self):
        # 1. Tavily
        tavily_key = os.environ.get("TAVILY_API_KEY")
        self.tavily = TavilyClient(api_key=tavily_key) if tavily_key else None
        
        # 2. Groq
        groq_key = os.environ.get("GROQ_API_KEY1")
        self.groq = Groq(api_key=groq_key) if groq_key else None
        
        # 3. KOBIS
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

    def get_top10_chart(self, category):
        print(f"📊 Processing {category}...")

        # [분기 처리]
        if category == "k-movie":
            print(f"🎬 Fetching Official KOBIS Box Office Data...")
            raw_context = self._get_kobis_data()
            source_type = "kobis"
        else:
            print(f"🔎 Fetching Tavily Search Data...")
            raw_context = self._search_tavily(category)
            source_type = "search"

        if not raw_context:
            print(f"⚠️ No raw context found for {category}")
            return json.dumps({"top10": []})

        return self._process_with_groq(category, raw_context, source_type)

    def _get_kobis_data(self):
        if not self.kobis_key: return None
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"[http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key=](http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key=){self.kobis_key}&targetDt={yesterday}"
        try:
            res = requests.get(url, timeout=5)
            data = res.json()
            box_office_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
            if not box_office_list: return None
            context = "OFFICIAL KOREAN BOX OFFICE DATA:\n"
            for movie in box_office_list:
                context += f"- Rank {movie['rank']}: {movie['movieNm']} (Audiences: {movie['audiCnt']})\n"
            return context
        except: return None

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
            response = self.tavily.search(query=query, topic="news", days=2, max_results=5)
            context = ""
            for result in response.get('results', []):
                context += f"- Title: {result['title']}\n  Content: {result['content']}\n\n"
            return context if context else None
        except: return None

    def _process_with_groq(self, category, context, source_type):
        today = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""
        Current Date: {today}
        Task: Create a Top 10 ranking for '{category}'.
        Source: {source_type}.
        Data: {context}
        
        Rules:
        1. Extract Top 10.
        2. Translate to English.
        3. Output strictly JSON.
        
        Format: {{ "top10": [ {{ "rank": 1, "title": "...", "info": "..." }} ] }}
        """

        try:
            chat = self.groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}, # JSON 모드 강제
                temperature=0.1
            )
            
            # 1. 안전하게 콘텐츠 추출
            content = chat.choices.message.content
            
            # 2. [핵심] 마크다운 코드 블록 제거 (JSON 에러 주범 해결)
            content = content.replace("```json", "").replace("```", "").strip()
            
            return content
                
        except Exception as e:
            print(f"❌ Groq Error: {e}")
            return json.dumps({"top10": []})
