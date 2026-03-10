import os
import json
import requests
from bs4 import BeautifulSoup
from google import genai

class NaverNewsAPI:
    def __init__(self, db_client):
        self.db = db_client
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        if self.gemini_key:
            self.ai_client = genai.Client(api_key=self.gemini_key)

        # 💡 프록시 로드
        self.proxy_host = os.environ.get("PROXY_HOST")
        self.proxy_port = os.environ.get("PROXY_PORT")
        self.proxy_user = os.environ.get("PROXY_USER")
        self.proxy_pass = os.environ.get("PROXY_PASS")
        
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
        
        # 1. 듀얼 엔진 스크래핑
        articles = self._scrape_top_30_links(target_url)
        if not articles:
            print("  ❌ Fatal Error: Could not retrieve any articles.")
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

        print(f"  🔍 Processing articles for '{category}'...")
        processed_count = 0  # 💡 30개 강제 할당 카운터

        for article in articles:
            if processed_count >= 30: break
            url = article['link']

            if url in existing_links:
                processed_count += 1
                rank = processed_count
                target_score = 100 - rank 
                current_top_links.add(url)

                rec_id = existing_links[url]
                try:
                    self.db.client.table("live_news").update({"score": target_score}).eq("id", rec_id).execute()
                    print(f"    🔄 [Maintained] Rank {rank}: DB Score updated to {target_score}.")
                except:
                    pass
            else:
                # 썸네일/본문 없으면 카운터 올리지 않고 스킵
                content, image_url = self._scrape_article_content(url)

                if not content or not image_url:
                    print(f"      ⏭️ Skipped: Missing Thumbnail or Content. ({url})")
                    continue

                processed_count += 1
                rank = processed_count
                target_score = 100 - rank 
                current_top_links.add(url)

                print(f"    ✨ [New Intake] Rank {rank}: Fetching content for AI... ({url})")
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
                print(f"  🧹 [Purge] Deleted {len(drop_ids)} old articles.")
            except:
                pass

    def _scrape_top_30_links(self, url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://m.naver.com/"
        }
        articles = []

        print("  🕵️ Initiating Plan A with Proxy...")
        try:
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
                print(f"  🟢 Plan A Success: Found {len(articles)} articles.")
                return articles
        except Exception as e:
            print(f"  ⚠️ Plan A failed: {e}")

        print("  🚜 Initiating Plan B (Headless Browser)...")
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
                    href = "https://m.entertain.naver.com" + href if 'entertain' in url else "https://n.news.naver.com" + href
                if href not in seen:
                    seen.add(href)
                    articles.append({'link': href})
            
            print(f"  🟢 Plan B Success: Found {len(articles)} articles.")
            return articles
        except Exception as e:
            print(f"  ❌ Plan B Failed: {e}")

        return articles

    def _scrape_article_content(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
        try:
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
        except Exception:
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
