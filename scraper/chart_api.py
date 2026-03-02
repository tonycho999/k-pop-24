import os
import json
import random
import time
import requests
from datetime import datetime, timedelta
from tavily import TavilyClient
from groq import Groq

class ChartEngine:
    def __init__(self):
        # 1. Tavily
        tavily_key = os.environ.get("TAVILY_API_KEY")
        self.tavily = TavilyClient(api_key=tavily_key) if tavily_key else None
        
        # 2. Groq 키 로드 (8개)
        self.groq_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key:
                self.groq_keys.append(key)
        
        # 키를 무작위로 섞어서 사용 순서 결정 (매번 다른 순서로 시작)
        if self.groq_keys:
            random.shuffle(self.groq_keys)
            print(f"✅ Loaded {len(self.groq_keys)} Groq API Keys.", flush=True)
        else:
            print("❌ CRITICAL: No GROQ_API_KEYs found!", flush=True)

        # 3. KOBIS
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

    def get_top10_chart(self, category):
        print(f"\n📊 --- Processing {category} ---", flush=True)

        # 1. 데이터 수집
        if category == "k-movie":
            raw_context = self._get_kobis_data()
            source_type = "kobis"
        else:
            raw_context = self._search_tavily(category)
            source_type = "search"

        if not raw_context:
            print(f"⚠️ [Skip] No data found for {category}.", flush=True)
            return json.dumps({"top10": []})

        # 2. Groq 처리 (재시도 로직 포함)
        return self._process_with_retry(category, raw_context, source_type)

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

    def _process_with_retry(self, category, context, source_type):
        """
        키가 막히면(429) 다음 키로 넘어가며 시도합니다.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""
        Current Date: {today}
        Task: Create a Top 10 ranking for '{category}'.
        Source: {source_type}.
        Data: {context}
        Format: {{ "top10": [ {{ "rank": 1, "title": "...", "info": "..." }} ] }}
        Output strictly JSON.
        """

        # 등록된 키 개수만큼 시도
        for i, key in enumerate(self.groq_keys):
            try:
                # 클라이언트 생성 (현재 순번의 키 사용)
                client = Groq(api_key=key)
                
                print(f"  > Attempt {i+1}/{len(self.groq_keys)} with Key ending in ...{key[-4:]}", flush=True)
                
                completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"},
                    temperature=0.1
                )

                # [성공 시 파싱] 
                # 로그 확인 결과: completion은 객체, choices는 리스트, choices는 객체입니다.
                # 따라서 아래 코드가 정답입니다.
                content = completion.choices.message.content
                
                # 마크다운 제거
                content = content.replace("```json", "").replace("```", "").strip()
                
                print("  ✅ Groq Success!", flush=True)
                return content

            except Exception as e:
                # 429 에러(Rate Limit)인 경우만 다음 키 시도
                error_msg = str(e)
                if "429" in error_msg or "Rate limit" in error_msg:
                    print(f"  ⚠️ Rate Limit reached for this key. Switching...", flush=True)
                    continue # 다음 키로 loop
                else:
                    # 그 외 치명적 에러는 즉시 중단
                    print(f"❌ Groq Fatal Error: {e}", flush=True)
                    return json.dumps({"top10": []})

        # 모든 키를 다 써도 안 되면
        print("❌ All Groq keys exhausted.", flush=True)
        return json.dumps({"top10": []})
