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

# 💡 [핵심] 구글 신형 SDK 규격 적용
from google import genai
from google.genai import types

from database import Database
from model_manager import ModelManager

class NaverTrendEngine:
    def __init__(self, db: Database):
        self.db = db
        self.naver_client_id = os.environ.get("NAVER_CLIENT_ID")
        self.naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET")
        
        self.google_api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
        self.google_cx = os.environ.get("GOOGLE_SEARCH_CX")
        
        self.proxy_host = os.environ.get("PROXY_HOST", "unblocker.iproyal.com")
        self.proxy_port = os.environ.get("PROXY_PORT", "12323")
        self.proxy_user = os.environ.get("PROXY_USER")
        self.proxy_pass = os.environ.get("PROXY_PASS")
        
        if self.proxy_user and self.proxy_pass:
            self.proxies = {
                "http": f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}",
                "https": f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}"
            }
        else:
            self.proxies = None
        
        self.gemini_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GEMINI_API_KEY{i}")
            if key: self.gemini_keys.append(key)

        if self.gemini_keys:
            temp_client = genai.Client(api_key=self.gemini_keys[0])
            manager = ModelManager(client=temp_client, provider="gemini")
            self.model_name = manager.get_best_model()
            if not self.model_name:
                self.model_name = "gemini-2.5-flash"
        else:
            self.model_name = None

    def _call_gemini_with_fallback(self, prompt, temperature=0.2):
        if not self.gemini_keys or not self.model_name: 
            print("❌ No Gemini keys or model available!")
            return None
            
        total_keys = len(self.gemini_keys)
        current_run_count = self.db.get_groq_index()
        
        for offset in range(total_keys):
            key_index = current_run_count % total_keys
            current_key = self.gemini_keys[key_index]
            
            try:
                # 💡 구글 신형 SDK 규격 호출
                client = genai.Client(api_key=current_key)
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type="application/json",
                    )
                )
                
                current_run_count += 1
                self.db.update_groq_index(current_run_count)
                
                return response.text.strip()
                
            except Exception as e:
                print(f"  ⚠️ Gemini Error (Key #{key_index+1}): {e}. Switching to next key...")
                current_run_count += 1
                self.db.update_groq_index(current_run_count)
                time.sleep(1)
                
        print("❌ All Gemini API Keys failed.")
        return None

    def _get_google_image(self, query):
        if not self.google_api_key or not self.google_cx:
            return ""
            
        url = "https://customsearch.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cx,
            "q": query,
            "searchType": "image",
            "num": 1 
        }
        
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            if "items" in data and len(data["items"]) > 0:
                print("  📸 [이미지 성공] 구글에서 이미지를 퍼왔습니다!")
                return data["items"][0]["link"]
        except Exception as e:
            print(f"  ⚠️ Google Image Search Error: {e}")
        return ""

    def _scrape_article_full(self, url):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            res = None
            if self.proxies:
                try:
                    res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=10)
                except: pass
            
            if not res or res.status_code != 200:
                res = requests.get(url, headers=headers, verify=False, timeout=10)
                
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            image_url = ""
            og_img = soup.select_one('meta[property="og:image"], meta[name="og:image"]')
            if og_img and og_img.get('content'):
                image_url = str(og_img.get('content')).strip()
            
            if not image_url:
                for img_tag in soup.find_all('img'):
                    src = img_tag.get('data-src') or img_tag.get('src')
                    if src:
                        src = str(src).strip()
                        if "logo" not in src.lower() and "icon" not in src.lower() and "btn" not in src.lower():
                            if src.startswith("http") or src.startswith("//"):
                                image_url = src
                                break
            
            if image_url:
                if image_url.startswith("//"):
                    image_url = "https:" + image_url
                elif image_url.startswith("http://"):
                    image_url = image_url.replace("http://", "https://")

            content_area = soup.select_one('#dic_area, #newsct_article, #artc_body, #newsEndContents')
            
            if content_area:
                raw_text = content_area.get_text(separator='\n', strip=True)
                lines = raw_text.split('\n')
                blacklist = ['구독되었습니다', 'Copyright', '무단 전재', '재배포 금지']
                clean_lines = [line.strip() for line in lines if len(line.strip()) >= 20 and not any(bad in line for bad in blacklist)]
                return " ".join(clean_lines), image_url
            return "", image_url 
        except:
            return "", ""

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
                pub_date = parsedate_to_datetime(item['pubDate'])
                if now_utc - pub_date > timedelta(hours=24):
                    continue
                    
                title = BeautifulSoup(item['title'], 'html.parser').text
                desc = BeautifulSoup(item['description'], 'html.parser').text
                combined_text += f"- {title}: {desc}\n"

            if not combined_text:
                return []

            prompt = f"Extract ONLY HUMAN NAMES (Korean celebrities/figures) from the text: {combined_text[:12000]}\nRules: Extract up to 50 names. Output strictly as JSON array of strings like: [\"Name1\", \"Name2\"]"
            
            result_text = self._call_gemini_with_fallback(prompt, temperature=0.1)
            if not result_text: return []
            
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
            first_image = ""
            
            for item in items:
                pub_date = parsedate_to_datetime(item['pubDate'])
                if now_utc - pub_date > timedelta(hours=24): continue
                    
                link = item['link']
                if not first_link: first_link = link
                
                full_text, img_url = self._scrape_article_full(link)
                
                if img_url and not first_image:
                    first_image = img_url
                
                if full_text and len(full_text) > 100:
                    article_texts.append(f"[본문수집 성공] {full_text}")
                else:
                    desc = BeautifulSoup(item['description'], 'html.parser').text
                    article_texts.append(f"[API요약 땜빵] {desc}")
                
                if len(article_texts) >= 3: break
                
            if not article_texts: return None

            if not first_image:
                print(f"  ⚠️ 네이버 이미지 실패. 구글 검색 작동: {person_name}")
                first_image = self._get_google_image(f"{person_name} 연예인")
                
            combined_articles = "\n\n".join(article_texts)
            
            prompt = f"""
            Persona: You are a sharp Entertainment News Chief Editor.
            Current Time in Korea: {now_kst}
            Time Context: {time_context}
            Recent News about '{person_name}': {combined_articles[:10000]}
            
            Task:
            1. Write a 3-sentence engaging summary based on the news above.
            2. Create a catchy headline.
            3. TRANSLATE BOTH the headline and the summary into ENGLISH.
            4. Evaluate the 'Hotness Score' from 1 to 100.
            
            Format: Output ONLY valid JSON matching this structure:
            {{ "title": "English Headline", "summary": "English summary...", "score": 85 }}
            """
            
            print(f"  > Writing & Translating article for: {person_name}")
            result_text = self._call_gemini_with_fallback(prompt, temperature=0.5)
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
