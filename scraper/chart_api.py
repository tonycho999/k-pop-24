import os
import json
import time
import requests
from bs4 import BeautifulSoup
from google import genai

class NaverNewsAPI:
    def __init__(self, db_client):
        self.db = db_client
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        if self.gemini_key:
            self.ai_client = genai.Client(api_key=self.gemini_key)

        # 💡 [핵심 추가] GitHub Secrets에 저장된 프록시 정보 로드
        self.proxy_host = os.environ.get("PROXY_HOST")
        self.proxy_port = os.environ.get("PROXY_PORT")
        self.proxy_user = os.environ.get("PROXY_USER")
        self.proxy_pass = os.environ.get("PROXY_PASS")
        
        # requests 라이브러리용 프록시 딕셔너리 생성
        self.proxies = None
        if self.proxy_host and self.proxy_port and self.proxy_user and self.proxy_pass:
            proxy_url = f"http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_host}:{self.proxy_port}"
            self.proxies = {
                "http": proxy_url,
                "https": proxy_url
            }

    def get_target_url(self, category):
        urls = {
            'k-pop': 'https://m.entertain.naver.com/music',
            'k-movie': 'https://m.entertain.naver.com/movie',
            'k-drama': 'https://m.entertain.naver.com/tv',
            'k-entertain': 'https://m.entertain.naver.com/ranking',
            'k-culture': 'https://m.news.naver.com/rankingList'
        }
        return urls.get(category, 'https://m.entertain.naver.com/ranking')

    def run_pipeline(self, category):
        target_url = self.get_target_url(category)
        
        # 1. 듀얼 엔진 스크래핑 (프록시 기본 탑재)
        articles = self._scrape_top_30_links(target_url)
        if not articles:
            print("  ❌ Fatal Error: Could not retrieve any articles even with Proxy & Plan B.")
            return

        existing_records = []
        try:
            res = self.db.client.table("live_news").select("id, link").eq("category", category).execute()
            existing_records = res.data if res.data else []
        except Exception as e:
            print(f"  ⚠️ Existing DB check failed: {e}")

        existing_links = {rec['link']: rec['id'] for rec in existing_records}
        new_results = []
        current_top_links = set()

        print(f"  🔍 Processing {len(articles)} articles for '{category}'...")
        for i, article in enumerate(articles):
            if i >= 30: break
            rank = i + 1
            target_score = 100 - rank 
            url = article['link']
            current_top_links.add(url)

            if url in existing_links:
                rec_id = existing_links[url]
                try:
                    self.db.client.table("live_news").update({"score": target_score}).eq("id", rec_id).execute()
                    print(f"    🔄 [Maintained] Rank {rank}: DB Score updated to {target_score} (AI skipped).")
                except:
                    pass
            else:
                print(f"    ✨ [New Intake] Rank {rank}: Fetching content for AI... ({url})")
                content, image_url = self._scrape_article_content(url)

                if not content or not image_url:
                    print(f"      ⏭️ Skipped: Missing Thumbnail or Content.")
                    continue

                ai_data = self._generate_ai_summary(content, category, url, image_url, target_score)
                if ai_data:
                    new_results.append(ai_data)
                    print(f"      ✅ AI Summarized: {ai_data['title']}")

        if new_results:
            self.db.save_news_results(category, new_results)

        drop_ids = [rec['id'] for rec in existing_records if rec['link'] not in current_top_links]
        if drop_ids:
            try:
                self.db.client.table("live_news").delete().in_("id", drop_ids).execute()
                print(f"  🧹 [Purge] Deleted {len(drop_ids)} old articles that dropped out of Top 30.")
            except Exception as e:
                print(f"  ⚠️ Purge error: {e}")

    def _scrape_top_30_links(self, url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://m.naver.com/"
        }
        articles = []

        # 🛡️ Plan A: 프록시망(IPRoyal)을 경유한 강력 위장 잠입
        print("  🕵️ Initiating Plan A with Proxy...")
        try:
            # self.proxies를 태워서 네이버에 요청
            res = requests.get(url, headers=headers, proxies=self.proxies, timeout=15, verify=False)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            
            links = [a for a in soup.find_all('a', href=True) if 'article' in a['href'] or 'read' in a['href']]
            seen = set()
            for a in links:
                href = a['href']
                if not href.startswith('http'):
                    href = "https://m.entertain.naver.com" + href if 'entertain' in url else "https://n.news.naver.com" + href
                if href not in seen:
                    seen.add(href)
                    articles.append({'link': href})

            if len(articles) >= 10:
                print(f"  🟢 Plan A Success: Found {len(articles)} articles using Proxy.")
                return articles
        except Exception as e:
            print(f"  ⚠️ Plan A failed (Proxy/Request error): {e}")

        # 🚜 Plan B: 투명 전차 (헤드리스 브라우저 + 프록시 동시 적용)
        print("  🚜 Initiating Plan B (Headless Browser Auto-Failover)...")
        try:
            from playwright.sync_api import sync_playwright
            
            proxy_settings = None
            if self.proxy_host:
                proxy_settings = {
                    "server": f"http://{self.proxy_host}:{self.proxy_port}",
                    "username": self.proxy_user,
                    "password": self.proxy_pass
                }

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, proxy=proxy_settings)
                page = browser.new_page(user_agent=headers["User-Agent"])
                page.goto(url, timeout=20000)
                page.wait_for_timeout(2000) 
                html = page.content()
                browser.close()

            soup = BeautifulSoup(html, 'html.parser')
            links = [a for a in soup.find_all('a', href=True) if 'article' in a['href'] or 'read' in a['href']]
            seen = set()
            articles = []
            for a in links:
                href = a['href']
                if not href.startswith('http'):
                    href = "https://m.entertain.naver.com" + href
                if href not in seen:
                    seen.add(href)
                    articles.append({'link': href})
            
            print(f"  🟢 Plan B Success: Found {len(articles)} articles using Playwright & Proxy.")
            return articles
        except ImportError:
            print("  ❌ Plan B Aborted: 'playwright' is not installed in the server environment.")
        except Exception as e:
            print(f"  ❌ Plan B Failed: {e}")

        return articles

    def _scrape_article_content(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
        try:
            # 💡 [핵심] 본문을 긁어올 때도 프록시를 태워서 차단 방지! (verify=False로 SSL 오류 회피)
            res = requests.get(url, headers=headers, proxies=self.proxies, timeout=15, allow_redirects=True, verify=False)
            soup = BeautifulSoup(res.text, 'html.parser')

            meta_img = soup.find("meta", property="og:image")
            img_url = meta_img["content"].strip() if meta_img and meta_img.get("content") else None
            blacklist = ["dummy", "naver_logo", "navernews", "default", "blank", "no_image", "news_logo"]
            if img_url and any(bad in img_url.lower() for bad in blacklist):
                img_url = None

            body = soup.select_one("#dic_area, #articeBody, .article_body, .news_end")
            text = body.get_text(separator=' ', strip=True) if body else soup.get_text(separator=' ', strip=True)[:3000]

            return text[:3500], img_url
        except Exception as e:
            print(f"      ⚠️ Content Scrape Error: {e}")
            return None, None

    def _generate_ai_summary(self, content, category, url, image_url, score):
        prompt = f'''
        You are a highly strictly factual English news summarizer. 
        Read the Korean article below and summarize it.
        
        CRITICAL RULES:
        1. Length: Must be between 3 to 10 sentences depending on importance.
        2. FACT ONLY: Do NOT add expert analysis, your personal opinions, or extra commentary. 
        3. PRESERVE NOUNS & NUMBERS: Keep all proper nouns (names of people/places/groups/works) and numbers (ages, money, dates) EXACTLY as they are, but translated naturally into English.
        4. Output strictly in the following JSON format without markdown code blocks.

        Article Content:
        {content}

        JSON Format:
        {{
            "title": "[English Translated Title]",
            "summary": "Factual English Summary..."
        }}
        '''
        try:
            ai_res = self.ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            text = ai_res.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)

            return {
                "name": url, 
                "title": data.get("title", "Untitled"),
                "summary": data.get("summary", ""),
                "link": url,
                "image_url": image_url,
                "score": score
            }
        except Exception as e:
            print(f"      ❌ AI Error: {e}")
            return None
