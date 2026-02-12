import os
import sys
import json
import time
import requests
import re
from supabase import create_client, Client
from datetime import datetime, timedelta
from dateutil.parser import isoparse 
from dotenv import load_dotenv
from groq import Groq
from bs4 import BeautifulSoup

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

# [기존] RLS 문제 없이 관리자 권한으로 실행
supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    print("🚨 오류: .env 파일에 Supabase URL 또는 Key가 없습니다.")
    sys.exit(1)

supabase: Client = create_client(supabase_url, supabase_key)
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

CATEGORY_MAP = {
    "k-pop": ["컴백", "빌보드", "아이돌", "뮤직", "비디오", "챌린지", "포토카드", "월드투어", "가수"],
    "k-drama": ["드라마", "시청률", "넷플릭스", "OTT", "배우", "캐스팅", "대본리딩", "종영"],
    "k-movie": ["영화", "개봉", "박스오피스", "시사회", "영화제", "관객", "무대인사"],
    "k-entertain": ["예능", "유튜브", "개그맨", "코미디언", "방송", "개그우먼"],
    "k-culture": ["푸드", "뷰티", "웹툰", "팝업스토어", "패션", "음식", "해외반응"]
}

# [기존] AI 모델 동적 조회
def get_best_model():
    try:
        models_raw = groq_client.models.list()
        available_models = [m.id for m in models_raw.data]
        
        def model_scorer(model_id):
            score = 0
            model_id = model_id.lower()
            if "llama" in model_id: score += 1000
            elif "mixtral" in model_id: score += 500
            elif "gemma" in model_id: score += 100
            
            version_match = re.search(r'(\d+\.?\d*)', model_id)
            if version_match:
                try:
                    version = float(version_match.group(1))
                    score += version * 100 
                except: pass

            if "70b" in model_id: score += 50
            elif "8b" in model_id: score += 10
            if "versatile" in model_id: score += 5
            return score

        available_models.sort(key=model_scorer, reverse=True)
        print(f"🤖 AI 모델 우선순위: {available_models[:3]}")
        return available_models

    except Exception as e:
        print(f"⚠️ 모델 조회 실패, 기본값 사용: {e}")
        return ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]

