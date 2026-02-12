import os
import sys
import json
import time
import random
import requests
from supabase import create_client, Client
from datetime import datetime, timedelta  # timedelta 추가
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY"))
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MODELS_TO_TRY = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"]

SEARCH_KEYWORDS = [
    "컴백", "빌보드", "데뷔", "월드투어", "독점", "가수", "아이돌",
    "뮤직비디오", "챌린지", "유행", "엠카", "포토카드",
    "시청률", "종영", "넷플릭스", "대본리딩", "배우",
    "드라마", "캐스팅", "OTT", "제작발표회", "반전 결말", "개봉",
    "영화", "관객수", "박스오피스", "시사회", "무대인사",
    "예능", "대상 후보", "유튜브", "개그맨", "개그우먼", "코미디언",
    "푸드", "해외 반응", "뷰티", "팝업스토어", "웹툰", "패션", "음식"
]

def get_naver_api_news(keyword):
    import urllib.parse, urllib.request
    # display를 100으로 늘려 더 많은 뉴스 수집
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

def ai_chief_editor(news_batch):
    raw_text = "\n".join([f"[{i}] {n['title']}" for i, n in enumerate(news_batch)])
    # 30개 제한을 100개(최대치)로 확장
    prompt = f"""
    Task: Analyze these {len(news_batch)} news items. 
    1. Select as many news items as possible (up to 100) and rank them by buzzworthiness.
    2. Categorize into [k-pop, k-drama, k-movie, k-entertain, k-culture].
    3. Generate a ONE-SENTENCE "Global Insight" based on the REAL trends found in these news titles. 
    
    Output JSON:
    {{
        "global_insight": "Actual trend summary...",
        "articles": [
            {{ "original_index": 0, "rank": 1, "category": "k-pop", "eng_title": "...", "summary": "3-line English summary", "score": 9.5 }}
        ]
    }}
    """
    for model in MODELS_TO_TRY:
        try:
            print(f"🤖 AI 분석 중... (모델: {model})")
            res = groq_client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=model, response_format={"type": "json_object"})
            return json.loads(res.choices[0].message.content)
        except: continue
    return None

def run():
    print("🚀 뉴스 엔진 가동...")

    # [수정 사항 2] 24시간 지난 뉴스 삭제
    time_threshold = (datetime.now() - timedelta(hours=24)).isoformat()
    print(f"🧹 24시간 경과 데이터 삭제 중... (기준: {time_threshold})")
    supabase.table("live_news").delete().lt("created_at", time_threshold).execute()

    # [수정 사항 3] 좋아요 순위 Top 10 아카이브 저장
    # 현재 live_news에서 좋아요가 많은 순으로 10개를 가져와 아카이브로 복사
    print("⭐ 좋아요 Top 10 아카이브 저장 중...")
    try:
        top_voted = supabase.table("live_news").select("*").order("likes", desc=True).limit(10).execute()
        for item in top_voted.data:
            archive_data = {
                "original_link": item['link'],
                "category": item['category'],
                "title": item['title'],
                "summary": item['summary'],
                "image_url": item['image_url'],
                "score": item['score'],
                "archive_reason": "Top 10 Likes"
            }
            supabase.table("search_archive").upsert(archive_data, on_conflict="original_link").execute()
    except Exception as e:
        print(f"⚠️ 좋아요 아카이브 실패: {e}")

    # 뉴스 수집
    all_news = []
    for kw in SEARCH_KEYWORDS:
        all_news.extend(get_naver_api_news(kw))
    
    # 중복 제거 (링크 기준)
    unique_news = {n['link']: n for n in all_news}.values()
    all_news = list(unique_news)

    print(f"🔍 {len(all_news)}건 수집 완료. AI 랭킹 분석 시작...")
    result = ai_chief_editor(all_news)
    if not result: return

    global_insight = result.get('global_insight', "Global entertainment is evolving with K-Wave's latest innovations.")
    
    # 새로운 랭킹 반영을 위해 기존 랭킹 데이터 삭제 (ID가 0인 것 제외)
    supabase.table("live_news").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    saved = 0
    for art in result.get('articles', []):
        idx = art['original_index']
        if idx >= len(all_news): continue
        orig = all_news[idx]
        
        img = get_article_image(orig['link'])
        if not img: img = f"https://placehold.co/600x400/111/cyan?text={art['category']}"

        data = {
            "rank": art['rank'],
            "category": art['category'],
            "title": art['eng_title'],
            "summary": art['summary'],
            "link": orig['link'],
            "image_url": img,
            "score": art['score'],
            "insight": global_insight,
            "likes": 0, "dislikes": 0,
            "created_at": datetime.now().isoformat()
        }
        
        # 1. 실시간 뉴스 저장
        supabase.table("live_news").insert(data).execute()
        
        # [수정 사항 3] 랭킹 10위권 이내 아카이브 영구 저장
        if art['rank'] <= 10:
            archive_data = {
                "original_link": orig['link'],
                "category": art['category'],
                "title": art['eng_title'],
                "summary": art['summary'],
                "image_url": img,
                "score": art['score'],
                "archive_reason": "Top 10 Rank"
            }
            supabase.table("search_archive").upsert(archive_data, on_conflict="original_link").execute()
            
        saved += 1
        if saved % 10 == 0: print(f"✅ {saved}개 처리 중...")

    print(f"=== 최종 완료: {saved}개 뉴스 업데이트 ===")

if __name__ == "__main__":
    run()
