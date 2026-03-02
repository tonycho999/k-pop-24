import os
import json
import time
import requests
import google.generativeai as genai
from datetime import datetime, timedelta

class ChartEngine:
    def __init__(self):
        self.kobis_key = os.environ.get("KOBIS_API_KEY")
        self.model = None

    def set_api_key(self, api_key):
        """Gemini API 키 설정 및 최적 모델 자동 선택"""
        genai.configure(api_key=api_key)
        self.model = self._get_best_gemini_model()

    def _get_best_gemini_model(self):
        """
        [스마트 모델 선택]
        1. 사용 가능한 모델 리스트를 조회
        2. 유료/무거운 모델(Pro, Ultra) 제외
        3. 빠르고 최신 정보 반영이 좋은 'Flash' 계열 우선 선택
        """
        try:
            # generateContent 기능을 지원하는 모델 조회
            models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # 제외할 키워드 (유료/고비용)
            excluded = ["pro", "ultra", "advanced", "vision"]
            
            # 1차 필터링: 제외 키워드가 없는 모델만 남김
            candidates = [m.name for m in models if not any(x in m.name.lower() for x in excluded)]
            
            # 2차 필터링: 그 중에서 'flash'가 포함된 모델 우선 (속도/최신성)
            flash_models = [name for name in candidates if "flash" in name.lower()]
            
            # 최신 버전이 위로 오도록 정렬 (알파벳 역순: 1.5 > 1.0)
            flash_models.sort(reverse=True)
            
            if flash_models:
                print(f"🤖 Auto-selected Gemini Model: {flash_models}")
                return genai.GenerativeModel(flash_models)
            
            # Flash가 없으면 필터링된 것 중 최신 선택
            candidates.sort(reverse=True)
            if candidates:
                print(f"⚠️ Fallback Model: {candidates}")
                return genai.GenerativeModel(candidates)
                
            # 정말 아무것도 없으면 하드코딩 (안전장치)
            return genai.GenerativeModel('gemini-1.5-flash')
            
        except Exception as e:
            print(f"❌ Model Selection Error: {e}, using fallback.")
            return genai.GenerativeModel('gemini-1.5-flash')

    def get_top10_chart(self, category):
        """카테고리에 따라 API(영화)와 Gemini검색(나머지)을 분기 처리"""
        try:
            # 1. 영화: 영진위(KOBIS) 공식 데이터 사용
            if category == "k-movie":
                print(f"🎬 Fetching {category} via KOBIS API...")
                raw_data = self._get_kobis_data()
                return self._process_with_gemini(category, raw_data, context="movie_api")

            # 2. 나머지: Gemini 구글 검색 활용
            else:
                print(f"🌍 Fetching {category} via Gemini Google Search...")
                return self._process_with_gemini(category, None, context="search")

        except Exception as e:
            print(f"❌ Error in {category}: {e}")
            return json.dumps({"top10": []})

    def _get_kobis_data(self):
        """어제 날짜 기준 박스오피스 원문 데이터 가져오기"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={yesterday}"
        try:
            res = requests.get(url, timeout=10)
            return res.text
        except:
            return ""

    def _process_with_gemini(self, category, raw_data, context):
        """Gemini에게 데이터 검색/가공 요청"""
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        # 기본 프롬프트 설정
        base_prompt = f"""
        You are a K-Trend expert. Today is {today_date}.
        Output Format: JSON object ONLY {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief info" }}, ... ] }}
        Translate everything to English.
        """

        if context == "movie_api":
            prompt = f"""
            {base_prompt}
            Convert this raw KOBIS Box Office data into the Top 10 JSON format.
            Raw Data: {raw_data}
            """
        else:
            # K-Culture 전용 필터 (연예인 제외)
            culture_rule = ""
            if category == "k-culture":
                culture_rule = "STRICT: Exclude celebrities/idols. Focus on Hot Places (Seongsu, Hannam), Pop-up stores, and Food trends."

            prompt = f"""
            {base_prompt}
            Search and analyze the real-time Top 10 rankings for '{category}' in South Korea as of {today_date} (or yesterday).
            
            [Sources]
            - K-Drama/Entertain: Search Nielsen Korea ratings from yesterday.
            - K-Pop: Search latest Melon/Circle Chart.
            - K-Culture: {culture_rule}
            
            [STRICT] Do not use old data (e.g., from 2023, 2024). Find the latest 2026 data via Google Search.
            """

        response = self.model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return text
