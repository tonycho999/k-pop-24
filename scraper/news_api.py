import os
import time
import json
import re
import random
from openai import OpenAI
from groq import Groq

class NewsEngine:
    def __init__(self, run_count=0):
        # Perplexity (Search & Data Collection)
        self.pplx = OpenAI(
            api_key=os.environ.get("PERPLEXITY_API_KEY"), 
            base_url="https://api.perplexity.ai"
        )
        
        # ---------------------------------------------------------
        # [Core] Sequential Key Rotation
        # ---------------------------------------------------------
        self.groq_keys = []
        for i in range(1, 9): 
            key_name = f"GROQ_API_KEY{i}"
            val = os.environ.get(key_name)
            if val: self.groq_keys.append(val)
        
        if not self.groq_keys:
            print("⚠️ No Groq API Keys found!")
            self.current_key = None
            self.current_key_index = -1
        else:
            self.current_key_index = run_count % len(self.groq_keys)
            self.current_key = self.groq_keys[self.current_key_index]
            print(f"🔑 [Key Rotation] Run: {run_count} -> Using GROQ_API_KEY{self.current_key_index + 1}")

        self.groq = self._create_groq_client()
        self.model_id = self._get_optimal_model()
        print(f"🤖 Selected AI Model: {self.model_id}")

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
    # [Step 1] Get Rankings List (Top 10 Charts + Top 30 People Names)
    # ----------------------------------------------------------------
    def get_rankings_list(self, category):
        """
        Fetches ONLY the list of names and titles. No article bodies yet.
        """
        chart_instruction = ""
        people_instruction = ""

        if category == "k-pop":
            chart_instruction = "Source: **Melon Chart (Real-time)**. Target: Song Titles & Artists."
            people_instruction = "Singers / Idol Groups"
        elif category == "k-drama":
            chart_instruction = "Source: **Naver TV Ratings (Drama)**. Target: Drama Titles only."
            people_instruction = "Actors / PDs (Drama related)"
        elif category == "k-movie":
            chart_instruction = "Source: **Naver Movie Box Office**. Target: Movie Titles (Foreign allowed)."
            people_instruction = "Actors / Directors (Movie related)"
        elif category == "k-entertain":
            chart_instruction = "Source: **Naver TV Ratings**. Target: Show Titles."
            people_instruction = "Variety Show Cast / MCs / PDs"
        elif category == "k-culture":
            chart_instruction = "Source: Current Trending Keywords. Target: Place, Festival, Food."
            people_instruction = "Figures related to K-Culture (EXCLUDING Celebrities)"

        system_prompt = "You are a specialized researcher. Search ONLY Korean domestic sources (Naver, Daum, Melon)."
        
        user_prompt = f"""
        Perform a search on **Korean domestic portals (Naver, Melon)** within the **last 24 hours**.
        Category: {category}

        **Task 1: Top 10 Ranking Chart**
        {chart_instruction}
        - Get the actual current ranking data. Translate Titles/Names to English.

        **Task 2: Top 30 Trending People (Buzz Ranking)**
        - Identify the Top 30 people ({people_instruction}) mentioned most in Korean news in the last 24 hours.
        - Rank them from 1 to 30 based on news volume/buzz.
        - Output JUST their names (English & Korean).

        **Output JSON Format ONLY:**
        {{
            "top10": [
                {{"rank": 1, "title": "...", "info": "..."}}, ...
            ],
            "people": [
                {{"rank": 1, "name_en": "...", "name_kr": "..."}},
                ...
                {{"rank": 30, "name_en": "...", "name_kr": "..."}}
            ]
        }}
        """

        print(f"  🔍 [Perplexity] Searching Trends for {category}... (Timeout: 180s)")
        try:
            response = self.pplx.chat.completions.create(
                model="sonar-pro",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                timeout=180
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ PPLX List Error: {e}")
            return "{}"

    # ----------------------------------------------------------------
    # [Step 2] Deep Dive: Fetch Article Details for Specific Person
    # ----------------------------------------------------------------
    def fetch_article_details(self, name_kr, name_en, category, rank):
        """
        Reads N articles about a specific person and summarizes facts.
        """
        # Determine number of articles based on rank
        article_count = 2
        if rank <= 3: article_count = 4
        elif rank <= 10: article_count = 3
        
        system_prompt = "You are a reporter summarizing Korean news for global readers."
        
        user_prompt = f"""
        Search for **Korean news articles** about '{name_kr}' ({category}) published within the **last 24 hours**.
        
        **Constraint:**
        1. Read at least **{article_count} distinct articles**.
        2. Summarize the key facts in English.
        3. Ignore international sources (Allkpop, etc). Use ONLY Naver/Dispatch/Korean media.
        
        Output format: Just the factual summary points in English.
        """
        
        print(f"    ... [Perplexity] Digging details for {name_en} (Rank {rank})...")
        try:
            response = self.pplx.chat.completions.create(
                model="sonar-pro",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                timeout=60
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"    ⚠️ Failed to fetch details for {name_en}: {e}")
            return f"Failed to fetch details for {name_en}."

    # ----------------------------------------------------------------
    # [Step 3] Groq: Write Article
    # ----------------------------------------------------------------
    def edit_with_groq(self, name_en, facts, category):
        """
        Uses Groq (Llama 3) to write the final article based on facts.
        """
        system_msg = "You are a Senior Editor at a top Global K-Pop Magazine."
        user_msg = f"""
        Topic: {name_en}
        Facts: {facts}
        
        Write a news article **in English**.
        
        [Headline Rules]
        1. **Format**: Catchy, professional headline (1st line).
        2. ❌ **FORBIDDEN**: Do NOT start with "News about", "Update on".
        3. ✅ **Style**: Active verbs (e.g., "Dominates", "Reveals").

        [Body Rules]
        1. Style: Write in the style of a professional Korean entertainment journalist.
        2. Tone: Professional yet engaging for global fans.
        3. Structure: At least 3 paragraphs.
        4. Formatting: Start body text from the 2nd line.
        
        [Score Rule]
        - At the very end, write "###SCORE: XX" (10-99) based on viral potential.
        """
        
        try:
            completion = self.groq.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                temperature=0.7,
                timeout=60
            )
            content = completion.choices[0].message.content
            
            # Post-processing
            lines = content.split('\n')
            if lines[0].lower().startswith("news about"):
                lines[0] = lines[0].replace("News about ", "").replace("news about ", "").strip()
                return "\n".join(lines)
            return content
        except Exception as e:
            print(f"    ⚠️ Groq Error: {e}")
            return f"{name_en}: Latest Updates\n{facts}\n###SCORE: 50"
