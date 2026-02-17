import asyncio
import os
from playwright.async_api import async_playwright

class ChartEngine:
    def __init__(self):
        # 이제 Perplexity를 사용하지 않으므로 API 설정은 생략하거나 유지해도 됩니다.
        pass

    def get_top10_chart(self, category):
        """
        Playwright 봇을 사용하여 멜론에서 직접 텍스트를 추출합니다.
        (현재 K-POP 카테고리만 봇으로 동작하도록 설정)
        """
        if category == "k-pop":
            print(f"🚀 [Bot] Scraping Melon Top 10 Chart directly...")
            return asyncio.run(self._scrape_melon())
        else:
            # 다른 카테고리는 현재 빈 데이터 반환 (필요시 추가 확장 가능)
            return '{"top10": []}'

    async def _scrape_melon(self):
        async with async_playwright() as p:
            # GitHub Actions 환경에서는 headless=True 필수
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 멜론 차트 접속
                await page.goto("https://www.melon.com/chart/index.htm", timeout=60000)
                await page.wait_for_selector(".lst50", timeout=10000)

                top10_data = []
                # 상위 10개 행 추출
                rows = await page.query_selector_all(".lst50")
                for i, row in enumerate(rows[:10]):
                    title_el = await row.query_selector(".rank01 a")
                    artist_el = await row.query_selector(".rank02 a")
                    
                    title = (await title_el.inner_text()).strip()
                    artist = (await artist_el.inner_text()).strip()
                    
                    top10_data.append({
                        "rank": i + 1,
                        "title": title,
                        "info": artist  # 메타 정보에 가수명 저장
                    })

                await browser.close()
                # 기존 main.py와 호환되도록 JSON 형식으로 반환
                return json.dumps({"top10": top10_data}, ensure_ascii=False)
            
            except Exception as e:
                print(f"❌ Bot Scraping Error: {e}")
                await browser.close()
                return '{"top10": []}'
