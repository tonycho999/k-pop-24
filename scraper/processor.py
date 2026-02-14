# scraper/processor.py
import time
from datetime import datetime
import config
import naver_api
import gemini_api
import database

def run_category_process(category):
    print(f"\n🚀 [Processing] Category: {category}")

    # 1. 최신 기사 제목 100개 수집
    queries = config.SEARCH_QUERIES.get(category, [])
    all_titles = []
    seen_links = set()

    print(f"   1️⃣ Collecting 100 latest titles...")
    for q in queries:
        # 각 쿼리당 40개씩 요청하여 중복 제거 후 100개 근처로 맞춤
        items = naver_api.search_news_api(q, display=40) 
        for item in items:
            if item['link'] not in seen_links:
                seen_links.add(item['link'])
                # HTML 태그 제거 및 제목만 보관
                clean_title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", "")
                all_titles.append(clean_title)
        time.sleep(0.3)

    if not all_titles:
        print("   ❌ [Stop] No titles found.")
        return

    print(f"      ✅ Total titles for analysis: {len(all_titles)}")

    # 2. 제목 빈도 분석 기반 키워드 추출 (AI에게 제목 리스트 전달)
    print("   2️⃣ AI analyzing frequency & trends...")
    
    # 카테고리별 추출 규칙 (사용자 지시사항 100% 반영)
    if category == "K-Pop":
        rule = "Target: SONG TITLE / Search: ARTIST NAME"
    elif category == "K-Drama":
        rule = "Target: DRAMA TITLE / Search: MAIN ACTOR NAME"
    elif category == "K-Movie":
        rule = "Target: MOVIE TITLE / Search: MAIN ACTOR NAME"
    elif category == "K-Entertain":
        rule = "Target: SHOW TITLE / Search: CAST MEMBER NAME"
    else: # K-Culture
        rule = "Target: PLACE/FOOD/EVENT NAME (English) / Search: Korean Name. EXCLUDE IDOLS."

    rank_prompt = f"""
    [Context]
    Category: {category}
    Below are the latest 100 news titles. Analyze which subjects are mentioned most frequently.

    [Task]
    Identify the Top 10 most mentioned subjects following these rules:
    {rule}

    [News Titles]
    {chr(10).join(all_titles[:100])}

    [Output JSON ONLY]
    {{ "rankings": [ {{ "rank": 1, "display_title_en": "Title", "search_keyword_kr": "SearchName", "meta": "Short reason", "score": 95 }} ] }}
    """
    
    rank_res = gemini_api.ask_gemini(rank_prompt)
    if not rank_res or "rankings" not in rank_res:
        print("   ❌ [Stop] AI failed to extract keywords.")
        return

    rankings = rank_res.get("rankings", [])[:10]
    database.save_rankings_to_db([
        {
            "category": category, "rank": r['rank'], "title": r['display_title_en'],
            "meta_info": r['meta'], "score": r['score'], "updated_at": datetime.now().isoformat()
        } for r in rankings
    ])

    # 3. 타겟 선정 (1위 혹은 쿨타임 아닌 것)
    target = next((r for r in rankings if not database.is_keyword_used_recently(category, r['display_title_en'])), rankings[0])
    target_display = target['display_title_en']
    target_search = target['search_keyword_kr']
    print(f"   3️⃣ Selected: '{target_display}' (Search: {target_search})")

    # 4. 선택된 키워드로 정밀 검색 (이제 여기서만 본문을 읽음)
    print(f"   4️⃣ Deep dive into '{target_search}'...")
    target_items = naver_api.search_news_api(target_search, display=3)
    
    full_texts = []
    target_link, target_image = "", ""

    for item in target_items:
        crawled = naver_api.crawl_article(item['link'])
        if crawled['text']:
            full_texts.append(crawled['text'])
            if not target_image: target_image = crawled['image']
            if not target_link: target_link = item['link']
        else:
            full_texts.append(item['description'])
            if not target_link: target_link = item['link']

    # 5. 최종 영어 요약 작성
    print(f"   5️⃣ Summarizing news in English...")
    summary_prompt = f"""
    [Topic] {target_display} ({target_search})
    [Articles] {str(full_texts)[:5000]}
    [Task] Write a news summary in ENGLISH.
    [Output JSON] {{ "title": "Headline", "summary": "3-5 sentences" }}
    """
    
    sum_res = gemini_api.ask_gemini(summary_prompt)
    if sum_res:
        news_item = {
            "category": category, "keyword": target_display,
            "title": sum_res.get("title"), "summary": sum_res.get("summary"),
            "link": target_link, "image_url": target_image,
            "score": 100, "created_at": datetime.now().isoformat(), "likes": 0
        }
        database.save_news_to_live([news_item])
        database.save_news_to_archive([news_item])
        database.cleanup_old_data(category, config.MAX_ITEMS_PER_CATEGORY)
        print("   🎉 SUCCESS!")
