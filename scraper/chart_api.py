import os
import json
import random
import requests
from datetime import datetime, timedelta
from tavily import TavilyClient
from groq import Groq

class ChartEngine:
    def __init__(self):
        # 1. Tavily
        tavily_key = os.environ.get("TAVILY_API_KEY")
        self.tavily = TavilyClient(api_key=tavily_key) if tavily_key else None
        
        # 2. Groq 키 8개 로드 (Rate Limit 방지용)
        self.groq_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key:
                self.groq_keys.append(key)
        
        if not self.groq_keys:
            print("⚠️ Warning: No GROQ_API_KEYS found.")

        # 3. KOBIS
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

    def _get_random_groq_client(self):
        """키 8개 중 하나를 랜덤으로 뽑아 클라이언트를 생성"""
        if not self.groq_keys:
            return None
        selected_key = random.choice(self.groq_keys)
        return Groq(api_key=selected_key)

    def _safe_get(self, obj, key):
        """
        [만능 추출기] 객체면 .attr로, 딕셔너리면 ['key']로 값을 꺼냄
        """
        try:
            # 1. 딕셔너리인 경우
            if isinstance(obj, dict):
                return obj.get(key)
            # 2. 객체인 경우
            if hasattr(obj, key):
                return getattr(obj, key)
            return None
        except:
            return None

    def get_top10_chart(self, category):
        print(f"📊 Processing {category}...", flush=True)

        if category == "k-movie":
            print(f"🎬 Fetching KOBIS Data...", flush=True)
            raw_context = self._get_kobis_data()
            source_type = "kobis"
        else:
            print(f"🔎 Fetching Tavily Data...", flush=True)
            raw_context = self._search_tavily(category)
            source_type = "search"

        if not raw_context:
            print(f"⚠️ No raw data found for {category}", flush=True)
            return json.dumps({"top10": []})

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
            print(f"❌ KOBIS Error: {e}", flush=True)
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
            response = self.tavily.search(query=query, topic="news", days=2, max_results=5)
            context = ""
            for result in response.get('results', []):
                context += f"- Title: {result['title']}\n  Content: {result['content']}\n\n"
            return context if context else None
        except Exception as e:
            print(f"❌ Tavily Error: {e}", flush=True)
            return None

    def _process_with_groq(self, category, context, source_type):
        client = self._get_random_groq_client()
        if not client:
            return json.dumps({"top10": []})

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
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.1
            )

            # ------------------------------------------------------------------
            # [최종 수정] 만능 추출기 사용 (객체/딕셔너리 자동 감지)
            # ------------------------------------------------------------------
            
            # 1. choices 가져오기
            choices = self._safe_get(completion, 'choices')
            
            # choices가 리스트인지 확인
            if not choices or not isinstance(choices, list):
                # 가끔 choices가 없는 경우 대비
                print(f"⚠️ Invalid Groq response structure: {completion}")
                return json.dumps({"top10": []})

            # 2. 첫 번째 choice 가져오기
            first_choice = choices

            # 3. message 가져오기
            message = self._safe_get(first_choice, 'message')
            if not message:
                return json.dumps({"top10": []})

            # 4. content 가져오기
            content = self._safe_get(message, 'content')
            if not content:
                return json.dumps({"top10": []})

            # 마크다운 제거
            content = content.replace("```json", "").replace("```", "").strip()
            return content

        except Exception as e:
            print(f"❌ Groq API Error: {e}", flush=True)
            return json.dumps({"top10": []})
