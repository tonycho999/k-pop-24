import os
import time
import json
import requests
import pytz
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from google import genai
from google.genai import types

from database import Database
from model_manager import ModelManager

class NaverTrendEngine:
    def __init__(self, db: Database):
        self.db = db
        self.naver_client_id = os.environ.get("NAVER_CLIENT_ID")
        self.naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        
        # 💡 [핵심] main.py에 있던 상세 검색 키워드가 이쪽으로 이사 왔습니다.
        self.category_keywords = {
            "k-actor": "영화배우 | 탤런트 | 드라마 캐스팅",
            "k-pop": "걸그룹 | 보이그룹 | 아이돌 | 가요계",
            "k-entertain": "예능인 | 방송인 | 코미디언 | 예능 출연",
            "k-culture": "MZ세대 | 팝업스토어 | 품절대란 | SNS 화제 | 밈"
        }
        
        # 💡 프록시 설정은 뉴스 본문 스크래핑이 없어졌으므로 영구 삭제했습니다.
        
        self.gemini_key = os.environ.get("GEMINI_API_KEY")

        if self.gemini_key:
            temp_client = genai.Client(api_key=self.gemini_key)
            manager = ModelManager(client=temp_client, provider="gemini")
            self.model_name = manager.get_best_model()
            if not self.model_name:
                self.model_name = "gemini-2.5-flash"
        else:
            self.model_name = None

    def _call_gemini_with_fallback(self, prompt, temperature=0.0):
        if not self.gemini_key or not self.model_name: 
            return None
        try:
            client = genai.Client(api_key=self.gemini_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"  ⚠️ Gemini Error: {e}")
            return None

    def _get_naver_image(self, query, used_image_urls):
        if not self.naver_client_id: return ""
        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": self.naver_client_id,
            "X-Naver-Client-Secret": self.naver_client_secret
        }
        params = {"query": query, "display": 5, "sort": "sim", "filter": "large"}
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            data = res.json()
            items = data.get("items", [])
            for item in items:
                img_link = item.get("link")
                if img_link and img_link not in used_image_urls:
                    print(f"  📸 [Naver Image] Successfully fetched exclusive image for '{query}'!")
                    return img_link
        except Exception as e:
            pass
        return ""

    def get_target_people(self, category, exclude_names):
        if not self.naver_client_id: return []
        
        # 💡 딕셔너리에서 해당 부서의 검색 키워드를 꺼내옵니다.
        search_keyword = self.category_keywords.get(category, "")
        if not search_keyword: return []

        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_client_id, "X-Naver-Client-Secret": self.naver_client_secret}
        params = {"query": search_keyword, "display": 100, "sort": "date"}
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            res.raise_for_status()
            news_items = res.json().get("items", [])
            now_utc = datetime.now(timezone.utc)
            combined_text = ""
            
            for item in news_items:
                pub_date = parsedate_to_datetime(item['pubDate'])
                if now_utc - pub_date > timedelta(hours=24): continue 
                title = BeautifulSoup(item['title'], 'html.parser').text
                desc = BeautifulSoup(item['description'], 'html.parser').text
                combined_text += f"- {title}: {desc}\n"

            if not combined_text: return []
            
            # 💡 [핵심] 사람 이름만 뽑아내는 초강력 룰 적용
            rule = ""
            if category == "k-actor": 
                rule = "MUST extract REAL ACTOR NAMES (Human names) ONLY. Strictly exclude movie titles and character names."
            elif category == "k-pop": 
                rule = "MUST extract SINGER or IDOL GROUP NAMES ONLY. Strictly exclude fan club names (e.g., '영웅시대') and generic words."
            elif category == "k-entertain": 
                rule = "MUST extract REAL ENTERTAINERS, COMEDIANS, or CAST MEMBERS (Human names) ONLY. STRICTLY EXCLUDE TV show titles, episode missions, and generic terms like '가구 시청률'."
            elif category == "k-culture": 
                rule = "Extract SPECIFIC VIRAL TRENDS, FOODS, MEMES, or HOT PLACES ONLY. Exclude generic words like '문화', '트렌드'."

            prompt = f"""
            Extract the 10 most frequently mentioned SUBJECTS from the text below:
            {combined_text[:12000]}
            
            CRITICAL RULES:
            1. {rule}
            2. For k-actor, k-pop, and k-entertain: If it is NOT a real human name or group name, DO NOT extract it.
            3. COMBINE duplicates (e.g., merge '임영웅' and '가수 임영웅' into just '임영웅').
            4. Output strictly as a JSON array of strings like: ["Name1", "Name2"]
            """
            
            result_text = self._call_gemini_with_fallback(prompt, temperature=0.0)
            if not result_text: return []
            
            extracted_names = json.loads(result_text)
            name_counts = Counter(extracted_names)
            sorted_all_names = [name for name, count in name_counts.most_common()]
            filtered_names = [name for name in sorted_all_names if name not in exclude_names]
            
            return filtered_names[:10]

        except Exception as e:
            print(f"❌ Error extracting targets: {e}")
            return []

    def process_person(self, person_name, time_context, used_image_urls, category):
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
                pub_date = parsedate_to_datetime(item['pubDate'])
                if now_utc - pub_date > timedelta(hours=24): continue 
                
                if not first_link: first_link = item['link']
                
                title = BeautifulSoup(item['title'], 'html.parser').text
                desc = BeautifulSoup(item['description'], 'html.parser').text
                article_texts.append(f"Title: {title}\nSummary: {desc}")
                
                if len(article_texts) >= 3: break 
                
            if not article_texts: return None

            search_query = f"{person_name} 프로필" if category in ['k-actor', 'k-pop', 'k-entertain'] else f"{person_name}"
            print(f"  🔍 Searching Naver Image for exclusive photo: {person_name}")
            first_image = self._get_naver_image(search_query, used_image_urls)
                
            if first_image:
                used_image_urls.add(first_image)
                
            combined_articles = "\n\n".join(article_texts)
            
            prompt = f"""
            Current Time in Korea: {now_kst}
            Target Subject: '{person_name}'
            Recent News Summaries (from Naver API):
            {combined_articles}
            
            Task:
            1. Summary: Summarize the FACTS based strictly on the provided text. DO NOT add your own opinions, expert analysis, or extra comments.
            2. Exact Match: Keep all numbers (viewers, ratings, sales) and proper nouns EXACTLY as they appear in the original text.
            3. Headline: Create an English headline starting with the subject's name in brackets. Example: "[{person_name}] Headline Here".
            4. Hotness Score (1-100): Evaluate the trend impact. Give HIGH scores (80-100) for huge hits, major scandals, or mega viral crazes.
            
            Format: Output ONLY valid JSON matching this structure:
            {{ "category": "{category}", "title": "[{person_name}] English Headline...", "summary": "Factual English summary...", "score": 95 }}
            """
            
            print(f"  > AI Editor is extracting facts for: {person_name}")
            result_text = self._call_gemini_with_fallback(prompt, temperature=0.0) 
            if not result_text: return None
            
            summary_data = json.loads(result_text)
            summary_data['name'] = person_name
            summary_data['link'] = first_link 
            summary_data['image_url'] = first_image
            if 'score' not in summary_data: summary_data['score'] = 50 
                
            return summary_data
        except Exception as e:
            print(f"❌ Error processing {person_name}: {e}")
            return None
