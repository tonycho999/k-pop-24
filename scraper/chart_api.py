import asyncio
import json
from playwright.async_api import async_playwright

class ChartEngine:
    def __init__(self):
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self.rotation_map = {
            "k-pop": ["melon", "genie", "bugs"],
            "k-drama": ["naver_search", "naver_search", "naver_search"],
            "k-movie": ["naver_search", "naver_search", "naver_search"],
            "k-entertain": ["naver_search", "naver_search", "naver_search"]
        }

    async def get_top10_chart(self, category, run_count):
        targets = self.rotation_map.get(category, ["naver_search"])
        target = targets[run_count % 3]
        
        print(f"🔍 [Attempt] Category: {category} | Primary: {target}")
        result = await self._scrape_entry(target, category)
        
        # 메인 타겟 실패 시 네이버 백업 실행
        if not result or len(result) < 3:
            print(f"⚠️ {target} failed/insufficient. Switching to Emergency Backup: naver_search")
            result = await self._scrape_entry("naver_search", category)
            
        return json.dumps({"top10": result}, ensure_ascii=False)

    async def _scrape_entry(self, target, category):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # 권한 및 언어 설정 추가 (차단 방지)
            context = await browser.new_context(user_agent=self.ua, locale="ko-KR")
            page = await context.new_page()
            data = []
            
            try:
                if target == "melon":
                    await page.goto("https://www.melon.com/chart/index.htm", timeout=30000)
                    await page.wait_for_selector(".lst50", timeout=10000)
                    rows = await page.query_selector_all(".lst50")
                    for i, r in enumerate(rows[:10]):
                        t = await (await r.query_selector(".rank01 a")).inner_text()
                        a = await (await r.query_selector(".rank02 a")).inner_text()
                        data.append({"rank": i+1, "title": t.strip(), "info": a.strip()})
                
                elif target == "naver_search":
                    # 카테고리별 검색어 최적화
                    queries = {
                        "k-pop": "멜론 차트 순위",
                        "k-drama": "드라마 시청률 순위",
                        "k-movie": "박스오피스 순위",
                        "k-entertain": "예능 시청률 순위"
                    }
                    search_url = f"https://search.naver.com/search.naver?query={queries.get(category, category)}"
                    await page.goto(search_url, timeout=30000)
                    
                    # 네이버 통합검색 결과 로딩 대기 (중요)
                    await page.wait_for_load_state("networkidle")
                    await page.mouse.wheel(0, 500) # 약간의 스크롤로 로딩 유도
                    await asyncio.sleep(2) # 안정적인 로딩을 위한 대기

                    # [수정된 Selector] 네이버 통합검색 순위 리스트 패턴 (2026 기준 대응)
                    # 시청률/박스오피스 공통 요소를 더 넓게 잡음
                    items = await page.query_selector_all(".api_subject_bx .list_box .item, .api_subject_bx .lst_common .item")
                    
                    if not items:
                        # 대안 Selector 시도 (박스오피스 전용 등)
                        items = await page.query_selector_all(".box_image_list .item, .movie_audience_ranking .item")

                    for i, item in enumerate(items[:10]):
                        # 제목 찾기
                        title_el = await item.query_selector(".name, .title, .tit")
                        # 정보(시청률/관객수) 찾기
                        info_el = await item.query_selector(".figure, .sub_text, .value")
                        
                        if title_el:
                            t_text = await title_el.inner_text()
                            i_text = await info_el.inner_text() if info_el else ""
                            data.append({"rank": i+1, "title": t_text.strip(), "info": i_text.strip()})

                await browser.close()
                return data

            except Exception as e:
                print(f"❌ Scrape Error ({target} - {category}): {e}")
                # 실패 시 로그용 스크린샷 저장
                await page.screenshot(path=f"debug_{category}.png")
                await browser.close()
                return None
