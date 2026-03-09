import os
import json
import time  # 💡 재시도(Retry) 대기 시간을 위해 추가
import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from google import genai

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ChartManager:
    def __init__(self, model_name):
        self.ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model_name = model_name
        
        # IPRoyal 우회 봇 프록시 세팅
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

    def _scrape_real_chart(self, target):
        """우회 봇을 이용한 실시간 차트/시청률 스크래핑 (타임아웃 & 재시도 로직 추가)"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        max_retries = 3  # 💡 최대 3번까지 끈질기게 재시도
        for attempt in range(max_retries):
            try:
                if target == "melon":
                    # 💡 timeout을 10초에서 30초로 대폭 늘렸습니다.
                    res = requests.get("https://www.melon.com/chart/index.htm", headers=headers, proxies=self.proxies, timeout=30, verify=False)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    return soup.find('tbody').get_text(separator=' | ', strip=True)[:4000]
                elif target == "nielsen":
                    res = requests.get("https://search.naver.com/search.naver?query=주간+예능+시청률", headers=headers, proxies=self.proxies, timeout=30, verify=False)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    return soup.find('table').get_text(separator=' | ', strip=True)[:4000]
            except Exception as e:
                print(f"⚠️ Scraping Attempt {attempt + 1} Error ({target}): {e}")
                if attempt == max_retries - 1: # 마지막 시도까지 실패하면
                    return ""
                time.sleep(3) # 💡 실패 시 3초 쉬었다가 다시 찔러봅니다.
        return ""

    def process_chart(self, category: str, context: str):
        kst = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S KST")
        
        prompt = ""
        
        if category == "k-pop":
            raw = self._scrape_real_chart("melon")
            if not raw or len(raw) < 50:
                print("❌ 최신 멜론 차트 크롤링 실패 (AI 할루시네이션 방지 차단)")
                return None
                
            prompt = f"""
            Current Time in Korea: {now_kst}
            Task: Create Top 10 K-Pop Chart STRICTLY based on the provided live data.
            Data: {raw}
            CRITICAL RULES:
            1. DO NOT use your past knowledge. Only use the 'Data' provided above.
            2. 'title' is Song Name. 'info' is Singer Name. 
            3. Score: Assign 100 for 1st place, decreasing by 1 down to 91 for 10th.
            """
            
        elif category == "k-entertain":
            raw = self._scrape_real_chart("nielsen")
            if not raw or len(raw) < 50:
                print("❌ 최신 닐슨 시청률 크롤링 실패 (AI 할루시네이션 방지 차단)")
                return None
                
            prompt = f"""
            Current Time in Korea: {now_kst}
            Task: Create Top 10 Variety Show Chart strictly based on the provided live ratings data.
            Data: {raw}
            CRITICAL RULES:
            1. DO NOT use your past knowledge. Only use the 'Data' provided above.
            2. 'title' is Show Name. 'info' is TV Channel. EXCLUDE Dramas.
            3. Score: Assign 100 for 1st place, decreasing by 1 down to 91 for 10th.
            """
            
        elif category == "k-actor":
            prompt = f"""
            Current Time in Korea: {now_kst}
            Task: Create Top 10 Actor Trend Chart based strictly on today's news context (last 24 hours).
            Data: {context}
            CRITICAL RULES:
            1. DO NOT use past knowledge. Only rank actors mentioned in the 'Data' text.
            2. 'title' is Actor Name. 'info' is short keyword (e.g. "Drama"). 
            3. Score: Assign freely between 80 and 100 based on buzz.
            """
            
        elif category == "k-culture":
            prompt = f"""
            Current Time in Korea: {now_kst}
            Task: Create Top 10 K-Culture Chart based strictly on today's news context (last 24 hours).
            Data: {context}
            CRITICAL RULES:
            1. DO NOT use past knowledge. Only use the 'Data' text.
            2. Extract PROPER NOUNS ONLY (Food, Festival, Pop-up). EXCLUDE City names and Human names.
            3. Score: Assign freely between 50 and 80 ONLY. (Max 80).
            """

        prompt += """
        Format exactly as JSON:
        { "top10": [ { "rank": 1, "title": "Name", "info": "Keyword", "score": 95 } ] }
        """
        
        try:
            response = self.ai_client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            res_text = response.text
            data = json.loads(res_text.replace("```json", "").replace("```", "").strip())
            top10_list = data.get("top10", [])
            
            # 💡 [핵심 방어막] 제미나이가 순위를 엉망(중복)으로 줘도 파이썬이 강제로 1위~10위로 오버라이드!
            for i, item in enumerate(top10_list):
                item['rank'] = i + 1
                
            return top10_list
        except Exception as e:
            print(f"❌ Gemini Chart Error: {e}")
            return None
