import os
import json
import requests
import re
from groq import Groq

class NewsEngine:
    def __init__(self, run_count=0, db_path="news_history.db"):
        self.run_count = run_count
        
        # API 키 설정
        self.groq_api_key = os.environ.get(f"GROQ_API_KEY{run_count + 1}") or os.environ.get("GROQ_API_KEY1")
        self.pplx_api_key = os.environ.get("PERPLEXITY_API_KEY")
        
        self.groq_client = Groq(api_key=self.groq_api_key)

    def is_using_primary_key(self):
        return self.run_count == 0

    # ---------------------------------------------------------
    # [핵심] JSON 청소기 (에러 방지용)
    # ---------------------------------------------------------
    def _clean_and_parse_json(self, text):
        try:
            match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end+1]
            return json.loads(text)
        except:
            return {}

    # ---------------------------------------------------------
    # [Step 1] 순위표 가져오기 (네이버 뉴스 전용)
    # ---------------------------------------------------------
    def get_top10_chart(self, category):
        print(f"📊 [{category}] Fetching Top 10 Chart (Naver News Only)...")
        if not self.pplx_api_key: return "{}"

        # [수정됨] site:news.naver.com 조건 추가
        prompt = (
            f"Search ONLY on site:news.naver.com. "
            f"Find the current top 10 most popular {category} works or artists in South Korea right now based on recent Naver News articles. "
            "Do NOT use any other sources. "
            "Return ONLY valid JSON. "
            "Format: {'top10': [{'rank': 1, 'title': 'Name', 'info': 'Detail', 'score': 99}]}"
        )
        
        raw_text = self._call_perplexity_text(prompt)
        parsed_json = self._clean_and_parse_json(raw_text)
        return json.dumps(parsed_json)

    def get_top30_people(self, category):
        print(f"📡 [{category}] Searching for trending people (Naver News Only)...")
        
        if not self.pplx_api_key:
            print("   > ⚠️ Perplexity API Key missing.")
            return "{}"

        # [수정됨] site:news.naver.com 조건 추가
        prompt = (
            f"Search ONLY on site:news.naver.com. "
            f"List top 30 trending people in South Korea related to '{category}' based on today's Naver News. "
            "Focus on people mentioned in recent articles. "
            "Return ONLY valid JSON. "
            "Format: {'people': [{'rank': 1, 'name_en': 'English Name', 'name_kr': 'Korean Name'}]}"
        )
        
        try:
            raw_text = self._call_perplexity_text(prompt)
            parsed_data = self._clean_and_parse_json(raw_text)
            
            if "people" in parsed_data and len(parsed_data["people"]) > 0:
                return json.dumps(parsed_data)
            else:
                print(f"   > ⚠️ AI returned empty data. Raw text: {raw_text[:50]}...")
                return "{}"
        except Exception as e:
            print(f"   > ⚠️ Search Failed: {e}")
            return "{}"

    # ---------------------------------------------------------
    # [Step 2] 쿨타임 (Pass)
    # ---------------------------------------------------------
    def is_in_cooldown(self, name):
        return False

    def update_history(self, name, category):
        pass

    # ---------------------------------------------------------
    # [Step 3] 뉴스 팩트 체크 (네이버 뉴스 전용)
    # ---------------------------------------------------------
    def fetch_article_details(self, name_kr, name_en, category, rank):
        print(f"    🔍 Searching facts for: {name_kr}...")
        
        if not self.pplx_api_key:
            return "NO NEWS FOUND (API Key Missing)"

        # [수정됨] site:news.naver.com 조건 추가
        prompt = (
            f"Search ONLY on site:news.naver.com for the latest news (last 24 hours) about {name_kr} ({category}). "
            "Summarize the key facts found in Naver News articles in 3 sentences. "
            "If no articles are found on Naver News, explicitly say 'NO NEWS FOUND'."
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
    # [Step 4] 기사 작성 (Groq)
    # ---------------------------------------------------------
    def edit_with_groq(self, name, facts, category):
        if "NO NEWS FOUND" in facts or "Failed" in facts:
            return "Headline: Error\nNO NEWS FOUND"

        prompt = f"""
        You are a K-Culture journalist. Write a short news article.
        
        Target: {name} ({category})
        Facts from Naver News: {facts}
        
        Format:
        Headline: [Catchy English Title]
        [Body text in English]
        ###SCORE: [0-100]
        """
        try:
            completion = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
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
