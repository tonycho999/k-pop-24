import os
import json
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

class ChartManager:
    def __init__(self, model_name):
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(model_name)
        
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
        """우회 봇을 이용한 실시간 차트/시청률 스크래핑"""
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            if target == "melon":
                res = requests.get("https://www.melon.com/chart/index.htm", headers=headers, proxies=self.proxies, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                return soup.find('tbody').get_text(separator=' | ', strip=True)[:4000]
            elif target == "nielsen":
                res = requests.get("https://search.naver.com/search.naver?query=주간+예능+시청률", headers=headers, proxies=self.proxies, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                return soup.find('table').get_text(separator=' | ', strip=True)[:4000]
        except:
            return ""

    def process_chart(self, category: str, context: str):
        prompt = ""
        
        if category == "k-pop":
            raw = self._scrape_real_chart("melon")
            prompt = f"""
            Task: Create Top 10 K-Pop Chart.
            Data: {raw}
            RULES: 'title' is Song Name. 'info' is Singer Name. 
            Score: Assign 100 for 1st place, decreasing by 1 down to 91 for 10th.
            """
        elif category == "k-entertain":
            raw = self._scrape_real_chart("nielsen")
            prompt = f"""
            Task: Create Top 10 Variety Show Chart based on ratings.
            Data: {raw}
            RULES: 'title' is Show Name. 'info' is TV Channel. EXCLUDE Dramas.
            Score: Assign 100 for 1st place, decreasing by 1 down to 91 for 10th.
            """
        elif category == "k-actor":
            prompt = f"""
            Task: Create Top 10 Actor Trend Chart based on mention frequency today.
            Data: {context}
            RULES: 'title' is Actor Name. 'info' is short keyword (e.g. "Drama"). 
            Score: Assign freely between 80 and 100 based on buzz.
            """
        elif category == "k-culture":
            prompt = f"""
            Task: Create Top 10 K-Culture Chart.
            Data: {context}
            RULES: Extract PROPER NOUNS ONLY (Food, Festival, Pop-up). EXCLUDE City names and Human names (Actors/Singers/Sports).
            Score: Assign freely between 50 and 80 ONLY. (Max 80).
            """

        prompt += """
        Format exactly as JSON:
        { "top10": [ { "rank": 1, "title": "Name", "info": "Keyword", "score": 95 } ] }
        """
        try:
            res_text = self.model.generate_content(prompt).text
            data = json.loads(res_text.replace("```json", "").replace("```", "").strip())
            return data.get("top10", [])
        except Exception as e:
            print(f"❌ Gemini Chart Error: {e}")
            return None
