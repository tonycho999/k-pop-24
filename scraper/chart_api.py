import os
import json
import requests
from datetime import datetime, timedelta
from groq import Groq

class ChartEngine:
    def __init__(self):
        self.groq_client = None
        self.kobis_key = os.environ.get("KOBIS_API_KEY")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def set_groq_client(self, api_key):
        """main.py에서 결정된 로테이션 키를 주입합니다."""
        self.groq_client = Groq(api_key=api_key)

    def get_top10_chart(self, category):
        """카테고리별 데이터 소스 분기"""
        if category == "k-movie":
            return self._get_kobis_movie()
        elif category == "k-pop":
            # 네이버 뉴스 검색을 통해 '써클차트' 또는 '멜론차트' 관련 최신 기사 텍스트 분석
            return self._get_chart_via_news(category, "가요 순위 써클차트 멜론차트")
        elif category in ["k-drama", "k-entertain"]:
            # 네이버 뉴스 검색을 통해 '시청률 순위' 관련 최신 기사 텍스트 분석
            return self._get_chart_via_news(category, f"{category} 시청률 순위 닐슨코리아")
        return json.dumps({"top10": []})

    def _get_kobis_movie(self):
        """[영화] 영진위 공식 API 활용"""
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={target_date}"
        
        try:
            res = requests.get(url, timeout=10)
            data = res.json().get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
            top10 = [{"rank": int(item['rank']), "title": item['movieNm'], "info": f"관객 {item['audiCnt']}"} for item in data[:10]]
            return json.dumps({"top10": top10}, ensure_ascii=False)
        except:
            return json.dumps({"top10": []})

    def _get_chart_via_news(self, category, query):
        """네이버 뉴스 API에서 기사 텍스트를 가져와 AI로 차트 추출"""
        client_id = os.environ.get("NAVER_CLIENT_ID")
        client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=sim"
        
        headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        try:
            res = requests.get(url, headers=headers)
            items = res.json().get('items', [])
            context = " ".join([f"{i['title']} {i['description']}" for i in items])
            return self._ai_extract_chart(category, context)
        except:
            return json.dumps({"top10": []})

    def _ai_extract_chart(self, category, context):
        """지저분한 텍스트에서 Groq AI가 JSON 순위표만 추출"""
        if not self.groq_client: return json.dumps({"top10": []})

        prompt = f"""
        Extract the latest Top 10 ranking for {category} from the text.
        Return ONLY a JSON object: {{"top10": [{{"rank": 1, "title": "...", "info": "..."}}, ...]}}
        Text: {context[:3000]}
        """
        try:
            chat = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
                response_format={"type": "json_object"}
            )
            return chat.choices[0].message.content
        except:
            return json.dumps({"top10": []})
