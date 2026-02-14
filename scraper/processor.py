# scraper/processor.py
import time
from datetime import datetime
import config
import naver_api
import gemini_api
import database

def run_category_process(category):
    print(f"\n🚀 [Processing] Category: {category}")

    # 1. [광범위 탐색] API로 100개 수집
    keyword = config.SEARCH_KEYWORDS.get(category)
    raw_items = naver_api.search_news_api(keyword, display=100)
    
    if not raw_items:
        print("   ⚠️ No items found from Naver API.")
        return

    titles = "\n".join([f"- {item['title']}" for item in raw_items])

    # 2. [랭킹 선정] AI에게 Top 10 키워드/순위 추출 요청
    # live_rankings 테이블 스키마에 맞춤 (rank, title, meta_info, score)
    rank_prompt = f"""
    [Task]
    Analyze these news titles about {category}:
    {titles[:15000]}
    
    1. Identify Top 10 trending keywords (Person, Group, Work).
    2. Provide a short meta info for each (e.g., "New Album", "High Rating").
    
    [Output JSON Format]
    {{
        "rankings": [
            {{ "rank": 1, "keyword": "Name", "meta": "Reason", "score": 95 }}
        ]
    }}
    """
    
    rank_res = gemini_api.ask_gemini(rank_prompt)
    if not rank_res: return

    rankings = rank_res.get("rankings", [])[:10]
    
    # 2-1. 랭킹 DB 저장 (live_rankings)
    db_rankings = []
    for item in rankings:
        db_rankings.append({
            "category": category,
            "rank": item.get("rank"),
            "title": item.get("keyword"), # DB 컬럼명이 title임
            "meta_info": item.get("meta", ""),
            "score": item.get("score", 0),
            "updated_at": datetime.now().isoformat()
        })
    database.save_rankings_to_db(db_rankings)

    # 3. [정밀 타격] Top 10 키워드별 기사 수집 및 요약
    news_data_list = []
    
    for idx, rank_item in enumerate(rankings):
        keyword = rank_item.get("keyword")
        print(f"   running ({idx+1}/10): {keyword}")
        
        # 기사 2개 검색
        target_items = naver_api.search_news_api(keyword, display=2)
        full_texts = []
        target_link = ""
        target_image = ""

        for item in target_items:
            link = item['link']
            crawled = naver_api.crawl_article(link) # 본문+이미지 가져옴
            
            if crawled['text']:
                full_texts.append(crawled['text'])
                if not target_image: target_image = crawled['image'] # 이미지 확보
                if not target_link: target_link = link
            else:
                full_texts.append(item['description']) # 실패시 요약본
                if not target_link: target_link = link

        if not full_texts: continue

        # 4. [요약] AI 기사 작성
        # live_news 테이블 스키마에 맞춤
        summary_prompt = f"""
        [Articles about '{keyword}']
        {str(full_texts)[:5000]}

        [Task]
        Write a news summary in Korean.
        [Output JSON]
        {{ "title": "Catchy Title", "summary": "3-sentence summary" }}
        """
        
        sum_res = gemini_api.ask_gemini(summary_prompt)
        
        if sum_res:
            news_data_list.append({
                "category": category,
                "keyword": keyword,
                "title": sum_res.get("title", f"{keyword} 소식"),
                "summary": sum_res.get("summary", ""),
                "link": target_link,
                "image_url": target_image, # 크롤링한 이미지
                "score": 100 - idx, # 1위일수록 높은 점수
                "created_at": datetime.now().isoformat(),
                "likes": 0
            })
        
        time.sleep(1) # AI 과부하 방지

    # 5. [뉴스 저장 & 청소]
    if news_data_list:
        database.save_news_to_db(news_data_list)
        database.cleanup_old_data(category, "live_news", config.MAX_ITEMS_PER_CATEGORY)
