import os
import sys
import json
import time
import random
import requests
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

supabase: Client = create_client(os.environ.get("NEXT_PUBLIC_SUPABASE_URL"), os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY"))
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# [요구사항 2] 최신 모델부터 차례로 시도
MODELS_TO_TRY = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"]

# [요구사항 1] 보완 전략 키워드 전체 반영
SEARCH_KEYWORDS = [
    "컴백 초동 신기록", "아이돌 빌보드 독점", "뮤직비디오 1억뷰", "챌린지 유행", "엠카 1위", "아이돌 포토카드",
    "드라마 캐스팅 확정", "OTT 순위 1위", "드라마 제작발표회", "드라마 반전 결말", "인생 캐릭터 배우",
    "천만 영화 관객수", "영화제 수상 독점", "박스오피스 실시간 예매율", "영화 시사회 무대인사",
    "예능 대상 후보", "웹예능 유튜브 화제", "예능 시청률 대박", "예능 베스트 커플",
    "K-푸드 해외 반응", "K-뷰티 신상", "성수동 팝업스토어", "인기 웹툰 드라마화", "K-패션 글로벌 전시"
]

def get_naver_api_news(keyword):
    import urllib.parse, urllib.request
    url = f"https://openapi.naver.com/v1/search/news?query={urllib.parse.quote(keyword)}&display=20&sort=sim"
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", os.environ.get("NAVER_CLIENT_ID"))
    req.add_header("X-Naver-Client-Secret", os.environ.get("NAVER_CLIENT_SECRET"))
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read().decode('utf-8')).get('items', [])
    except: return []

def ai_chief_editor(news_batch):
    raw_text = "\n".join([f"[{i}] {n['title']}" for i, n in enumerate(news_batch)])
    prompt = f"""
    Task: Analyze these {len(news_batch)} news items. 
    1. Select exactly 30 news items and rank them 1 to 30 based on buzzworthiness.
    2. Categorize into [k-pop, k-drama, k-movie, k-entertain, k-culture].
    3. Generate a ONE-SENTENCE "Global Insight" based on REAL top news.
    
    News: {raw_text}
    
    Output JSON:
    {{
        "global_insight": "Actual trend summary...",
        "articles": [
            {{ "original_index": 0, "rank": 1, "category": "k-pop", "eng_title": "...", "summary": "3-line summary", "score": 9.5 }}
        ]
    }}
    """
    for model in MODELS_TO_TRY:
        try:
            res = groq_client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=model, response_format={"type": "json_object"})
            return json.loads(res.choices[0].message.content)
        except: continue
    return None

def run():
    print("🚀 뉴스 엔진 가동...")
    all_news = []
    for kw in SEARCH_KEYWORDS:
        all_news.extend(get_naver_api_news(kw))
    
    result = ai_chief_editor(all_news)
    if not result: return

    # [요구사항 4] 인사이트 업데이트 (별도 테이블 혹은 첫 번째 기사에 저장)
    global_insight = result.get('global_insight', "K-Enter news is trending worldwide.")
    
    # 기존 데이터 삭제 (Fresh Start)
    supabase.table("live_news").delete().neq("id", "0000").execute()

    for art in result.get('articles', []):
        orig = all_news[art['original_index']]
        data = {
            "rank": art['rank'],
            "category": art['category'],
            "title": art['eng_title'],
            "summary": art['summary'],
            "link": orig['link'],
            "score": art['score'],
            "insight": global_insight, # 모든 기사가 최신 인사이트를 공유하게 저장
            "likes": 0, "dislikes": 0,
            "created_at": datetime.now().isoformat()
        }
        supabase.table("live_news").insert(data).execute()
    print(f"✅ {len(result['articles'])}개 뉴스 랭킹 완료.")

if __name__ == "__main__":
    run()
