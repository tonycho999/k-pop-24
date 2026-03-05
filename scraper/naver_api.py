import os
import time
import json
import requests
from bs4 import BeautifulSoup
from collections import Counter
from groq import Groq
from database import Database

class NaverTrendEngine:
    def __init__(self, db: Database):
        self.db = db
        
        # 네이버 API 세팅
        self.naver_client_id = os.environ.get("NAVER_CLIENT_ID")
        self.naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        
        # Groq 키 수집 (GROQ_API_KEY1 ~ GROQ_API_KEY8)
        self.groq_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key: self.groq_keys.append(key)

        if not self.groq_keys:
            print("❌ CRITICAL: No GROQ_API_KEYs found!")
            
    # ==========================================
    # 🚀 Groq 에러 발생 시 "다음 키로 릴레이" 하는 핵심 함수
    # ==========================================
    def _call_groq_with_fallback(self, prompt, temperature=0.2):
        if not self.groq_keys: return None
        
        # 1. DB에서 현재 몇 번째 키를 써야 할지 가져옴
        total_keys = len(self.groq_keys)
        start_index = self.db.get_groq_index() % total_keys
        
        # 2. 현재 키부터 시작해서, 실패하면 다음 키로 넘어가며 최대 보유 키 개수만큼 재시도
        for offset in range(total_keys):
            current_index = (start_index + offset) % total_keys
            current_key = self.groq_keys[current_index]
            
            print(f"  > Trying Groq API with Key #{current_index + 1}...")
            try:
                client = Groq(api_key=current_key)
                # 속도와 가성비가 가장 좋은 8b 또는 70b 모델 하드코딩 (안정성 확보)
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile", 
                    temperature=temperature
                )
                
                # 성공했다면! 만약 키 번호가 바뀌었다면 DB에 업데이트
                if offset > 0:
                    self.db.update_groq_index(current_index)
                
                return chat_completion.choices[0].message.content.strip()
                
            except Exception as e:
                print(f"  ⚠️ Groq Key #{current_index + 1} Failed: {e}. Switching to next key...")
                time.sleep(1) # 에러 시 1초 대기 후 다음 키 시도
                
        print("❌ All Groq API Keys failed or exhausted limits.")
        return None

    # ==========================================
    # STEP 1: 기사 100개 수집 및 인물 30명 추출
    # ==========================================
    def get_top_30_people(self, category_keyword):
        if not self.naver_client_id: return []

        print(f"\n🔍 [STEP 1] Fetching recent news for '{category_keyword}'...")
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

            print(f"🤖 [STEP 2] Asking Groq to extract Top 30 human names...")
            prompt = f"""
            Task: Extract ONLY HUMAN NAMES (Korean celebrities, actors, singers) from the text.
            Text: {combined_text[:12000]}
            Rules: Return STRICTLY as a JSON array of strings. Format: ["Name1", "Name2"]
            """
            
            result_text = self._call_groq_with_fallback(prompt, temperature=0.1)
            if not result_text: return []
            
            if result_text.startswith("```"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
                
            extracted_names = json.loads(result_text)
            name_counts = Counter(extracted_names)
            return [name for name, count in name_counts.most_common(30)]

        except Exception as e:
            print(f"❌ Error extracting people: {e}")
            return []

    # ==========================================
    # STEP 2 & 3: 인물별 기사 수집 및 요약
    # ==========================================
    def process_person(self, person_name, rank_idx):
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
                    # 본문 스크래핑 (IPRoyal 없이 쌩 requests)
                    res_body = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                    soup = BeautifulSoup(res_body.text, 'html.parser')
                    dic_area = soup.select_one('#dic_area')
                    if dic_area:
                        article_texts.append(dic_area.text.strip())
                if len(article_texts) >= 3: break
                
            if not article_texts:
                return None
                
            combined_articles = "\n\n".join(article_texts)
            prompt = f"""
            Task: Summarize why '{person_name}' is currently in the news.
            Articles: {combined_articles[:10000]}
            Rules:
            1. Create a catchy title: "제목 [ {person_name} ] (Headline here)"
            2. Write a 3-sentence summary in Korean.
            3. Output strictly JSON.
            Format: {{ "title": "...", "summary": "..." }}
            """
            
            print(f"  > Generating summary for 1위~30위 중 {rank_idx}위: {person_name}")
            result_text = self._call_groq_with_fallback(prompt, temperature=0.3)
            if not result_text: return None
            
            if result_text.startswith("```"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            summary_data = json.loads(result_text)
            summary_data['name'] = person_name
            summary_data['rank'] = rank_idx
            summary_data['link'] = first_link # DB 저장을 위해 뉴스 링크 하나 확보
            return summary_data
            
        except Exception as e:
            print(f"❌ Processing failed for {person_name}: {e}")
            return None
