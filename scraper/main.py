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

# [Step 1의 연료] 키워드 맵 유지
CATEGORY_MAP = {
    "k-pop": ["컴백", "빌보드", "아이돌", "뮤직", "비디오", "챌린지", "포토카드", "월드투어", "가수"],
    "k-drama": ["드라마", "시청률", "넷플릭스", "OTT", "배우", "캐스팅", "대본리딩", "종영"],
    "k-movie": ["영화", "개봉", "박스오피스", "시사회", "영화제", "관객", "무대인사"],
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
    """Step 3: 분류 및 평점 부여"""
    if not news_batch: return []
    limited_batch = news_batch[:150]
    raw_text = "\n".join([f"[{i}] {n['title']}" for i, n in enumerate(limited_batch)])
    
    prompt = f"""
    Task: Select the top buzzworthy news for '{category}'. 
    Constraints: 
    - Select up to 30 items. 
    - Rank 1-30. 
    - Translate title to English & 3-line English summary. 
    - Provide AI Score (0.0-10.0).
    Output JSON: {{ "articles": [ {{ "original_index": 0, "rank": 1, "category": "{category}", "eng_title": "...", "summary": "...", "score": 9.5 }} ] }}
    """
    
    for model in MODELS_TO_TRY:
        try:
            res = groq_client.chat.completions.create(
                messages=[{"role": "system", "content": "You are a professional K-Enter Editor."},
                          {"role": "user", "content": prompt}], 
                model=model, response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content).get('articles', [])
        except: continue
    return []

def run():
    print("🚀 7단계 마스터 엔진 가동 (카테고리별 30개 유지)...")
    total_added = 0
    
    for category, keywords in CATEGORY_MAP.items():
        print(f"📂 {category.upper()} 부문 처리 중...")

        # 1. 수집 (Maximum Fetch)
        raw_news = []
        for kw in keywords:
            raw_news.extend(get_naver_api_news(kw))
        
        # 2. 중복 제거 (Dedupe) - 링크 기준
        deduped_news = list({n['link']: n for n in raw_news}.values())
        print(f"   🔎 수집: {len(raw_news)}개 -> 중복제거 후: {len(deduped_news)}개")

        # 3. 분류 및 평점 (AI Scoring)
        selected = ai_category_editor(category, deduped_news)
        num_new = len(selected)
        print(f"   ㄴ AI 선별 완료: {num_new}개")

        if num_new > 0:
            # 4. 슬롯 체크 (Slot Check)
            res = supabase.table("live_news").select("id", "created_at", "score").eq("category", category).execute()
            existing = res.data
            current_count = len(existing)

            # 삭제 필요한 수량 계산 (총합이 30개를 넘는 만큼)
            num_to_delete = max(0, (current_count + num_new) - 30)

            if num_to_delete > 0:
                # 5. 노후화 삭제 (Time-based Clean) & 6. 저득점 삭제 (Quality-based Clean)
                # 정렬 기준: 1순위 시간(오래된 순), 2순위 점수(낮은 순)
                existing.sort(key=lambda x: (x['created_at'], x['score']))
                
                delete_ids = [item['id'] for item in existing[:num_to_delete]]
                supabase.table("live_news").delete().in_("id", delete_ids).execute()
                print(f"   🧹 슬롯 확보: {len(delete_ids)}개 삭제 완료 (시간/점수 기준)")

            # 7. 최종 저장 (Final Upsert)
            new_data_list = []
            for art in selected:
                idx = art['original_index']
                if idx >= len(deduped_news): continue
                orig = deduped_news[idx]
                img = get_article_image(orig['link']) or f"https://placehold.co/600x400/111/cyan?text={category}"

                new_data_list.append({
                    "rank": art['rank'], "category": category, "title": art['eng_title'],
                    "summary": art['summary'], "link": orig['link'], "image_url": img,
                    "score": art['score'], "likes": 0, "dislikes": 0, "created_at": datetime.now().isoformat()
                })

            if new_data_list:
                supabase.table("live_news").insert(new_data_list).execute()
                total_added += len(new_data_list)
                print(f"   ✅ {category} 업데이트 성공 (슬롯 30개 유지)")

    print(f"🎉 작업 완료: 총 {total_added}개 기사 갱신.")

if __name__ == "__main__":
    run()
