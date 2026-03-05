import os
import time
import json
import requests
import re
from bs4 import BeautifulSoup
from collections import Counter
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

    # ==========================================
    # ★ 대표님 코드 이식: 강력한 네이버 본문 추출기
    # ==========================================
    def _scrape_article_full(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 대표님의 완벽한 다중 셀렉터 적용 (연예, 스포츠, 일반 뉴스 모두 커버)
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
            return "" # 못 찾으면 깔끔하게 포기
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
            
            filtered_names = [name for name in sorted_all_names if name not in exclude_names]
            return filtered_names[:10]

        except Exception as e:
            print(f"❌ Error extracting people: {e}")
            return []

    def process_person(self, person_name, time_context):
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
                if not first_link: first_link = link
                
                # 1. 일단 대표님 로직으로 본문 전체 크롤링 시도
                full_text = self._scrape_article_full(link)
                
                if full_text and len(full_text) > 100:
                    # 크롤링 성공 시 본문 텍스트 채택
                    article_texts.append(f"[본문수집 성공] {full_text}")
                else:
                    # 2. 크롤링 실패 시, 버리지 않고 API 요약문(description)으로 안전하게 땜빵
                    desc = BeautifulSoup(item['description'], 'html.parser').text
                    article_texts.append(f"[API요약 땜빵] {desc}")
                
                # 기사 3개 분량 수집하면 스톱
                if len(article_texts) >= 3: break
                
            if not article_texts: return None
                
            combined_articles = "\n\n".join(article_texts)
            
            prompt = f"""
            Persona: You are a sharp Entertainment News Chief Editor.
            Time Context: {time_context} (Reflect this time of day in your tone naturally).
            
            News about '{person_name}': {combined_articles[:10000]}
            
            Task:
            1. Create a catchy headline: "제목 [ {person_name} ] (Headline)"
            2. Write a 3-sentence engaging summary in Korean based on the news above.
            3. Evaluate the 'Hotness Score' (평점) from 1 to 100 based on how impactful or scandalous this news is.
            4. Output STRICTLY as JSON.
            
            Format:
            {{ "title": "...", "summary": "...", "score": 85 }}
            """
            
            print(f"  > Writing article for: {person_name}")
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
