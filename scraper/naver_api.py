import os
import json
import requests
import re
import random
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
    # [설정] 카테고리별 검색 타겟
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
    # [유틸] 한국 시간(KST) 구하기 (UTC+9 강제 적용)
    # ---------------------------------------------------------
    def _get_korean_time_str(self):
        # 서버 시간이 몇 시든 상관없이, 강제로 UTC를 구해 9시간을 더합니다.
        # 이것이 '진짜 한국 시간'입니다.
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
    # [Step 1] Top 10 차트 (한국 시간 기준 24시간 이내)
    # ---------------------------------------------------------
    def get_top10_chart(self, category):
        current_time_str = self._get_korean_time_str()
        target_desc = self._get_target_description(category)
        
        print(f"📊 [{category}] Fetching Top 10 Chart (KST: {current_time_str})...")
        
        if not self.pplx_api_key: return "{}"

        prompt = (
            f"Current KST Time: {current_time_str}. "
            f"Source: ONLY site:news.naver.com. "
            f"Target: Find Top 10 trending '{target_desc}' based on news coverage volume. "
            "STRICT CONSTRAINT: Only include news published within the LAST 24 HOURS from the Current KST Time. "
            "Do NOT include older news. "
            "Output Requirement: Return titles and names in KOREAN (한국어). "
            "Return ONLY valid JSON. "
            "Format: {'top10': [{'rank': 1, 'title': '한국어 제목/이름', 'info': '이유', 'score': 95}]}"
        )
        
        raw_text = self._call_perplexity_text(prompt)
        parsed_json = self._clean_and_parse_json(raw_text)
        return json.dumps(parsed_json)

    # ---------------------------------------------------------
    # [Step 2] 인물 30인 리스트 (한국 시간 기준 24시간 이내)
    # ---------------------------------------------------------
    def get_top30_people(self, category):
        current_time_str = self._get_korean_time_str()
        target_desc = self._get_target_description(category)
        
        print(f"📡 [{category}] Searching for Top 30 People (KST: {current_time_str})...")
        
        if not self.pplx_api_key:
            print("   > ⚠️ Perplexity API Key missing.")
            return "{}"

        prompt = (
            f"Current KST Time: {current_time_str}. "
            f"Source: ONLY site:news.naver.com. "
            f"Target: List top 30 '{target_desc}' mentioned in news articles. "
            "STRICT CONSTRAINT: Look for articles published strictly within the LAST 24 HOURS from the Current KST Time. "
            "If no one fits the 24-hour criteria, return an empty list. Do NOT fake data. "
            "Sorting: Sort by mention count (Highest first). "
            "Output Requirement: Keep names in KOREAN (한국어). "
            "Return ONLY valid JSON. "
            "Format: {'people': [{'rank': 1, 'name_en': 'English Name', 'name_kr': '한국어 이름'}]}"
        )
        
        try:
            raw_text = self._call_perplexity_text(prompt)
            parsed_data = self._clean_and_parse_json(raw_text)
            
            if "people" in parsed_data and len(parsed_data["people"]) > 0:
                return json.dumps(parsed_data)
            else:
                print(f"   > ⚠️ No data strictly within last 24h. Raw: {raw_text[:100]}...")
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
    # [Step 4] 팩트 체크 (한국 시간 기준 24시간 이내)
    # ---------------------------------------------------------
    def fetch_article_details(self, name_kr, name_en, category, rank):
        current_time_str = self._get_korean_time_str()
        search_name = name_kr if name_kr else name_en
        
        print(f"    🔍 Searching facts for: {search_name} (Strict 24h)...")
        
        if not self.pplx_api_key:
            return "NO NEWS FOUND"

        prompt = (
            f"Current KST Time: {current_time_str}. "
            f"Source: site:news.naver.com. "
            f"Query: '{search_name}'. "
            "Task: Find official news articles published strictly within the LAST 24 HOURS from now. "
            "Output: Summarize the key facts in English (3 sentences). "
            "Constraint: If no articles are found in the last 24 hours, explicitly return 'NO NEWS FOUND'. Do not use old news."
        )

        try:
            content = self._call_perplexity_text(prompt)
            if not content or len(content) < 5:
                return "Failed to fetch news."
            return content
        except Exception as e:
            print(f"    ⚠️ Fact Check Error: {e}")
            return "Failed to fetch news."

    # ---------------------------------------------------------
    # [Step 5] 기사 작성 (Groq - 독창성 유지)
    # ---------------------------------------------------------
    def edit_with_groq(self, name, facts, category):
        if "NO NEWS FOUND" in facts or "Failed" in facts:
            return "Headline: Error\nNO NEWS FOUND"

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
        
        CRITICAL RULES:
        1. NO PREDICTIONS.
        2. NO CLICHES.
        3. HEADLINE: Must be catchy and unique.
        4. FACT-BASED: Only use the Source Material.
        
        FORMAT:
        Headline: [Insert Creative Headline Here]
        [Body Text in English]
        ###SCORE: [0-100 based on global buzz]
        """
        
        try:
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
            if response.status_code != 200:
                print(f"⚠️ API Error {response.status_code}: {response.text}")
                return ""
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"⚠️ API Call Failed: {e}")
            return ""
