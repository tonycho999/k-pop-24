import asyncio
import json
import os
from playwright.async_api import async_playwright

class ChartEngine:
    def __init__(self):
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        # 카테고리별 3사 로테이션 맵
        self.rotation_map = {
            "k-pop": ["melon", "genie", "bugs"],
            "k-drama": ["nielsen", "naver_drama", "daum_drama"],
            "k-movie": ["kobis", "naver_movie", "daum_movie"],
            "k-entertain": ["nielsen_ent", "naver_ent", "daum_ent"]
        }

    async def get_top10_chart(self, category, run_count):
        targets = self.rotation_map.get(category, ["naver_search"])
        target = targets[run_count % 3] # 0, 1, 2 순환
        
        print(f"🔍 [Attempt] Category: {category} | Primary: {target}")
        
        # 1. 메인 타겟 시도
        result = await self._scrape_entry(target, category)
        
        # 2. 실패 시 즉시 네이버 통합 검색(백업) 시도
        if not result or len(result) < 5:
            print(f"⚠️ {target} failed or insufficient. Switching to Backup: naver_search")
            result = await self._scrape_entry("naver_search", category)
            
        return json.dumps({"top10": result}, ensure_ascii=False)

    async def _scrape_entry(self, target, category):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=self.ua)
            data = []
            try:
                # [예시] 타겟별 분기 처리 (실제 사이트별 Selector 적용 필요)
                if target == "melon":
                    await page.goto("https://www.melon.com/chart/index.htm", timeout=30000)
                    rows = await page.query_selector_all(".lst50")
                    for i, r in enumerate(rows[:10]):
                        t = await (await r.query_selector(".rank01 a")).inner_text()
                        a = await (await r.query_selector(".rank02 a")).inner_text()
                        data.append({"rank": i+1, "title": t.strip(), "info": a.strip()})
                
                elif target == "naver_search":
                    queries = {"k-pop":"멜론차트", "k-drama":"드라마 시청률", "k-movie":"박스오피스", "k-entertain":"예능 시청률"}
                    await page.goto(f"https://search.naver.com/search.naver?query={queries.get(category, category)}")
                    await page.wait_for_timeout(2000)
                    items = await page.query_selector_all(".api_subject_bx .list_box .item")
                    for i, item in enumerate(items[:10]):
                        title_el = await item.query_selector(".name, .title")
                        if title_el:
                            data.append({"rank": i+1, "title": (await title_el.inner_text()).strip(), "info": ""})

                # (지니, 벅스, 닐슨 등 추가 타겟 로직 구현...)
                
                await browser.close()
                return data
            except Exception as e:
                # 실패 시 에러가 난 시점의 HTML을 저장하여 AI 분석용으로 넘김
                print(f"❌ Scrape Error ({target}): {e}")
                html_content = await page.content()
                with open(f"error_{category}.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                await browser.close()
                return None
