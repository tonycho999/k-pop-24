import os
import time
import json
import re
import random
from openai import OpenAI
from groq import Groq

class NewsEngine:
    def __init__(self, run_count=0):
        # Perplexity
        self.pplx = OpenAI(
            api_key=os.environ.get("PERPLEXITY_API_KEY"), 
            base_url="https://api.perplexity.ai"
        )
        
        # 키 로테이션 (1~8번)
        self.groq_keys = []
        for i in range(1, 9): 
            key_name = f"GROQ_API_KEY{i}"
            val = os.environ.get(key_name)
            if val: self.groq_keys.append(val)
        
        if not self.groq_keys:
            self.current_key = None
            self.current_key_index = -1
        else:
            self.current_key_index = run_count % len(self.groq_keys)
            self.current_key = self.groq_keys[self.current_key_index]
            print(f"🔑 [Key Rotation] Run: {run_count} -> Using GROQ_API_KEY{self.current_key_index + 1}")

        self.groq = self._create_groq_client()
        self.model_id = self._get_optimal_model()

    def _create_groq_client(self):
        if not self.current_key: return None
        return Groq(api_key=self.current_key)

    def is_using_primary_key(self):
        return self.current_key_index == 0

    def _get_optimal_model(self):
        default = "llama-3.3-70b-versatile"
        if not self.groq: return default
        try:
            models = self.groq.models.list()
            ids = [m.id for m in models.data]
            for k in ["llama-3.3-70b", "llama-3.2-90b", "llama-3.1-70b", "mixtral", "llama3-70b"]:
                for mid in ids:
                    if k in mid: return mid
            return default
        except: return default

    # ----------------------------------------------------------------
    # [Task 1] Top 10 차트 데이터 수집 (인물 뉴스 배제)
    # ----------------------------------------------------------------
    def get_top10_chart(self, category):
        """
        오직 '랭킹 차트'만 검색해서 가져옵니다.
        """
        target_info = ""
        if category == "k-pop":
            target_info = "Source: **Melon Chart (Real-time)**. Target: Song Titles & Artists."
        elif category == "k-drama":
            target_info = "Source: **Naver TV Ratings (Drama)**. Target: Drama Titles only."
        elif category == "k-movie":
            target_info = "Source: **Naver Movie Box Office**. Target: Movie Titles (Foreign movies allowed)."
        elif category == "k-entertain":
            target_info = "Source: **Naver TV Ratings (Variety)**. Target: Show Titles."
        elif category == "k-culture":
            target_info = "Source: Trending Keywords (Place, Festival, Food). Target: Keywords."

        system_prompt = "You are a specialized researcher. Search ONLY Korean domestic sources."
        user_prompt = f"""
        Search **Korean domestic portals (Naver, Melon)** within the **last 24 hours**.
        Category: {category}

        **Task: Extract the Top 10 Ranking Chart**
        {target_info}
        - Get the actual ranking data.
        - **Translate all Titles/Names to English.**

        **Output JSON Format ONLY:**
        {{
            "top10": [
                {{"rank": 1, "title": "...", "info": "..."}},
                ...
                {{"rank": 10, "title": "...", "info": "..."}}
            ]
        }}
        """
        print(f"  🔍 [Perplexity] Fetching Top 10 Chart for {category}...")
        try:
            response = self.pplx.chat.completions.create(
                model="sonar-pro",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                timeout=180
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ PPLX Chart Error: {e}")
            return "{}"

    # ----------------------------------------------------------------
    # [Task 2] Top 30 인물 명단 수집 (기사 요약 전 단계)
    # ----------------------------------------------------------------
    def get_top30_people(self, category):
        """
        언급량 기준 상위 30명의 인물 이름만 가져옵니다.
        """
        target_people = ""
        if category == "k-pop": target_people = "Singers / Idol Groups"
        elif category == "k-drama": target_people = "Actors / PDs (Drama related)"
        elif category == "k-movie": target_people = "Actors / Directors (Movie related)"
        elif category == "k-entertain": target_people = "Variety Show Cast / MCs / PDs"
        elif category == "k-culture": target_people = "Figures related to K-Culture (EXCLUDING Celebrities)"

        system_prompt = "You are a specialized researcher. Search ONLY Korean domestic sources."
        user_prompt = f"""
        Search **Korean news (Naver News)** within the **last 24 hours**.
        Category: {category}

        **Task: Identify Top 30 Trending People**
        - Target: {target_people}
        - Rank them 1 to 30 based on news buzz/volume.
        - **Output JUST their names (English & Korean).**

        **Output JSON Format ONLY:**
        {{
            "people": [
                {{"rank": 1, "name_en": "...", "name_kr": "..."}},
                ...
                {{"rank": 30, "name_en": "...", "name_kr": "..."}}
            ]
        }}
        """
        print(f"  🔍 [Perplexity] Fetching Top 30 People List for {category}...")
        try:
            response = self.pplx.chat.completions.create(
                model="sonar-pro",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                timeout=180
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ PPLX People List Error: {e}")
            return "{}"

    # ----------------------------------------------------------------
    # [Task 3] 심층 기사 조사 (순위별 기사 수 차등 적용)
    # ----------------------------------------------------------------
    def fetch_article_details(self, name_kr, name_en, category, rank):
        # [조건 적용] 순위별 기사 참조 개수
        article_count = 2
        if rank <= 3: article_count = 4    # 1~3위: 4개
        elif rank <= 10: article_count = 3 # 4~10위: 3개
        # 11~30위: 2개 (기본값)

        system_prompt = "You are a reporter summarizing Korean news."
        user_prompt = f"""
        Search for **Korean news articles** about '{name_kr}' ({category}) published within the **last 24 hours**.
        
        **Constraints:**
        1. Read at least **{article_count} distinct articles**.
        2. Summarize the key facts in English.
        3. Use ONLY Korean domestic media (Naver, Dispatch, etc.). Ignore international sources.
        
        Output format: Just the factual summary points in English.
        """
        
        print(f"    ... [Perplexity] Reading {article_count} articles for Rank #{rank} {name_en}...")
        try:
            response = self.pplx.chat.completions.create(
                model="sonar-pro",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                timeout=60
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"    ⚠️ Detail Fetch Error: {e}")
            return "Failed."

    # ----------------------------------------------------------------
    # [Task 4] Groq 기사 작성
    # ----------------------------------------------------------------
    def edit_with_groq(self, name_en, facts, category):
        system_msg = "You are a Senior Editor at a top Global K-Pop Magazine."
        user_msg = f"""
        Topic: {name_en}
        Facts: {facts}
        Write a news article **in English**.
        - Headline: Catchy, No "News about" prefix.
        - Body: 3 paragraphs, professional tone.
        - End with "###SCORE: XX" (10-99).
        """
        try:
            completion = self.groq.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                temperature=0.7,
                timeout=60
            )
            content = completion.choices[0].message.content
            lines = content.split('\n')
            if lines[0].lower().startswith("news about"):
                lines[0] = lines[0].replace("News about ", "").replace("news about ", "").strip()
                return "\n".join(lines)
            return content
        except Exception as e:
            print(f"    ⚠️ Groq Error: {e}")
            return f"{name_en}: Latest Updates\n{facts}\n###SCORE: 50"
