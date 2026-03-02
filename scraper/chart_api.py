import os
import json
import random
import requests
from datetime import datetime, timedelta
from tavily import TavilyClient
from groq import Groq

class ChartEngine:
    def __init__(self):
        # 1. Tavily 초기화 확인
        tavily_key = os.environ.get("TAVILY_API_KEY")
        if tavily_key:
            print(f"✅ Tavily Key Loaded: {tavily_key[:5]}...", flush=True)
            self.tavily = TavilyClient(api_key=tavily_key)
        else:
            print("❌ CRITICAL: TAVILY_API_KEY is missing!", flush=True)
            self.tavily = None
        
        # 2. Groq 키 8개 로드 확인
        self.groq_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key:
                self.groq_keys.append(key)
        
        if self.groq_keys:
            print(f"✅ Loaded {len(self.groq_keys)} Groq API Keys.", flush=True)
        else:
            print("❌ CRITICAL: No GROQ_API_KEYs found in env!", flush=True)

        # 3. KOBIS 초기화 확인
        self.kobis_key = os.environ.get("KOBIS_API_KEY")
        if self.kobis_key:
            print(f"✅ Kobis Key Loaded.", flush=True)
        else:
            print("⚠️ Kobis Key missing.", flush=True)

    def _get_random_groq_client(self):
        if not self.groq_keys:
            print("❌ Error: No Groq keys available to create client.", flush=True)
            return None
        selected_key = random.choice(self.groq_keys)
        return Groq(api_key=selected_key)

    def get_top10_chart(self, category):
        print(f"\n📊 --- Processing {category} ---", flush=True)

        # 1. 데이터 수집 단계
        if category == "k-movie":
            raw_context = self._get_kobis_data()
            source_type = "kobis"
        else:
            raw_context = self._search_tavily(category)
            source_type = "search"

        # 수집 결과 확인
        if not raw_context:
            print(f"⚠️ [Stop] No raw data found for {category}. Skipping Groq.", flush=True)
            return json.dumps({"top10": []})
        
        print(f"✅ Raw Data Length: {len(raw_context)} characters.", flush=True)

        # 2. AI 처리 단계
        return self._process_with_groq(category, raw_context, source_type)

    def _get_kobis_data(self):
        if not self.kobis_key: return None
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={yesterday}"
        try:
            print("  > Requesting KOBIS API...", flush=True)
            res = requests.get(url, timeout=5)
            data = res.json()
            box_office_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
            if not box_office_list:
                print("  > KOBIS returned empty list.", flush=True)
                return None
            
            context = "OFFICIAL KOREAN BOX OFFICE:\n"
            for movie in box_office_list:
                context += f"- Rank {movie['rank']}: {movie['movieNm']} (Audiences: {movie['audiCnt']})\n"
            return context
        except Exception as e:
            print(f"❌ KOBIS API Error: {e}", flush=True)
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
            print(f"  > Searching Tavily: '{query}'", flush=True)
            response = self.tavily.search(query=query, topic="news", days=2, max_results=5)
            
            results = response.get('results', [])
            print(f"  > Tavily found {len(results)} articles.", flush=True)
            
            context = ""
            for result in results:
                context += f"- Title: {result['title']}\n  Content: {result['content']}\n\n"
            
            return context if context else None
        except Exception as e:
            print(f"❌ Tavily API Error: {e}", flush=True)
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
        Output strictly JSON only. No markdown.
        """

        try:
            print("  > Sending request to Groq LLM...", flush=True)
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # [디버깅] Groq 응답 원본 확인
            print(f"  > Groq Response Type: {type(completion)}", flush=True)

            # [만능 파싱 로직]
            # 1. 딕셔너리 변환 시도
            if hasattr(completion, 'model_dump'):
                data = completion.model_dump()
            elif hasattr(completion, 'to_dict'):
                data = completion.to_dict()
            elif hasattr(completion, 'dict'):
                data = completion.dict()
            else:
                data = completion # 변환 불가 시 그대로

            # 2. 데이터 추출
            # 딕셔너리면 ['choices'], 객체면 .choices 시도
            if isinstance(data, dict):
                choices = data.get('choices', [])
                if choices:
                    content = choices['message']['content']
                else:
                    print(f"❌ Groq Response has no choices: {data}", flush=True)
                    return json.dumps({"top10": []})
            else:
                # 객체 직접 접근 (최후의 수단)
                content = completion.choices.message.content

            # 3. 결과 반환
            print("  > Groq content received. Cleaning...", flush=True)
            content = content.replace("```json", "").replace("```", "").strip()
            return content

        except Exception as e:
            print(f"❌ Groq Processing Error: {e}", flush=True)
            # 에러 발생 시 원본 데이터가 무엇이었는지 출력 (매우 중요)
            try:
                print(f"   (Debug) Raw completion object: {completion}", flush=True)
            except: pass
            return json.dumps({"top10": []})
