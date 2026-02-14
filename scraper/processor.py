import time
from datetime import datetime
import config
import naver_api
import gemini_api
import database

def run_category_process(category):
    print(f"\n🚀 [Processing] Category: {category}")

    # ---------------------------------------------------------
    # 1단계: 100개 이상의 최신 뉴스 제목 수집 (광범위 검색)
    # ---------------------------------------------------------
    all_titles = []
    seen_links = set()
    print(f"   1️⃣ Collecting latest news titles for analysis...")
    
    queries = config.SEARCH_QUERIES.get(category, [])
    for q in queries:
        # 최신순(date)으로 각 쿼리당 50개씩 가져와서 중복 제거
        items = naver_api.search_news_api(q, display=50, sort='date')
        for item in items:
            if item['link'] not in seen_links:
                seen_links.add(item['link'])
                # 제목 내 HTML 태그 및 특수문자 제거
                clean_title = item['title'].replace("<b>","").replace("</b>","").replace("&quot;","")
                all_titles.append(clean_title)
        
        if len(all_titles) >= 120: break 
        time.sleep(0.3)

    if not all_titles:
        print(f"   ❌ No titles found for category: {category}")
        return

    # ---------------------------------------------------------
    # 2단계: 랭킹 1~10위 선정 및 기사 작성용 타겟 추출
    # ---------------------------------------------------------
    # 카테고리별 규칙 설정 (사용자 지시사항 반영)
    rank_rule = "Target(Rank): SONG / Search(Person): ARTIST" if category == "K-Pop" else \
                "Target(Rank): DRAMA / Search(Person): ACTOR" if category == "K-Drama" else \
                "Target(Rank): MOVIE / Search(Person): ACTOR" if category == "K-Movie" else \
                "Target(Rank): SHOW / Search(Person): CAST" if category == "K-Entertain" else \
                "Target: PLACE or TRADITION / Search: KEYWORD (EXCLUDE IDOLS)"

    print(f"   2️⃣ AI analyzing trends from {len(all_titles[:100])} titles...")
    rank_prompt = f"""
    Analyze these news titles about {category}. 
    
    [Task]
    1. Identify the TOP 10 {rank_rule.split('/')[0]} mentioned most frequently in these titles.
    2. Pick the SINGLE most trending {rank_rule.split('/')[1]} to be the subject of a deep-dive article.
    
    [Titles Data]
    {" | ".join(all_titles[:100])}
    
    [Important Rules]
    - 'search_keyword_kr' MUST be in KOREAN (e.g., '뉴진스', '이정재', '경복궁').
    - 'display_title_en' and 'top_subject_en' MUST be in ENGLISH.
    - For K-Culture: Strictly exclude K-Pop idols or celebrities.
    
    [Return JSON Format]
    {{
      "rankings": [ 
        {{
          "rank": 1, 
          "display_title_en": "English Title", 
          "search_keyword_kr": "한국어 검색어", 
          "meta": "Brief trending reason in English", 
          "score": 95
        }} 
      ],
      "top_person_kr": "한국어 검색어(가수/배우/장소명)",
      "top_subject_en": "English Subject Name for Database"
    }}
    """
    
    rank_res = gemini_api.ask_gemini(rank_prompt)
    if not rank_res or "rankings" not in rank_res:
        print("   ❌ AI failed to extract ranking data.")
        return

    # 라이브 랭킹 DB 업데이트
    database.save_rankings_to_db(rank_res.get("rankings", []))
    
    # ---------------------------------------------------------
    # 5단계 적용: 최근 4시간 내 사용된 키워드인지 확인 (중복 방지)
    # ---------------------------------------------------------
    target_kr = rank_res.get("top_person_kr") # 네이버 재검색용 (한국어)
    target_en = rank_res.get("top_subject_en") # DB 저장용 (영어)

    if database.is_keyword_used_recently(category, target_en, hours=4):
        print(f"   🕒 '{target_en}' is on 4-hour cooldown. Skipping article generation.")
        return

    # ---------------------------------------------------------
    # 3단계: 선택된 키워드로 정밀 검색 및 본문 3개 샘플링
    # ---------------------------------------------------------
    print(f"   3️⃣ Deep searching for '{target_kr}' (Sampling 3 valid articles)...")
    deep_items = naver_api.search_news_api(target_kr, display=10, sort='date')
    
    full_texts = []
    main_link = ""
    main_image = ""
    
    for item in deep_items:
        crawled = naver_api.crawl_article(item['link'])
        # 본문이 충분히 길고 유효한 경우만 수집
        if crawled['text'] and len(crawled['text']) > 300:
            full_texts.append(crawled['text'])
            if not main_link: main_link = item['link']
            if not main_image: main_image = crawled['image']
        
        # 3개의 성공적인 본문을 찾으면 중단
        if len(full_texts) >= 3:
            break

    if len(full_texts) < 1:
        print(f"   ❌ Could not retrieve enough article bodies for '{target_kr}'.")
        return

    # ---------------------------------------------------------
    # 4단계: 베테랑 기자 스타일로 새로운 영어 기사 작성
    # ---------------------------------------------------------
    print(f"   4️⃣ Writing Professional Article in English (20-year Veteran Style)...")
    article_prompt = f"""
    You are a veteran entertainment journalist with 20 years of experience. 
    Write a NEW, insightful professional news report in ENGLISH based on the provided 3 Korean articles.

    [Subject]
    {target_en} ({target_kr})

    [Source Material (Korean)]
    {str(full_texts)[:6000]}

    [Requirements]
    - Headline: Catchy, authoritative, and professional.
    - Content: Write 4-5 paragraphs of in-depth analysis. 
    - Style: Do NOT just summarize. Create a new narrative that connects the facts with expert insight.
    - Language: Perfect journalistic English.

    [Output JSON Format]
    {{ "title": "Headline", "content": "Full Professional Article Body" }}
    """
    
    news_res = gemini_api.ask_gemini(article_prompt)
    
    if news_res and news_res.get("content"):
        news_item = {
            "category": category,
            "keyword": target_en,
            "title": news_res.get("title"),
            "summary": news_res.get("content"), # 전문 내용을 summary 필드에 저장
            "link": main_link,
            "image_url": main_image,
            "score": 100,
            "created_at": datetime.now().isoformat(),
            "likes": 0
        }
        
        # 최종 DB 저장
        database.save_news_to_live([news_item])
        database.save_news_to_archive([news_item])
        database.cleanup_old_data(category, config.MAX_ITEMS_PER_CATEGORY)
        print(f"   🎉 SUCCESS: '{target_en}' article has been published.")
    else:
        print("   ❌ AI failed to generate the final article.")
