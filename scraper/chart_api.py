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
        
        # 2. Groq (요약 및 번역용)
        groq_key = os.environ.get("GROQ_API_KEY1")
        if not groq_key:
             print("⚠️ Warning: GROQ_API_KEY1 is missing.")
        self.groq = Groq(api_key=groq_key)
        
        # 3. KOBIS (영화용)
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

    def _extract_content(self, completion):
        """
        [안전 파싱 함수] 제공해주신 참고 코드 기반 수정
        Groq 응답이 객체든 딕셔너리든 안전하게 content만 추출
        """
        try:
            # 1. response에서 choices 리스트 가져오기
            if hasattr(completion, 'choices'):
                choices = completion.choices
            elif isinstance(completion, dict):
                choices = completion.get('choices', [])
            else:
                return ""

            # 2. 리스트가 비어있지 않은지 확인
            if isinstance(choices, list) and len(choices) > 0:
                first_choice = choices # [핵심] 리스트의 첫 번째 요소 선택
                
                # Case A: 객체 형태 (first_choice.message.content)
                if hasattr(first_choice, 'message'):
                    return str(first_choice.message.content)
                
                # Case B: 딕셔너리 형태 (first_choice['message']['content'])
                if isinstance(first_choice, dict):
                    message = first_choice.get('message', {})
                    if isinstance(message, dict):
                        return str(message.get('content', ''))
                    return str(message)
            
            return ""

        except Exception as e:
            print(f"⚠️ Groq Parsing Error: {e}")
            return ""

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

        if not raw_context:
            print(f"⚠️ No raw context found for {category}")
            return json.dumps({"top10": []})

        # Groq에게 데이터 정제 및 JSON 변환 요청
        return self._process_with_groq(category, raw_context, source_type)

    def _get_kobis_data(self):
        """영진위 API에서 어제 날짜 박스오피스 가져오기"""
        if not self.kobis_key:
            return None

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={yesterday}"
        
        try:
            res = requests.get(url, timeout=5)
            data = res.json()
            box_office_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
            
            if not box_office_list:
                return None

            context = "OFFICIAL KOREAN BOX OFFICE DATA (YESTERDAY):\n"
            for movie in box_office_list:
                context += f"- Rank {movie['rank']}: {movie['movieNm']} (Audiences: {movie['audiCnt']})\n"
            
            return context
        except Exception as e:
            print(f"❌ KOBIS API Error: {e}")
            return None

    def _search_tavily(self, category):
        """Tavily로 최신 뉴스 검색"""
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
                days=2,
                max_results=5
            )
            
            context = ""
            for result in response.get('results', []):
                context += f"- Title: {result['title']}\n  Content: {result['content']}\n\n"
            
            return context if context else None
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
            
            # [수정됨] 안전 파싱 함수 사용
            return self._extract_content(chat)
                
        except Exception as e:
            print(f"❌ Groq Generation Error: {e}")
            return json.dumps({"top10": []})
