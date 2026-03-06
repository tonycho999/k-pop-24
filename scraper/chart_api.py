import os
import json
import requests
import time
import pytz
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import urllib.parse
from groq import Groq

from model_manager import ModelManager 

class ChartEngine:
    def __init__(self, db):
        self.db = db
        
        self.kobis_key = os.environ.get("KOBIS_API_KEY")

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

        self.groq_keys = []
        for i in range(1, 9):
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key: self.groq_keys.append(key)

        if self.groq_keys:
            temp_client = Groq(api_key=self.groq_keys[0])
            manager = ModelManager(client=temp_client, provider="groq")
            best_model_name = manager.get_best_model()
            self.model_name = best_model_name if best_model_name else "llama-3.3-70b-versatile"
        else:
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
        if not self.kobis_key: return None
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        url = f"http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json?key={self.kobis_key}&targetDt={yesterday}"
        try:
            res = requests.get(url, timeout=15)
            box_office_list = res.json().get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
            if not box_office_list: return None
            context = ""
            for movie in box_office_list:
                context += f"- Rank {movie['rank']}: {movie['movieNm']} (Audiences: {movie['audiCnt']})\n"
            return context
        except Exception:
            return None

    def _scrape_bugs_realtime(self):
        url = "https://music.bugs.co.kr/chart"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        try:
            res = None
            if self.proxies:
                try:
                    res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=10)
                except:
                    pass
            
            if not res or res.status_code != 200:
                res = requests.get(url, headers=headers, verify=False, timeout=10)

            soup = BeautifulSoup(res.text, 'html.parser')
            
            titles = soup.select('p.title a')
            artists = soup.select('p.artist a:nth-of-type(1)')
            
            if not titles or not artists: return None
            
            context = ""
            for i in range(min(10, len(titles))):
                context += f"- Rank {i+1}: {titles[i].text.strip()} by {artists[i].text.strip()}\n"
            return context
        except Exception:
            return None

    def _scrape_naver_ratings(self, query):
        url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        try:
            res = None
            if self.proxies:
                try:
                    res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=10)
                except:
                    pass
            
            if not res or res.status_code != 200:
                res = requests.get(url, headers=headers, verify=False, timeout=10)

            soup = BeautifulSoup(res.text, 'html.parser')
            
            tables = soup.select('table')
            rating_text = ""
            for table in tables:
                if '%' in table.text or '시청률' in table.text:
                    rows = table.select('tr')
                    for i, row in enumerate(rows):
                        if i == 0: continue
                        cols = row.select('td')
                        if len(cols) >= 2:
                            title = cols[0].text.strip()
                            rating = cols[1].text.strip()
                            rating_text += f"- Title: {title}, Rating: {rating}\n"
                    break 
                    
            if rating_text:
                return rating_text
            
            main_pack = soup.select_one('#main_pack')
            if main_pack:
                return main_pack.get_text(separator=' | ', strip=True)[:8000]
                
            return None
        except Exception:
            return None

    def _scrape_naver_blogs(self, query):
        url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        try:
            res = None
            if self.proxies:
                try:
                    res = requests.get(url, headers=headers, proxies=self.proxies, verify=False, timeout=10)
                except:
                    pass
            
            if not res or res.status_code != 200:
                res = requests.get(url, headers=headers, verify=False, timeout=10)

            soup = BeautifulSoup(res.text, 'html.parser')
            
            titles = soup.select('a.title_link')
            if titles:
                context = ""
                for i in range(min(20, len(titles))):
                    context += f"- Title: {titles[i].text.strip()}\n"
                return context
                
            fallback_titles = soup.select('.api_txt_lines, .link_tit, .title')
            if fallback_titles:
                context = ""
                for i in range(min(20, len(fallback_titles))):
                    context += f"- Title: {fallback_titles[i].text.strip()}\n"
                return context
            
            main_pack = soup.select_one('#main_pack')
            if main_pack:
                return main_pack.get_text(separator=' | ', strip=True)[:8000]
                
            return None
        except Exception:
            return None

    def _process_with_groq(self, category, context, source_type):
        if not self.groq_keys or not self.model_name:
            return json.dumps({"top10": []})

        today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 💡 [버그 해결] 프롬프트 조건 완화: 텍스트가 엉망이어도 빈칸 치지 말고 무조건 뽑아내도록 명령
        prompt = f"""
        Current Time: {today}.
        Task: Create a Top 10 ranking chart for '{category}' based ABSOLUTELY ONLY on the provided source text.
        
        Source Data ({source_type}):
        {context}
        
        CRITICAL RULES:
        1. DO NOT HALLUCINATE. Use ONLY the data provided above.
        2. Extract up to 10 items. Even if the text is messy or not formatted perfectly, logically deduce the top items (e.g., highly mentioned places, shows, or ratings). ONLY return empty [] if there is absolutely zero relevant data.
        3. Translate all Korean titles naturally into English.
        4. 'info' should be a concise 1-sentence description.
        5. Output STRICTLY as a valid JSON object without markdown code blocks.
        
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
                        {"role": "system", "content": "You are a strict data parser. You only parse data from the prompt. Output nothing but JSON."},
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
