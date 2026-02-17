import os
import json
from datetime import datetime, timedelta, timezone
from openai import OpenAI
from groq import Groq

class NewsEngine:
    def __init__(self, run_count=0):
        # Perplexity for news searching
        self.pplx = OpenAI(
            api_key=os.environ.get("PERPLEXITY_API_KEY"), 
            base_url="https://api.perplexity.ai"
        )
        
        # Groq Key Rotation
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
    # [Task 2] Top 30 People (Strict Naver News Only)
    # ----------------------------------------------------------------
    def get_top30_people(self, category):
        kst = timezone(timedelta(hours=9))
        today_str = datetime.now(kst).strftime("%Y-%m-%d")

        target_people = ""
        if category == "k-pop": target_people = "Singers / Idols"
        elif category == "k-drama": target_people = "Actors / PDs"
        elif category == "k-movie": target_people = "Actors / Directors"
        elif category == "k-entertain": target_people = "Variety Stars / MCs"
        elif category == "k-culture": target_people = "Public Figures (Non-Celebs)"

        # Strict Prompt
        system_prompt = "You are a news curator. Search ONLY 'Naver News' (news.naver.com)."
        user_prompt = f"""
        **Strict Search Rule:**
        1. Source: **Naver News (news.naver.com)** ONLY.
        2. Date: Articles published on **{today_str}** (Last 24h).
        3. ❌ **EXCLUDE**: Community posts (Theqoo, Instiz, DC Inside, Twitter, Blogs, Cafes).
        4. ❌ **EXCLUDE**: People with NO official news articles today.

        **Task:**
        Identify Top 30 people in '{category}' ({target_people}) who have the **most official news articles** today.
        
        **Output JSON ONLY:**
        {{
            "people": [
                {{ "rank": 1, "name_en": "...", "name_kr": "..." }},
                ...
                {{ "rank": 30, "name_en": "...", "name_kr": "..." }}
            ]
        }}
        """
        print(f"  🔍 [Perplexity] Fetching Top 30 People (Naver News Only)...")
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
    # [Task 3] Deep Dive & Verification
    # ----------------------------------------------------------------
    def fetch_article_details(self, name_kr, name_en, category, rank):
        article_count = 2
        if rank <= 3: article_count = 4
        elif rank <= 10: article_count = 3
        
        system_prompt = "You are a reporter. Search ONLY Naver News."
        user_prompt = f"""
        Search **Naver News (news.naver.com)** for '{name_kr}' ({category}) in the **last 24 hours**.
        
        **Constraints:**
        1. Find at least **{article_count} distinct OFFICIAL ARTICLES**.
        2. If no official news exists, return "NO NEWS FOUND".
        3. Do NOT use blogs or twitter.
        
        Summarize the key facts in English.
        """
        
        print(f"    ... [Perplexity] Checking news for #{rank} {name_en}...")
        try:
            response = self.pplx.chat.completions.create(
                model="sonar-pro",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                timeout=60
            )
            return response.choices[0].message.content
        except: return "Failed."

    # ----------------------------------------------------------------
    # [Task 4] Groq Article Writing
    # ----------------------------------------------------------------
    def edit_with_groq(self, name_en, facts, category):
        system_msg = "You are a Senior Editor."
        user_msg = f"""
        Topic: {name_en}
        Facts: {facts}
        Write a news article **in English**.
        - Headline: Catchy, No "News about" prefix.
        - Body: 3 paragraphs, professional tone.
        - End with "###SCORE: XX".
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
        except: return f"{name_en}: Latest Updates\n{facts}\n###SCORE: 50"
