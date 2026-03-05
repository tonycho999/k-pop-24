import os
import time
import json
import requests
from bs4 import BeautifulSoup
from collections import Counter
from groq import Groq
from database import Database
from datetime import datetime

class NaverTrendEngine:
    def __init__(self, db: Database):
        self.db = db
        self.naver_client_id = os.environ.get("NAVER_CLIENT_ID")
        self.naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        
        self.groq_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key: self.groq_keys.append(key)

    def _call_groq_with_fallback(self, prompt, temperature=0.2):
        if not self.groq_keys: return None
        total_keys = len(self.groq_keys)
        start_index = self.db.get_groq_index() % total_keys
        
        for offset in range(total_keys):
            current_index = (start_index + offset) % total_keys
            current_key = self.groq_keys[current_index]
            try:
                client = Groq(api_key=current_key)
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile", 
                    temperature=temperature
                )
                if offset > 0: self.db.update_groq_index(current_index)
                return chat_completion.choices[0].message.content.strip()
            except Exception:
                time.sleep(1)
        return None

    def get_target_10_people(self, category_keyword, exclude_names):
        """중복(exclude_names) 제외하고 새로운 타겟 10명만 추출"""
        if not self.naver_client_id: return []
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_client_id, "X-Naver-Client-Secret": self.naver_client_secret}
        params = {"query": category_keyword, "display": 100, "sort": "date"}
        
        try:
            res = requests.get(url, headers=headers, params=params, timeout=15)
            news_items = res.json().get("items", [])
            
            combined_text = ""
            for item in news_items:
                title = BeautifulSoup(item['title'], 'html.parser').text
                desc = BeautifulSoup(item['description'], 'html.parser').text
                combined_text += f"- {title}: {desc}\n"

            prompt = f"Extract ONLY HUMAN NAMES (Korean celebrities/figures) from the text: {combined_text[:12000]}\nRules: Extract up to 50 names. Output strictly as JSON array of strings: [\"Name1\", \"Name2\"]"
            
            result_text = self._call_groq_with_fallback(prompt, temperature=0.1)
            if not result_text: return []
            
            if result_text.startswith("```"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
                
            extracted_names = json.loads(result_text)
            name_counts = Counter(extracted_names)
            sorted_all_names = [name for name, count in name_counts.most_common()]
            
            # DB에 이미 있는 50명 제외
            filtered_names = [name for name in sorted_all_names if name not in exclude_names]
            return filtered_names[:10]

        except Exception as e:
            return []

    def process_person(self, person_name, time_context):
        """기사 분석 및 평점(Score) 부여"""
        url = "[https://openapi.naver.com/v1/search/news.json](https://openapi.naver.com/v1/search/news.json)"
        headers = {"X-Naver-Client-Id": self.naver_client_id, "X-Naver-Client-Secret": self.naver_client_secret}
        params = {"query": person_name, "display": 10, "sort": "date"}
        
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            items = res.json().get("items", [])
            
            article_texts = []
            first_link = ""
            for item in items:
                link = item['link']
                if link.startswith("[https://n.news.naver.com](https://n.news.naver.com)"):
                    if not first_link: first_link = link
                    res_body = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                    soup = BeautifulSoup(res_body.text, 'html.parser')
                    dic_area = soup.select_one('#dic_area')
                    if dic_area: article_texts.append(dic_area.text.strip())
                if len(article_texts) >= 3: break
                
            if not article_texts: return None
                
            combined_articles = "\n\n".join(article_texts)
            
            prompt = f"""
            Persona: You are a sharp Entertainment News Chief Editor.
            Time Context: {time_context} (Reflect this time of day in your tone naturally).
            
            Articles about '{person_name}': {combined_articles[:10000]}
            
            Task:
            1. Create a catchy headline: "제목 [ {person_name} ] (Headline)"
            2. Write a 3-sentence engaging summary.
            3. Evaluate the 'Hotness Score' (평점) from 1 to 100 based on how impactful or scandalous this news is (100 = massive breaking news/scandal, 50 = normal update).
            4. Output STRICTLY as JSON.
            
            Format:
            {{ "title": "...", "summary": "...", "score": 85 }}
            """
            
            print(f"  > Analyzing impact & generating article for: {person_name}")
            result_text = self._call_groq_with_fallback(prompt, temperature=0.5)
            if not result_text: return None
            
            if result_text.startswith("```"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            summary_data = json.loads(result_text)
            summary_data['name'] = person_name
            summary_data['link'] = first_link 
            
            # AI가 점수를 안 줬을 경우를 대비한 안전장치
            if 'score' not in summary_data or not isinstance(summary_data['score'], int):
                summary_data['score'] = 50 
                
            return summary_data
            
        except Exception as e:
            return None