MODELS_TO_TRY = get_best_model()

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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        res = requests.get(link, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        candidates = []

        main_content = soup.select_one('#dic_area, #articleBodyContents, .article_view, #articeBody, .news_view')
        if main_content:
            imgs = main_content.find_all('img')
            for i in imgs:
                src = i.get('src') or i.get('data-src')
                if src and 'http' in src:
                    width = i.get('width')
                    if width and width.isdigit() and int(width) < 200: continue
                    candidates.append(src)

        og = soup.find('meta', property='og:image')
        if og and og.get('content'): candidates.append(og['content'])

        for img_url in candidates:
            bad_keywords = r'logo|icon|button|share|banner|thumb|profile|default|ranking|news_stand|ssl.pstatic.net'
            if re.search(bad_keywords, img_url, re.IGNORECASE): continue
            return img_url
        return None
    except: return None

# [기존] 뉴스 요약 20~40%
def ai_category_editor(category, news_batch):
    if not news_batch: return []
    limited_batch = news_batch[:50]
    
    raw_text = ""
    for i, n in enumerate(limited_batch):
        clean_desc = n['description'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
        raw_text += f"[{i}] Title: {n['title']} / Context: {clean_desc}\n"
    
    prompt = f"""
    Task: Select highly relevant news items for '{category}'. 
    Target Quantity: Try to select up to 30 items if they are relevant.
    
    Constraints: 
    1. English Title: Translate naturally.
    2. English Summary: 
       - Write a DETAILED narrative summary (approx. 20-40% length of a typical article).
       - DO NOT use bullet points. Write 5-8 sentences in a cohesive paragraph.
       - Include Who, When, Where, Why based on the context.
    3. AI Score (0.0-10.0): Judge based on importance and trendiness.
    4. Return JSON format strictly.

    News List:
    {raw_text}

    Output JSON Format:
    {{
        "articles": [
            {{ "original_index": 0, "eng_title": "...", "summary": "Detailed summary...", "score": 8.5 }}
        ]
    }}
    """
    
    for model in MODELS_TO_TRY:
        try:
            res = groq_client.chat.completions.create(
                messages=[{"role": "system", "content": f"You are a K-Enter Journalist for {category}."},
                          {"role": "user", "content": prompt}], 
                model=model, 
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            articles = data.get('articles', [])
            if articles: return articles
        except Exception as e:
            print(f"      ⚠️ {model} 오류 ({str(e)[:60]}...). 다음 모델 시도.")
            continue
    return []

# [기존] 키워드 분석
def update_hot_keywords():
    print("📊 AI 키워드 트렌드 분석 시작...")
    res = supabase.table("live_news").select("title").order("created_at", desc=True).limit(100).execute()
    titles = [item['title'] for item in res.data]
    if not titles:
        print("   ⚠️ 분석할 기사가 없습니다.")
        return
    
    titles_text = "\n".join([f"- {t}" for t in titles])
    prompt = f"""
    Analyze the following K-Entertainment news titles and identify the TOP 10 most trending keywords.
    [Rules]
    1. Extract specific Entities: Person Name (e.g., "Lee Min-ho", NOT "Lee"), Group Name (e.g., "BTS"), Drama/Movie Title (e.g., "Squid Game").
    2. Merge related concepts: If "Jin" and "BTS" are both popular, use "BTS Jin".
    3. EXCLUDE generic words: Do NOT use words like "Variety", "Actor", "K-pop", "Review", "Netizens", "Update", "Official", "Comeback", "Teaser".
    4. Return JSON format with 'keyword' and estimated 'count' (importance score 1-100).
    [Titles]
    {titles_text}
    [Output Format JSON]
    {{
        "keywords": [
            {{ "keyword": "BTS Jin", "count": 95, "rank": 1 }},
            {{ "keyword": "Squid Game 2", "count": 80, "rank": 2 }}
        ]
    }}
    """
    
    for model in MODELS_TO_TRY:
        try:
            res = groq_client.chat.completions.create(
                messages=[{"role": "system", "content": "You are a K-Trend Analyst."},
                          {"role": "user", "content": prompt}], 
                model=model, 
                response_format={"type": "json_object"}
            )
            result = json.loads(res.choices[0].message.content)
            keywords = result.get('keywords', [])
            
            if not keywords: continue
            
            print(f"   🔥 AI가 추출한 진짜 트렌드: {[k.get('keyword') for k in keywords[:5]]}...")
            
            supabase.table("trending_keywords").delete().neq("id", 0).execute()
            
            insert_data = []
            for i, item in enumerate(keywords):
                insert_data.append({
                    "keyword": item.get('keyword'),
                    "count": item.get('count', 0),
                    "rank": item.get('rank', i + 1), 
                    "updated_at": datetime.now().isoformat()
                })
            
            if insert_data:
                supabase.table("trending_keywords").insert(insert_data).execute()
                print("   ✅ 키워드 랭킹 DB 업데이트 완료.")
                return 

        except Exception as e:
            print(f"      ⚠️ {model} 분석 실패: {e}")
            continue

# [신규 추가] 상위 랭크 기사 아카이빙 함수
def archive_top_articles():
    print("🗄️ 상위 랭크(Top 10) 기사 아카이빙 시작...")
    
    for category in CATEGORY_MAP.keys():
        # 각 카테고리별로 rank가 1~10등인 기사만 가져옴 (score 높은 순도 가능)
        res = supabase.table("live_news").select("*").eq("category", category).order("rank", ascending=True).limit(10).execute()
        top_articles = res.data
        
        if top_articles:
            # search_archive 테이블에 저장 (중복된 link가 있으면 업데이트)
            # 주의: search_archive 테이블이 존재해야 함
            try:
                supabase.table("search_archive").upsert(top_articles, on_conflict="link").execute()
                print(f"   💾 {category.upper()}: Top {len(top_articles)}개 -> 아카이브 저장 완료.")
            except Exception as e:
                print(f"   ⚠️ 아카이브 저장 실패 ({category}): {e}")

def run():
    print("🚀 7단계 마스터 엔진 가동 (30개 사수 + 아카이빙 + 동적 AI)...")
    
    for category, keywords in CATEGORY_MAP.items():
        print(f"📂 {category.upper()} 부문 처리 중...")

        # 1. 수집
        raw_news = []
        for kw in keywords: raw_news.extend(get_naver_api_news(kw))
        
        # 2. 중복 제거
        db_res = supabase.table("live_news").select("link").eq("category", category).execute()
        existing_links = {item['link'] for item in db_res.data}
        
        new_candidate_news = []
        seen_links = set()
        for n in raw_news:
            if n['link'] not in existing_links and n['link'] not in seen_links:
                new_candidate_news.append(n)
                seen_links.add(n['link'])
        
        print(f"   🔎 수집: {len(raw_news)}개 -> 기존 DB 중복 제외: {len(new_candidate_news)}개")

        # 3. AI 선별
        selected = ai_category_editor(category, new_candidate_news)
        print(f"   ㄴ AI 선별 완료: {len(selected)}개")

        # 4. 신규 뉴스 저장
        if selected:
            new_data_list = []
            for i, art in enumerate(selected):
                idx = art.get('original_index')
                if idx is None or idx >= len(new_candidate_news): continue
                
                orig = new_candidate_news[idx]
                img = get_article_image(orig['link']) or f"https://placehold.co/600x400/111/cyan?text={category}"

                new_data_list.append({
                    "rank": art.get('rank', 99), 
                    "category": category, 
                    "title": art.get('eng_title', orig['title']),
                    "summary": art.get('summary', 'Detailed summary not available.'), 
                    "link": orig['link'], 
                    "image_url": img,
                    "score": art.get('score', 5.0), 
                    "likes": 0, 
                    "dislikes": 0, 
                    "created_at": datetime.now().isoformat()
                })
            
            if new_data_list:
                supabase.table("live_news").upsert(new_data_list, on_conflict="link").execute()
                print(f"   ✅ 신규 {len(new_data_list)}개 DB 저장 완료.")

        # [조건 5 & 6] 스마트 삭제 로직 (무조건 30개 유지)
        res = supabase.table("live_news").select("id", "created_at", "score").eq("category", category).execute()
        all_articles = res.data
        total_count = len(all_articles)
        
        print(f"   📊 현재 DB 총 개수: {total_count}개 (목표: 30개 유지)")

        if total_count > 30:
            delete_ids = []
            
            # 전략 A: 24시간 지난 기사 삭제
            now = datetime.now()
            threshold = now - timedelta(hours=24)
            
            try:
                all_articles.sort(key=lambda x: isoparse(x['created_at']).replace(tzinfo=None))
            except: pass

            remaining_count = total_count
            
            for art in all_articles:
                try: art_date = isoparse(art['created_at']).replace(tzinfo=None)
                except: art_date = datetime(2000, 1, 1)

                if art_date < threshold:
                    if remaining_count > 30:
                        delete_ids.append(art['id'])
                        remaining_count -= 1
                    else: break

            # 전략 B: 점수 낮은 순 삭제
            if remaining_count > 30:
                survivors = [a for a in all_articles if a['id'] not in delete_ids]
                survivors.sort(key=lambda x: x['score'])
                
                for art in survivors:
                    if remaining_count > 30:
                        delete_ids.append(art['id'])
                        remaining_count -= 1
                    else: break

            if delete_ids:
                supabase.table("live_news").delete().in_("id", delete_ids).execute()
                print(f"   🧹 공간 확보: {len(delete_ids)}개 삭제 완료 (현재 {remaining_count}개 유지).")

    # [마지막 단계] 아카이빙 및 키워드 분석
    archive_top_articles() # [추가된 함수 호출]
    update_hot_keywords()
    
    print(f"🎉 모든 작업 완료.")

if __name__ == "__main__":
    run()
