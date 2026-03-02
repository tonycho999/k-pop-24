import os
import json
from datetime import datetime
from tavily import TavilyClient
from groq import Groq

class ChartEngine:
    def __init__(self):
        # 1. Tavily (검색 담당)
        self.tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
        
        # 2. Groq (요약 담당) - 테스트용으로 1번 키만 사용
        self.groq = Groq(api_key=os.environ.get("GROQ_API_KEY1"))

    def get_top10_chart(self, category):
        print(f"🔎 [Tavily] Searching latest trends for {category}...")
        
        # 1단계: 최신 뉴스 검색 (2026년 데이터 확보)
        search_result_text = self._search_tavily(category)
        
        if not search_result_text:
            return json.dumps({"top10": []})

        # 2단계: Groq에게 JSON 변환 요청
        return self._process_with_groq(category, search_result_text)

    def _search_tavily(self, category):
        """
        Tavily API를 사용해 '최근 2일' 뉴스만 검색
        """
        # 검색어 전략 (2026년 현재 시점 반영)
        queries = {
            "k-pop": "Melon Chart Top 10 ranking today 2026",
            "k-drama": "Nielsen Korea Drama ratings ranking yesterday 2026",
            "k-entertain": "Nielsen Korea Variety Show ratings ranking yesterday 2026",
            "k-movie": "KOBIS Box Office ranking yesterday 2026",
            "k-culture": "Seoul Seongsu-dong Hannam-dong hot places pop-up store trends 2026"
        }
        
        query = queries.get(category, f"South Korea {category} trends 2026")
        
        try:
            # topic="news": 뉴스 기사만 검색
            # days=2: 오늘~어제 데이터만 가져옴 (과거 데이터 차단 핵심!)
            response = self.tavily.search(
                query=query,
                search_depth="basic",
                topic="news",
                days=2, 
                max_results=5
            )
            
            # AI가 읽기 좋게 텍스트로 합치기
            context = ""
            for result in response.get('results', []):
                context += f"- Title: {result['title']}\n  Content: {result['content']}\n\n"
            
            return context
            
        except Exception as e:
            print(f"❌ Tavily Search Error: {e}")
            return None

    def _process_with_groq(self, category, context):
        """
        수집된 텍스트를 분석하여 Top 10 JSON 생성
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        prompt = f"""
        Current Date: {today}
        Task: Create a Top 10 ranking for '{category}' based ONLY on the provided search results.
        
        [Search Results]
        {context}
        
        [Instructions]
        1. Extract the ranking directly from the search results.
        2. Translate titles and descriptions to English.
        3. K-Culture Rule: Exclude celebrities. Focus on places (Seongsu, Hannam) or food.
        4. Return JSON object ONLY.
        
        Format: {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief info" }}, ... ] }}
        """

        try:
            chat = self.groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile", # 성능 좋은 모델
                response_format={"type": "json_object"},
                temperature=0.1
            )
            return chat.choices.message.content
        except Exception as e:
            print(f"❌ Groq Generation Error: {e}")
            return json.dumps({"top10": []})
