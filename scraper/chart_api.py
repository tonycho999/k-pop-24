import os
import json
import requests
import time
import random
from datetime import datetime, timedelta
from groq import Groq

class ChartEngine:
    def __init__(self):
        self.groq_client = None
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

    def set_groq_client(self, api_key):
        self.groq_client = Groq(api_key=api_key)

    def get_top10_chart(self, category):
        """카테고리별 데이터 수집 실행 (실패 시 1회 재시도 포함)"""
        max_retries = 1
        
        for attempt in range(max_retries + 1):
            try:
                # 1. AI 작업 전후 랜덤 대기 (4~5초)
                wait_time = random.uniform(4.0, 5.0)
                print(f"⏳ Waiting {wait_time:.2f}s before processing {category}...")
                time.sleep(wait_time)

                # 2. 데이터 소스 분기
                if category == "k-movie":
                    result = self._get_kobis_movie()
                else:
                    # 카테고리별 검색어 최적화
                    queries = {
                        "k-pop": "실시간 음원 차트 순위 써클차트 멜론",
                        "k-drama": "주간 드라마 시청률 순위 닐슨코리아",
                        "k-entertain": "예능 시청률 순위 닐슨코리아"
                    }
                    result = self._get_chart_via_news(category, queries.get(category, category))

                # 3. 결과 검증 (데이터가 비어있는지 확인)
                data = json.loads(result).get("top10", [])
                if not data and category != "k-movie":
                    raise ValueError(f"Empty data extracted for {category}")
                
                return result

            except Exception as e:
                if attempt < max_retries:
                    print(f"⚠️ [Attempt {attempt+1}] Error in {category}: {e}. Retrying after break...")
                    time.sleep(5) # 재시도 전 추가 대기
                else:
                    print(f"❌ [Final Failure] {category} skipped: {e}")
                    return json.dumps({"top10": []})

    def _get_kobis_movie(self):
        """영화진흥위원회 API"""
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={target_date}"
        res = requests.get(url, timeout=10)
        data = res.json().get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
        top10 = [{"rank": i+1, "title": m['movieNm'], "info": f"관객 {m['audiCnt']}"} for i, m in enumerate(data[:10])]
        return json.dumps({"top10": top10}, ensure_ascii=False)

    def _get_chart_via_news(self, category, query):
        """네이버 뉴스 검색 데이터 기반 AI 추출"""
        client_id = os.environ.get("NAVER_CLIENT_ID")
        client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=15&sort=sim"
        
        headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        res = requests.get(url, headers=headers, timeout=10)
        items = res.json().get('items', [])
        
        if not items:
            return json.dumps({"top10": []})
            
        context = " ".join([f"{i['title']} {i['description']}" for i in items])
        return self._ai_extract_chart(category, context)

    def _ai_extract_chart(self, category, context):
        """Groq AI를 통한 정밀 추출"""
        if not self.groq_client: return json.dumps({"top10": []})

        prompt = f"""
        당신은 한국 대중문화 데이터 전문가입니다. 아래 뉴스 텍스트를 분석하여 {category}의 최신 Top 10 순위표를 작성하세요.
        - 정보가 부족하다면 텍스트에서 가장 비중 있게 다뤄진 순서대로 나열하세요.
        - 반드시 다음 JSON 형식만 응답하세요:
        {{"top10": [{{"rank": 1, "title": "제목", "info": "수치/정보"}}, ...]}}
        
        텍스트: {context[:3500]}
        """
        chat = self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192", # 더 정교한 분석을 위해 70B 모델 사용
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return chat.choices[0].message.content
