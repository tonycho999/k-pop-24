import os
import time
import json
import requests
import re
import pytz
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from groq import Groq
from database import Database

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
        if not self.groq_keys: 
            print("❌ No Groq keys available!")
            return None
            
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
            except Exception as e:
                print(f"  ⚠️ Groq Error (Key #{current_index+1}): {e}")
                time.sleep(1)
        return None

    def _scrape_article_full(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            content_area = soup.select_one('#dic_area, #newsct_article, #artc_body, #newsEndContents, [itemprop="articleBody"]')
            
            if content_area:
                raw_text = content_area.get_text(separator='\n', strip=True)
                lines = raw_text.split('\n')
                blacklist = ['구독되었습니다', 'Copyright', '무단 전재', '재배포 금지', '기자의 다른 기사', '섹션 정보']
                clean_lines = []
                
                for line in lines:
                    line = line.strip()
                    if len(line) < 20: continue 
                    if any(bad in line for bad in blacklist): continue 
                    clean_lines.append(line)
                    
                return " ".join(clean_lines)
            return ""
        except:
            return ""

    def get_target_10_people(self, category_keyword, exclude_names):
        if not self.naver_client_id: return []
            
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_client_id, "X-Naver-Client-Secret": self.naver_client_secret}
        params = {"query": category_keyword, "display": 100, "sort": "date"}
        
        try:
            res = requests.get(url, headers=headers, params=params, timeout=15)
            res.raise_for_status()
            news_items = res.json().get("items", [])
            
            now_utc = datetime.now(timezone.utc)
            combined_text = ""
            
            for item in news_items:
                # ★ 1차 방어: 24시간 이내 기사만 수집 (오래된 기사 차단)
                pub_date = parsedate_to_datetime(item['pubDate'])
                if now_utc - pub_date > timedelta(hours=24):
                    continue
                    
                title = BeautifulSoup(item['title'], 'html.parser').text
                desc = BeautifulSoup(item['description'], 'html.parser').text
                combined_text += f"- {title}: {desc}\n"

            if not combined_text:
                print(f"  ⚠️ No articles within the last 24 hours for '{category_keyword}'.")
                return []

            prompt = f"Extract ONLY HUMAN NAMES (Korean celebrities/figures) from the text: {combined_text[:12000]}\nRules: Extract up to 50 names. Output strictly as JSON array of strings: [\"Name1\", \"Name2\"]"
            
            result_text = self._call_groq_with_fallback(prompt, temperature=0.1)
            if not result_text: return []
            
            if result_text.startswith("```"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
                
            extracted_names = json.loads(result_text)
            name_counts = Counter(extracted_names)
            sorted_all_names = [name for name, count in name_counts.most_common()]
            
            filtered_names = [name for name in sorted_all_names if name not in exclude_names]
            return filtered_names[:10]

        except Exception as e:
            print(f"❌ Error extracting people: {e}")
            return []

    def process_person(self, person_name, time_context):
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_client_id, "X-Naver-Client-Secret": self.naver_client_secret}
        params = {"query": person_name, "display": 15, "sort": "date"}
        
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            items = res.json().get("items", [])
            
            now_utc = datetime.now(timezone.utc)
            korea_tz = pytz.timezone('Asia/Seoul')
            now_kst = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S KST')
            
            article_texts = []
            first_link = ""
            
            for item in items:
                # ★ 2차 방어: 인물 개별 기사에서도 24시간 초과 기사는 버림
                pub_date = parsedate_to_datetime(item['pubDate'])
                if now_utc - pub_date > timedelta(hours=24):
                    continue
                    
                link = item['link']
                if not first_link: first_link = link
                
                full_text = self._scrape_article_full(link)
                
                if full_text and len(full_text) > 100:
                    article_texts.append(f"[본문수집 성공] {full_text}")
                else:
                    desc = BeautifulSoup(item['description'], 'html.parser').text
                    article_texts.append(f"[API요약 땜빵] {desc}")
                
                if len(article_texts) >= 3: break
                
            if not article_texts:
                print(f"  ⚠️ No recent articles (<24h) found for: {person_name}")
                return None
                
            combined_articles = "\n\n".join(article_texts)
            
            # ★ 3차: 한국 시간 주입 및 '영문 번역' 지시 프롬프트
            prompt = f"""
            Persona: You are a sharp Entertainment News Chief Editor.
            Current Time in Korea: {now_kst}
            Time Context: {time_context}
            
            Recent News about '{person_name}': {combined_articles[:10000]}
            
            Task:
            1. Write a 3-sentence engaging summary based on the news above.
            2. Create a catchy headline.
            3. TRANSLATE BOTH the headline and the summary into ENGLISH. Your final output must be completely in English.
            4. Evaluate the 'Hotness Score' (평점) from 1 to 100.
            5. Output STRICTLY as JSON.
            
            Format:
            {{ "title": "[ English Headline ]", "summary": "English summary...", "score": 85 }}
            """
            
            print(f"  > Writing & Translating article for: {person_name}")
            result_text = self._call_groq_with_fallback(prompt, temperature=0.5)
            if not result_text: return None
            
            if result_text.startswith("```"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            summary_data = json.loads(result_text)
            summary_data['name'] = person_name
            summary_data['link'] = first_link 
            if 'score' not in summary_data: summary_data['score'] = 50 
                
            return summary_data
            
        except Exception as e:
            print(f"❌ Error processing {person_name}: {e}")
            return None
