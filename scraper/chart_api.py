import os
import json
import requests
import time
import random
import email.utils
from datetime import datetime, timedelta
from groq import Groq

class ChartEngine:
    def __init__(self):
        self.groq_client = None
        self.kobis_key = os.environ.get("KOBIS_API_KEY")
        self.selected_model = None

    def set_groq_client(self, api_key):
        """API 키 설정 및 실시간 가용 모델 자동 선택"""
        self.groq_client = Groq(api_key=api_key)
        self._auto_select_model()

    def _auto_select_model(self):
        """Groq 가용 모델 중 최적의 모델 선택"""
        try:
            models = self.groq_client.models.list()
            model_ids = [m.id for m in models.data]
            preferences = [
                "llama-3.3-70b-specdec",
                "llama-3.1-70b-versatile",
                "llama-3.1-8b-instant"
            ]
            for pref in preferences:
                if pref in model_ids:
                    self.selected_model = pref
                    print(f"🤖 AI Model Selected: {self.selected_model}")
                    return
            self.selected_model = model_ids[0]
        except Exception as e:
            print(f"❌ Model selection error: {e}")
            self.selected_model = "llama-3.1-8b-instant"

    def get_top10_chart(self, category):
        """24시간 이내의 최신 데이터만 수집하여 영문으로 번역 반환"""
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                # API 호출 간격 유지 (랜덤 대기)
                wait_time = random.uniform(3.0, 5.0)
                time.sleep(wait_time)

                if category == "k-movie":
                    # 영화는 공식 API에서 어제(24시간 내) 데이터를 직접 가져옴
                    raw_data = self._get_kobis_movie()
                else:
                    # 카테고리별 검색어 (최신성 유도를 위해 '오늘', '실시간' 강조)
                    queries = {
                        "k-pop": "오늘 실시간 음원 차트 순위 멜론 써클차트",
                        "k-drama": "오늘 드라마 시청률 순위 닐슨코리아",
                        "k-entertain": "오늘 예능 시청률 순위 닐슨코리아",
                        "k-culture": "오늘 성수동 한남동 팝업스토어 핫플레이스 추천"
                    }
                    raw_data = self._get_fresh_news_data(category, queries.get(category))

                # 분석 및 영문 번역
                return self._ai_extract_and_translate(category, raw_data)

            except Exception as e:
                if attempt < max_retries:
                    print(f"⚠️ [{category}] Retry (Attempt {attempt+2}): {e}")
                    time.sleep(5)
                else:
                    print(f"❌ [{category}] Skipped: {e}")
                    return json.dumps({"top10": []})

    def _get_fresh_news_data(self, category, query):
        """네이버 뉴스에서 정확히 24시간 이내의 기사만 필터링하여 추출"""
        client_id = os.environ.get("NAVER_CLIENT_ID")
        client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=30&sort=date"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        
        res = requests.get(url, headers=headers, timeout=10)
        items = res.json().get('items', [])
        
        now = datetime.now()
        fresh_contents = []
        
        for item in items:
            # 네이버 날짜 형식(RFC822) 파싱
            pub_date = email.utils.parsedate_to_datetime(item['pubDate']).replace(tzinfo=None)
            
            # 정확히 현재 시간으로부터 24시간 이내 기사만 통과
            if now - pub_date <= timedelta(hours=24):
                fresh_contents.append(f"[{pub_date.strftime('%H:%M')}] {item['title']} {item['description']}")

        if not fresh_contents:
            raise ValueError(f"No fresh news found for {category} within the last 24 hours.")
            
        print(f"✅ Found {len(fresh_contents)} fresh news items for {category}.")
        return "\n".join(fresh_contents)[:5000]

    def _get_kobis_movie(self):
        """영화진흥위원회 API (어제 날짜 고정)"""
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={target_date}"
        res = requests.get(url, timeout=10)
        return res.text

    def _ai_extract_and_translate(self, category, raw_data):
        """AI를 통한 데이터 분석 및 영문 번역"""
        prompt = f"""
        Analyze the provided South Korean news snippets from the LAST 24 HOURS to extract the {category} Top 10.
        
        [STRICT GUIDELINES]
        1. TIME SENSITIVITY: Use ONLY data from the provided text. Ensure it represents current trends.
        2. TRANSLATION: Translate the 'title' and 'info' into English.
        3. PROPER NOUNS: Use official English names for artists and shows (e.g., 'NewJeans' instead of 'Nyujinseu', 'IU' instead of 'Aiyu').
        4. ACCURACY: If the text doesn't provide a clear ranking, list the most discussed topics/items in the text.
        5. OUTPUT: Respond ONLY with a JSON object in this format:
           {{"top10": [{{"rank": 1, "title": "English Title", "info": "Brief English Info"}}, ...]}}
        
        Data (Last 24h):
        {raw_data}
        """
        
        chat = self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.selected_model,
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return chat.choices[0].message.content
