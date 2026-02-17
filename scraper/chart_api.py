import asyncio
import json  # <--- 이 부분이 누락되어 에러가 발생했습니다!
import os
from playwright.async_api import async_playwright

class ChartEngine:
    def __init__(self):
        pass

    def get_top10_chart(self, category):
        """
        봇을 사용하여 웹사이트에서 직접 텍스트를 추출합니다.
        """
        if category == "k-pop":
            print(f"🔍 [Bot] Scraping Melon Real-time Chart...")
            try:
                # Playwright 동기 실행을 위한 처리
                return asyncio.run(self._scrape_melon())
            except Exception as e:
                print(f"❌ Scraping Error: {e}")
                return json.dumps({"top10": []})
        else:
            return json.dumps({"top10": []})

    async def _scrape_melon(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 멜론 차트 접속
                await page.goto("https://www.melon.com/chart/index.htm", timeout=60000)
                await page.wait_for_selector(".lst50", timeout=10000)

                top10_data = []
                rows = await page.query_selector_all(".lst50")
                
                for i, row in enumerate(rows[:10]):
                    # 순수 텍스트 추출 (곡명, 가수명)
                    title_el = await row.query_selector(".rank01 a")
                    artist_el = await row.query_selector(".rank02 a")
                    
                    title = (await title_el.inner_text()).strip()
                    artist = (await artist_el.inner_text()).strip()
                    
                    top10_data.append({
                        "rank": i + 1,
                        "title": title,
                        "info": artist
                    })

                await browser.close()
                # ensure_ascii=False를 해줘야 한글이 깨지지 않고 JSON으로 저장됩니다.
                return json.dumps({"top10": top10_data}, ensure_ascii=False)
            
            except Exception as e:
                print(f"❌ Bot Scraping Error: {e}")
                await browser.close()
                return json.dumps({"top10": []})
