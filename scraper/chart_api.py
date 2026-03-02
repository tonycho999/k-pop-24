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

    def _extract_safe_content(self, response):
        """
        [만능 파서] Groq 응답이 객체, 딕셔너리, 리스트 중 무엇으로 오든 content를 추출합니다.
        """
        try:
            # Type 1: 표준 객체 (Object) 접근 방식
            # response.choices.message.content
            if hasattr(response, 'choices'):
                choices = response.choices
                if isinstance(choices, list) and len(choices) > 0:
                    first = choices
                    if hasattr(first, 'message'):
                        return first.message.content
            
            # Type 2: 딕셔너리 (Dict) 접근 방식
            # response['choices']['message']['content']
            if isinstance(response, dict):
                choices = response.get('choices', [])
                if isinstance(choices, list) and len(choices) > 0:
                    first = choices
                    if isinstance(first, dict):
                        message = first.get('message', {})
                        return message.get('content', '')
            
            # Type 3: 리스트 (List) 직접 반환 케이스 (드물지만 대비)
            if isinstance(response, list) and len(response) > 0:
                # 리스트의 첫 번째가 객체인 경우
                if hasattr(response, 'message'):
                    return response.message.content
                # 리스트의 첫 번째가 딕셔너리인 경우
                if isinstance(response, dict):
                    return response.get('message', {}).get('content', '')

            # 여기까지 왔다면 알 수 없는 구조임 -> 디버깅용으로 원본 출력 시도
            print(f"⚠️ Unknown response structure. Type: {type(response)}")
            return str(response)

        except Exception as e:
            print(f"⚠️ Parsing Logic Error: {e}")
            return ""

    def get_top10_chart(self, category):
        print(f"📊 Processing {category}...")

        # [데이터 수집 분기]
        if category == "k-movie":
            print(f"🎬 Fetching KOBIS Data...")
            raw_context = self._get_kobis_data()
            source_type = "kobis"
        else:
            print(f"🔎 Fetching Tavily Data...")
            raw_context = self._search_tavily(category)
            source_type = "search"

        # 데이터가 아예 없으면 조기 종료
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
            
            # [핵심] 만능 파서로 내용 추출 (여기서 에러가 나면 로그에 타입이 찍힘)
            content = self._extract_safe_content(chat_completion)
            
            if not content:
                print(f"⚠️ Extracted content is empty for {category}")
                return json.dumps({"top10": []})

            # 마크다운 제거 (JSON 파싱 에러 방지)
            content = content.replace("```json", "").replace("```", "").strip()
            return content
                
        except Exception as e:
            # 여기서도 에러가 나면 진짜 시스템 문제임
            print(f"❌ Groq API Call Error: {e}")
            return json.dumps({"top10": []})
