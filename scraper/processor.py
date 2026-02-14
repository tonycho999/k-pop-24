import time
import config
import naver_api
import gemini_api
import database

def run_category(category_name):
    print(f"\n🚀 Processing: {category_name}")
    
    # 1. [광범위 탐색] API로 제목만 100개 수집
    keyword = config.SEARCH_KEYWORDS.get(category_name)
    raw_items = naver_api.search_news_api(keyword, display=100)
    
    if not raw_items:
        print("   ⚠️ No items found.")
        return

    # 제목 리스트 생성
    titles = "\n".join([f"- {item['title']}" for item in raw_items])

    # 2. [랭킹 선정] AI에게 Top 10 선정 요청
    rank_prompt = f"""
    [Task]
    Analyze these news titles about {category_name}:
    {titles[:10000]}
    
    Select Top 10 trending keywords (Person, Group, or Work).
    Output JSON: {{ "keywords": ["Key1", "Key2", ...] }}
    """
    
    rank_res = gemini_api.ask_gemini(rank_prompt)
    if not rank_res: return

    keywords = rank_res.get("keywords", [])[:10]
    print(f"   🔥 Trending: {keywords}")

    # 3. [정밀 수집] 키워드별로 봇 파견
    final_data = []
    
    for idx, key in enumerate(keywords):
        print(f"   Running ({idx+1}/10): {key}")
        
        # 기사 2개 검색
        items = naver_api.search_news_api(key, display=2)
        full_texts = []
        link = ""

        for item in items:
            link = item['link']
            # 봇이 본문 긁기
            body = naver_api.crawl_full_body(link)
            if body:
                full_texts.append(body)
            else:
                full_texts.append(item['description']) # 실패시 요약본
        
        if not full_texts: continue

        # 4. [요약] AI 기사 작성
        summary_prompt = f"""
        [Input Articles about '{key}']
        {str(full_texts)[:5000]}

        [Task]
        Write a news summary (Korean).
        Output JSON: {{ "title": "...", "summary": "..." }}
        """
        
        sum_res = gemini_api.ask_gemini(summary_prompt)
        
        if sum_res:
            final_data.append({
                "category": category_name,
                "keyword": key,
                "title": sum_res.get("title", f"{key} 이슈"),
                "summary": sum_res.get("summary", ""),
                "link": link,
                "score": 100 - idx,
                "created_at": "now()"
            })
        
        time.sleep(1) # 과부하 방지

    # 5. [저장]
    if final_data:
        database.save_news(final_data)
        database.cleanup_old_news(category_name)
