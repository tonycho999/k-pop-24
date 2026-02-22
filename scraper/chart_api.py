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
        self.selected_model = None

    def set_groq_client(self, api_key):
        self.groq_client = Groq(api_key=api_key)
        self._auto_select_model()

    def _auto_select_model(self):
        try:
            models = self.groq_client.models.list()
            model_ids = [m.id for m in models.data]
            preferences = ["llama-3.3-70b-specdec", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"]
            for pref in preferences:
                if pref in model_ids:
                    self.selected_model = pref
                    return
            self.selected_model = "llama-3.1-8b-instant"
        except:
            self.selected_model = "llama-3.1-8b-instant"

    def get_top10_chart(self, category):
        """네이버 검색 차트 데이터 수집 및 영문 번역"""
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                wait_time = random.uniform(2.0, 3.0) # 봇이 아니므로 대기시간 단축 가능
                time.sleep(wait_time)

                if category == "k-movie":
                    raw_data = self._get_kobis_movie()
                else:
                    # 네이버 통합 검색 결과 영역 타겟팅 (음원 순위, 시청률 등)
                    queries = {
                        "k-pop": "음원 순위",
                        "k-drama": "드라마 시청률 순위",
                        "k-entertain": "예능 시청률 순위",
                        "k-culture": "성수동 팝업스토어 순위"
                    }
                    raw_data = self._get_naver_search_data(queries.get(category))

                # AI에게 분석 및 '영문 번역' 요청
                return self._ai_extract_and_translate(category, raw_data)

            except Exception as e:
                if attempt < max_retries:
                    time.sleep(3)
                else:
                    return json.dumps({"top10": []})

    def _get_naver_search_data(self, query):
        """네이버 검색 결과의 구조화된 데이터 추출 (봇 없이 요청)"""
        url = "https://search.naver.com/search.naver"
        params = {"query": query, "where": "nexearch"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, params=params, headers=headers, timeout=10)
        # HTML 본문 중 차트 데이터가 포함된 텍스트만 추출하여 AI에게 전달
        return res.text[:5000] # 분석에 필요한 앞부분만 전달

    def _get_kobis_movie(self):
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={target_date}"
        res = requests.get(url, timeout=10)
        return res.text

    def _ai_extract_and_translate(self, category, raw_data):
        """한국어 데이터를 분석하여 영문으로 번역된 JSON 반환"""
        prompt = f"""
        You are an expert South Korean culture analyst. 
        Analyze the provided raw data for '{category}' and extract the Top 10 rankings.
        
        [IMPORTANT INSTRUCTIONS]
        1. Translate the Title and Info into ENGLISH.
        2. Keep proper nouns (like K-pop group names) as they are commonly known in English (e.g., '아이유' to 'IU', '뉴진스' to 'NewJeans').
        3. For Drama/Entertain, translate the show titles into their official English titles.
        4. Respond ONLY in this JSON format:
        {{"top10": [{{"rank": 1, "title": "English Title", "info": "English Info"}}, ...]}}
        
        Data: {raw_data[:3000]}
        """
        chat = self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.selected_model,
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return chat.choices[0].message.content
