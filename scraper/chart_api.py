import os
import json
import time
import random
from datetime import datetime
from model_manager import GroqModelManager

class ChartEngine:
    def __init__(self):
        self.groq_client = None
        self.model_id = None

    def set_groq_client(self, api_key):
        from groq import Groq
        self.groq_client = Groq(api_key=api_key)
        # 모델 매니저를 통해 최신/고성능 모델 자동 선택
        manager = GroqModelManager(self.groq_client)
        self.model_id = manager.get_best_model()

    def get_top10_chart(self, category):
        """네이버 API 없이 Groq의 검색/추론 능력만으로 데이터 생성"""
        # 작업 간 4~6초 랜덤 휴식
        wait_time = random.uniform(4.0, 6.0)
        print(f"⏳ Waiting {wait_time:.2f}s for {category}...")
        time.sleep(wait_time)

        # K-Culture 연예인 배제 규칙
        culture_filter = ""
        if category == "k-culture":
            culture_filter = "STRICT RULE: Focus ONLY on places and trends. NO celebrities or fan-events."

        prompt = f"""
        Today's date is {datetime.now().strftime('%B %22, 2026')}.
        Search and analyze the LATEST South Korean trends from the LAST 24 HOURS for '{category}'.
        
        [INSTRUCTIONS]
        1. Access real-time Korean data to find the Top 10 rankings.
        2. {culture_filter}
        3. Translate everything into English.
        4. For Drama/Variety, list current top shows by viewership ratings.
        5. Return ONLY a JSON object:
           {{"top10": [{{"rank": 1, "title": "English Title", "info": "Brief English Info"}}, ...]}}
        
        [STRICT] If you cannot find real-time 2026 data, do not make up old data. 
        Focus on accuracy for February 2026.
        """

        try:
            chat = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model_id,
                response_format={"type": "json_object"},
                temperature=0.2 # 약간의 유연함을 위해 0.2 설정
            )
            return chat.choices[0].message.content
        except Exception as e:
            print(f"❌ Groq Direct Search Error: {e}")
            return json.dumps({"top10": []})
