import os
import json
import requests
import pytz
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import urllib.parse
from groq import Groq

from model_manager import ModelManager 

class ChartEngine:
    def __init__(self, db):
        self.db = db
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

        # 프록시 설정
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

        # Groq 설정
        self.groq_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key: self.groq_keys.append(key)

        if self.groq_keys:
            self.groq_client = Groq(api_key=self.groq_keys[0])
            manager = ModelManager(client=self.groq_client, provider="groq")
            best_model_name = manager.get_best_model()
            self.model_name = best_model_name if best_model_name else "llama-3.3-70b-versatile"
        else:
            self.groq_client = None
            self.model_name = None

    def get_top10_chart(self, category):
        print(f"\n📊 --- Processing {category} (ABSOLUTE LATEST) ---", flush=True)

        if category == "k-movie":
            raw_context = self._get_kobis_data()
            source_type = "Official KOBIS Daily Box Office"
        elif category == "k-pop":
            raw_context = self._scrape_bugs_realtime()
            source_type = "Bugs Music REAL-TIME Chart"
        elif category == "k-drama":
            raw_context = self._scrape_naver_ratings("현재 방영중 드라마 시청률 순위")
            source_type = "Naver Latest Drama Ratings"
        elif category == "k-entertain":
            raw_context = self._scrape_naver_ratings("현재 방영중 예능 시청률 순위")
            source_type = "Naver Latest Entertain Ratings"
        elif category == "k-culture":
            raw_context = self._scrape_naver_blogs("요즘 가장 뜨는 핫플레이스")
            source_type = "Naver Latest Trending Places"
        else:
            raw_context = None
            source_type = "Unknown"

        if not raw_context:
            print(f"⚠️ [Skip] Valid real-time data not found for {category}.", flush=True)
            return json.dumps({"top10": []})

        return self._process_with_groq(category, context=raw_context, source_type=source_type)

    def _get_kobis_data(self):
        if not self.kobis_key: 
            print("  ❌ KOBIS_API_KEY is missing!")
            return None
        
        korea_tz = pytz.timezone('Asia/Seoul')
        kst_now = datetime.now(korea_tz)
        yesterday = (kst_now - timedelta(days=1)).strftime("%Y%m%d")
        
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={yesterday}"
        try:
            res = requests.get(url, timeout=15)
            res.raise_for_status()
            box_office_list = res.json().get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
            if not box_office_list: 
                print("  ❌ KOBIS API returned empty list.")
                return None
            context = ""
            for movie in box_office_list:
                context += f"- Rank {movie['rank']}: {movie['movieNm']} (Audiences: {movie['audiCnt']})\n"
            return context
        except Exception as e:
            print(f"  ❌ KOBIS Error: {e}")
            return None

    # 💡 [핵심] 프록시 실패 시 즉각 다이렉트 통신으로 우회하는 무적 로직
    def _fetch_html_with_fallback(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        try:
            if self.proxies:
                res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=15)
                if res.status_code == 200:
                    return res.text
                else:
                    print(f"  ⚠️ Proxy returned {res.status_code}. Retrying directly...")
            
            # 프록시가 아예 없거나 실패했을 때 최후의 수단으로 다이렉트 접속 시도
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            return res.text
        except Exception as e:
            print(f"  ❌ Fetch Error for {url}: {e}")
            return None

    # 💡 [핵심] 깐깐한 HTML 태그 찾기를 버리고 화면 전체 텍스트를 AI에게 던짐
    def _scrape_bugs_realtime(self):
        url = "https://music.bugs.co.kr/chart"
        html = self._fetch_html_with_fallback(url)
        if not html: return None
        
        soup = BeautifulSoup(html, 'html.parser')
        chart = soup.select_one('table.list')
        if chart:
            return chart.get_text(separator=' | ', strip=True)[:10000]
        return soup.get_text(separator=' | ', strip=True)[:10000]

    def _scrape_naver_ratings(self, query):
        url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}"
        html = self._fetch_html_with_fallback(url)
        if not html: return None
        
        soup = BeautifulSoup(html, 'html.parser')
        main_pack = soup.select_one('#main_pack')
        if main_pack:
            return main_pack.get_text(separator=' | ', strip=True)[:10000]
        return soup.get_text(separator=' | ', strip=True)[:10000]

    def _scrape_naver_blogs(self, query):
        url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}"
        html = self._fetch_html_with_fallback(url)
        if not html: return None
        
        soup = BeautifulSoup(html, 'html.parser')
        main_pack = soup.select_one('#main_pack')
        if main_pack:
            return main_pack.get_text(separator=' | ', strip=True)[:10000]
        return soup.get_text(separator=' | ', strip=True)[:10000]

    def _process_with_groq(self, category, context, source_type):
        if not self.groq_keys or not self.model_name:
            return json.dumps({"top10": []})

        korea_tz = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S KST')
        
        prompt = f"""
        Current Time in Korea: {now_kst}.
        Task: Create a Top 10 ranking chart for '{category}' based ABSOLUTELY ONLY on the provided source text.
        
        Source Data ({source_type}):
        {context}
        
        CRITICAL RULES:
        1. DO NOT HALLUCINATE OR INVENT DATA. Use ONLY the data provided above.
        2. Extract up to 10 items. If the data is messy, logically deduce the top items.
        3. Translate all Korean titles naturally into English.
        4. 'info' should be a concise 1-sentence description (e.g., exact ratings or artist name).
        5. Output STRICTLY as a valid JSON object.
        
        Required Format:
        {{ "top10": [ {{ "rank": 1, "title": "English Title", "info": "Brief description" }} ] }}
        """

        total_keys = len(self.groq_keys)
        current_run_count = self.db.get_groq_index()
        
        for offset in range(total_keys):
            key_index = current_run_count % total_keys
            current_key = self.groq_keys[key_index]
            
            try:
                print(f"  > Sending factual real-time data to Groq API (Key #{key_index + 1})...", flush=True)
                client = Groq(api_key=current_key)
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a strict data parser. Output nothing but JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.model_name,
                    temperature=0.0, 
                )
                
                current_run_count += 1
                self.db.update_groq_index(current_run_count)

                content = chat_completion.choices[0].message.content.strip()
                if content.startswith("```"):
                    content = content.replace("```json", "").replace("```", "").strip()
                return content

            except Exception as e:
                print(f"  ⚠️ Groq Error on Key #{key_index + 1}: {e}. Switching to next key...", flush=True)
                current_run_count += 1
                self.db.update_groq_index(current_run_count)
                time.sleep(1)
                
        print("❌ All Groq API Keys failed.", flush=True)
        return json.dumps({"top10": []})
