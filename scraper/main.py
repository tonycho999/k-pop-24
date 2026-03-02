import os
import json
import requests
from datetime import datetime, timedelta
from tavily import TavilyClient
from groq import Groq

class ChartEngine:
    def __init__(self):
        self.tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
        self.groq = Groq(api_key=os.environ.get("GROQ_API_KEY1"))
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

    def _get_kobis_data(self):
        # (기존 코드와 동일, 생략 없이 유지)
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
        except: return None

    def _search_tavily(self, category):
        # (기존 코드와 동일)
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

    def get_top10_chart(self, category):
        print(f"📊 Processing {category}...")
        
        if category == "k-movie":
            raw_context = self._get_kobis_data()
            source_type = "kobis"
        else:
            raw_context = self._search_tavily(category)
            source_type = "search"

        if not raw_context:
            print(f"⚠️ No data for {category}")
            return json.dumps({"top10": []})

        return self._process_with_groq(category, raw_context, source_type)

    def _process_with_groq(self, category, context, source_type):
        today = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""
        Current Date: {today}
        Task: Create a Top 10 ranking for '{category}'.
        Source: {source_type}.
        Data: {context}
        Format: {{ "top10": [ {{ "rank": 1, "title": "...", "info": "..." }} ] }}
        Output strictly JSON.
        """

        try:
            completion = self.groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.1
            )

            # ---------------------------------------------------------
            # [수정된 파싱 로직]
            # 객체 속성 접근(.) 대신 model_dump()로 딕셔너리 변환 후 처리
            # ---------------------------------------------------------
            response_data = None
            
            # 1. 딕셔너리 변환 시도
            if hasattr(completion, 'model_dump'):
                response_data = completion.model_dump()
            elif hasattr(completion, 'to_dict'):
                response_data = completion.to_dict()
            elif hasattr(completion, 'dict'):
                response_data = completion.dict()
            elif isinstance(completion, dict):
                response_data = completion
            else:
                # 변환 실패 시: 직접 속성 접근 시도 (최후의 수단)
                print(f"⚠️ Unknown type: {type(completion)}, trying direct access")
                return completion.choices.message.content

            # 2. 딕셔너리 키로 안전하게 접근 ('list' error 원천 차단)
            choices = response_data.get('choices', [])
            if not choices:
                print("⚠️ Choices list is empty")
                return json.dumps({"top10": []})
            
            # choices 접근
            first_choice = choices
            
            # message 접근
            message = first_choice.get('message', {})
            
            # content 접근
            content = message.get('content', '')

            # 3. 마크다운 제거
            content = content.replace("```json", "").replace("```", "").strip()
            
            return content

        except Exception as e:
            # 4. 구조를 모를 때를 대비한 디버깅 로그
            print(f"❌ Groq Error: {e}")
            # print(f"❌ Raw Response: {completion}") # 필요시 주석 해제하여 구조 확인
            return json.dumps({"top10": []})
