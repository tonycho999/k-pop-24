import os
import sys
import json
import time
import requests
from supabase import create_client, Client
from datetime import datetime, timedelta
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY"))
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MODELS_TO_TRY = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile"]

# [수정] 카테고리별 키워드 매핑 (분할 수집을 위해)
CATEGORY_MAP = {
    "k-pop": ["컴백", "빌보드", "아이돌", "뮤직", "비디오", "챌린지", "포토카드", "월드투어", "가수"],
    "k-drama": ["드라마", "시청률", "넷플릭스", "OTT", "배우", "캐스팅", "대본리딩", "종영"],
    "k-movie": ["영화", "개봉", "박스오피스", "시사회", "영화제", "관객", "무대인사", "개봉"],
    "k-entertain": ["예능", "유튜브", "개그맨", "코미디언", "방송", "개그우먼"],
    "k-culture": ["푸드", "뷰티", "웹툰", "팝업스토어", "패션", "음식", "해외반응"]
}

def get_naver_api_news(keyword):
    import urllib.parse, urllib.request
    url = f"https://openapi.naver.com/v1/search/news?query={urllib.parse.quote(keyword)}&display=100&sort=sim"
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", os.environ.get("NAVER_CLIENT_ID"))
    req.add_header("X-Naver-Client-Secret", os.environ.get("NAVER_CLIENT_SECRET"))
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode('utf-8')).get('items', [])
    except: return []

def get_article_image(link):
    from bs4 import BeautifulSoup
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(link, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        og_image = soup.find('meta', property='og:image')
        return og_image['content'] if og_image else None
    except: return None

def ai_category_editor(category, news_batch):
    """특정 카테고리에 특화하여 30개를 반드시 선별하도록 요청"""
    # 너무 많은 입력은 AI가 혼란스러워하므로 상위 150개 정도로 제한
    limited_batch = news_batch[:150]
    raw_text = "\n".join([f"[{i}] {n['title']}" for i, n in enumerate(limited_batch)])
    
    prompt = f"""
    Task: Select the TOP 30 most buzzworthy news items for the '{category}' category from the list below.
    
    Constraints:
    1. You MUST select EXACTLY 30 items.
    2. Rank them from 1 to 30.
    3. Translate titles to English and write a 3-line English summary for each.
    4. Provide an AI Score (0.0 to 10.0) based on trend potential.

    List:
    {raw_text}

    Output JSON Format:
    {{
        "articles": [
            {{ "original_index": 0, "rank": 1, "category": "{category}", "eng_title": "...", "summary": "...", "score": 9.5 }}
        ]
    }}
    """
    
    for model in MODELS_TO_TRY:
        try:
            res = groq_client.chat.completions.create(
                messages=[{"role": "system", "content": "You are a professional K-Enter Editor."},
                          {"role": "user", "content": prompt}], 
                model=model, 
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content).get('articles', [])
        except: continue
    return []

def run():
    print("🚀 뉴스 엔진 가동 (분할 처리 모드)...")

    # 1. 24시간 지난 뉴스 삭제
    time_threshold = (datetime.now() - timedelta(hours=24)).isoformat()
    supabase.table("live_news").delete().lt("created_at", time_threshold).execute()

    # 2. 기존 live_news 백업 (좋아요 상위 10개)
    try:
        top_voted = supabase.table("live_news").select("*").order("likes", desc=True).limit(10).execute()
        for item in top_voted.data:
            archive_data = {
                "original_link": item['link'], "category": item['category'], "title": item['title'],
                "summary": item['summary'], "image_url": item['image_url'], "score": item['score'], "archive_reason": "Top 10 Likes"
            }
            supabase.table("search_archive").upsert(archive_data, on_conflict="original_link").execute()
    except: pass

    # 3. 신규 실시간 랭킹 데이터 삭제 (초기화)
    supabase.table("live_news").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    final_articles = []
    
    # [핵심] 카테고리별로 돌면서 수집 및 AI 분석
    for category, keywords in CATEGORY_MAP.items():
        print(f"📂 {category.upper()} 부문 수집 및 분석 시작...")
        cat_news = []
        for kw in keywords:
            cat_news.extend(get_naver_api_news(kw))
        
        # 중복 제거
        cat_news = list({n['link']: n for n in cat_news}.values())
        
        # AI에게 이 카테고리에서 30개 뽑으라고 명령
        selected = ai_category_editor(category, cat_news)
        print(f"   ㄴ AI 선별 완료: {len(selected)}개")
        
        # 실제 데이터 매칭 및 저장 준비
        for art in selected:
            idx = art['original_index']
            if idx >= len(cat_news): continue
            
            orig = cat_news[idx]
            img = get_article_image(orig['link'])
            if not img: img = f"https://placehold.co/600x400/111/cyan?text={category}"

            data = {
                "rank": art['rank'], # 카테고리 내 순위
                "category": category,
                "title": art['eng_title'],
                "summary": art['summary'],
                "link": orig['link'],
                "image_url": img,
                "score": art['score'],
                "likes": 0, "dislikes": 0,
                "created_at": datetime.now().isoformat()
            }
            
            # DB 저장
            supabase.table("live_news").insert(data).execute()
            
            # 아카이브 (카테고리 1~3위는 무조건 저장)
            if art['rank'] <= 3:
                archive_data = {
                    "original_link": orig['link'], "category": category, "title": art['eng_title'],
                    "summary": art['summary'], "image_url": img, "score": art['score'], "archive_reason": f"{category} Top 3"
                }
                supabase.table("search_archive").upsert(archive_data, on_conflict="original_link").execute()
            
            final_articles.append(data)

    print(f"🎉 최종 완료: 총 {len(final_articles)}개의 뉴스가 카테고리별로 업데이트되었습니다.")

if __name__ == "__main__":
    run()
