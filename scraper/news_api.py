import os
import json
import requests
import re
import random  # [추가] 스타일 랜덤 선택을 위해 필요
from datetime import datetime, timedelta
from groq import Groq

class NewsEngine:
    def __init__(self, run_count=0, db_path="news_history.db"):
        self.run_count = run_count
        
        self.groq_api_key = os.environ.get(f"GROQ_API_KEY{run_count + 1}") or os.environ.get("GROQ_API_KEY1")
        self.pplx_api_key = os.environ.get("PERPLEXITY_API_KEY")
        
        self.groq_client = Groq(api_key=self.groq_api_key)

    def is_using_primary_key(self):
        return self.run_count == 0

    # ---------------------------------------------------------
    # [설정] 카테고리별 검색 타겟 (한국어)
    # ---------------------------------------------------------
    def _get_target_description(self, category):
        mapping = {
            "k-pop": "대한민국 가수, 아이돌 그룹",
            "k-drama": "한국 드라마에 출연한 배우",
            "k-movie": "한국 영화에 출연한 배우 및 영화 감독",
            "k-entertain": "한국 예능에 출연한 방송인, 개그맨",
            "k-culture": "한국 문화계 유명인사, 유튜버, 인플루언서"
        }
        return mapping.get(category, "유명인")

    # ---------------------------------------------------------
    # [유틸] 한국 시간(KST) 구하기
    # ---------------------------------------------------------
    def _get_korean_time_str(self):
        utc_now = datetime.utcnow()
        kst_now = utc_now + timedelta(hours=9)
        return kst_now.strftime("%Y년 %m월 %d일 %H시 %M분")

    # ---------------------------------------------------------
    # [핵심] JSON 청소기
    # ---------------------------------------------------------
    def _clean_and_parse_json(self, text):
        try:
            match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL)
            if match: text = match.group(1)
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1: text = text[start:end+1]
            return json.loads(text)
        except:
            return {}

    # ---------------------------------------------------------
    # [Step 1] Top 10 차트 (이름은 한국어로!)
    # ---------------------------------------------------------
    def get_top10_chart(self, category):
        current_time = self._get_korean_time_str()
        target_desc = self._get_target_description(category)
        
        print(f"📊 [{category}] Fetching Top 10 Chart ({current_time} 기준)...")
        
        if not self.pplx_api_key: return "{}"

        prompt = (
            f"현재 시간: {current_time}. "
            f"검색 출처: site:news.naver.com. "
            f"목표: 현재 시간 기준으로 '지난 24시간 동안' 네이버 뉴스 기사에서 가장 많이 언급된 '{target_desc}' 관련 순위 Top 10을 찾으세요. "
            "조건 1: 어제부터 오늘까지 기사가 쏟아진 화제성 순위여야 합니다. "
            "조건 2: 결과 데이터(제목, 이름)는 번역하지 말고 '한국어 그대로' 주세요. "
            "형식: {'top10': [{'rank': 1, 'title': '한국어 제목/이름', 'info': '이유', 'score': 95}]}"
        )
        
        raw_text = self._call_perplexity_text(prompt)
        parsed_json = self._clean_and_parse_json(raw_text)
        return json.dumps(parsed_json)

    # ---------------------------------------------------------
    # [Step 2] 인물 30인 리스트 (이름은 한국어로!)
    # ---------------------------------------------------------
    def get_top30_people(self, category):
        current_time = self._get_korean_time_str()
        target_desc = self._get_target_description(category)
        
        print(f"📡 [{category}] Searching for Top 30 People ({current_time} 기준)...")
        
        if not self.pplx_api_key:
            print("   > ⚠️ Perplexity API Key missing.")
            return "{}"

        prompt = (
            f"현재 시간: {current_time}. "
            f"검색 출처: site:news.naver.com. "
            f"목표: 현재 시간 기준으로 '지난 24시간 동안' 네이버 뉴스 기사에서 가장 많이 언급된 '{target_desc}' 30명을 찾으세요. "
            "조건 1: 평소 유명한 사람이 아니라 '오늘 뉴스에 나온' 사람이어야 합니다. "
            "조건 2: 이름을 영어로 바꾸지 마세요. 검색을 위해 '한국어 이름'이 필요합니다. "
            "조건 3: 기사 언급량이 많은 순서대로 정렬하세요. "
            "형식: {'people': [{'rank': 1, 'name_en': 'English Name', 'name_kr': '한국어 이름'}]}"
        )
        
        try:
            raw_text = self._call_perplexity_text(prompt)
            parsed_data = self._clean_and_parse_json(raw_text)
            
            if "people" in parsed_data and len(parsed_data["people"]) > 0:
                return json.dumps(parsed_data)
            else:
                print(f"   > ⚠️ Empty data. Raw text start: {raw_text[:100]}...")
                return "{}"
        except Exception as e:
            print(f"   > ⚠️ Search Failed: {e}")
            return "{}"

    # ---------------------------------------------------------
    # [Step 3] 쿨타임 (Pass)
    # ---------------------------------------------------------
    def is_in_cooldown(self, name):
        return False

    def update_history(self, name, category):
        pass

    # ---------------------------------------------------------
    # [Step 4] 팩트 체크 (한국어 검색 -> 3개 기사 -> 영어 요약)
    # ---------------------------------------------------------
    def fetch_article_details(self, name_kr, name_en, category, rank):
        current_time = self._get_korean_time_str()
        search_name = name_kr if name_kr else name_en
        
        print(f"    🔍 Searching facts for: {search_name} (Latest 3 Articles)...")
        
        if not self.pplx_api_key:
            return "NO NEWS FOUND"

        prompt = (
            f"현재 시간: {current_time}. "
            f"검색 출처: site:news.naver.com. "
            f"검색어: '{search_name}'. "
            "지시사항: "
            "1. 지난 24시간 이내에 작성된 기사 중 '가장 최신 기사 3개'를 찾으세요. "
            "2. 그 3개 기사의 내용을 종합해서 핵심 내용을 파악하세요. "
            "3. 최종 결과는 '영어(English)'로 3문장으로 요약해서 출력하세요. "
            "조건: 만약 24시간 이내 기사가 하나도 없다면 'NO NEWS FOUND'라고만 출력하세요."
        )

        try:
            content = self._call_perplexity_text(prompt)
            if not content or len(content) < 10:
                return "Failed to fetch news."
            return content
        except Exception as e:
            print(f"    ⚠️ Fact Check Error: {e}")
            return "Failed to fetch news."

    # ---------------------------------------------------------
    # [Step 5] 기사 작성 (Groq - 독창성 강화 버전)
    # ---------------------------------------------------------
    def edit_with_groq(self, name, facts, category):
        # 팩트가 없으면 중단
        if "NO NEWS FOUND" in facts or "Failed" in facts:
            return "Headline: Error\nNO NEWS FOUND"

        # [다양성 엔진] 매번 다른 스타일을 적용하여 패턴화 방지
        styles = [
            "Witty and trendy (like a Gen-Z viral blog post)",
            "Professional and analytical (like a Billboard or Variety column)",
            "Story-driven and emotional (focusing on the artist's journey)",
            "Punchy and direct (highlighting the global impact)",
            "In-depth and contextual (explaining the cultural nuance)"
        ]
        selected_style = random.choice(styles)

        prompt = f"""
        ACT AS: A Senior Editor for a Global K-Culture Magazine.
        TARGET AUDIENCE: International fans (US, Europe, Global) who love K-Content.
        
        TOPIC: {name} ({category})
        SOURCE MATERIAL (FACTS): {facts}
        
        YOUR ASSIGNMENT:
        Write a unique and engaging news article based STRICTLY on the facts above.
        
        STYLE GUIDELINE:
        - Tone: {selected_style} <--- IMPORTANT: Adopt this tone!
        - Perspective: Explain why this news matters to international fans.
        - Structure: Do NOT follow a fixed template. Be creative with paragraph flow.
        
        CRITICAL RULES (DO NOT IGNORE):
        1. NO PREDICTIONS: Do not say "We look forward to..." or "It is expected that...". Stick to what happened.
        2. NO CLICHES: Do not start headlines with "Breaking News", "Report", or "{name} is...".
        3. HEADLINE: Must be catchy, idiomatic, and unique. Like a magazine feature title.
        4. FACT-BASED: Do not invent details. Only use the Source Material.
        
        FORMAT:
        Headline: [Insert Creative Headline Here]
        [Body Text in English]
        ###SCORE: [0-100 based on global buzz]
        """
        
        try:
            # temperature를 0.7 -> 0.85로 높여서 창의성 부여
            completion = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85 
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Headline: Error\n{e}"

    # ---------------------------------------------------------
    # API 호출 헬퍼
    # ---------------------------------------------------------
    def _call_perplexity_text(self, prompt):
        url = "https://api.perplexity.ai/chat/completions"
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [{"role": "user", "content": prompt}]
        }
        headers = {
            "Authorization": f"Bearer {self.pplx_api_key}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return ""
        except:
            return ""
