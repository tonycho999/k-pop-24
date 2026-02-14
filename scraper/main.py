import os
import json
import time
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv
from duckduckgo_search import DDGS

# 1. 환경변수 로드
load_dotenv()

# 2. Supabase 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. Gemini 설정
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# [핵심 수정] 모델 자동 복구 시스템
def get_working_model():
    """
    1순위(Flash)가 안 되면 2순위(Pro)를 돌려주는 똑똑한 함수입니다.
    """
    candidates = [
        "gemini-1.5-flash",        # 1순위: 최신/빠름/무료
        "gemini-1.5-flash-latest", # 1.5 다른 이름
        "gemini-pro",              # 2순위: 구버전/매우안정적
        "models/gemini-1.5-flash"  # 접두어 붙은 버전
    ]
    
    print("🚑 작동 가능한 AI 모델을 찾는 중...")
    for model_name in candidates:
        try:
            # 테스트용으로 살짝 찔러봅니다.
            test_model = genai.GenerativeModel(model_name)
            test_model.generate_content("Hi")
            print(f"✅ 모델 확정: {model_name}")
            return test_model
        except Exception:
            continue # 실패하면 다음 후보로

    print("⚠️ 모든 신형 모델 실패. 'gemini-pro'로 강제 설정합니다.")
    return genai.GenerativeModel("gemini-pro")

# 확정된 모델 로드
model = get_working_model()

# 검색어 최적화 (너무 길면 검색 안됨)
CATEGORIES = {
    "K-Pop": "k-pop latest news trends",
    "K-Drama": "k-drama ratings news",
    "K-Movie": "korean movie box office news",
    "K-Variety": "korean variety show news",
    "K-Culture": "seoul travel food trends"
}

def search_web(keyword):
    """DuckDuckGo 검색 (에러 처리 강화)"""
    print(f"🔍 [Search] '{keyword}' 검색 중...")
    results = []
    try:
        # max_results를 조금 줄여서 속도 향상
        with DDGS() as ddgs:
            ddg_results = list(ddgs.news(keywords=keyword, region="kr-kr", safesearch="off", max_results=10))
            
            if not ddg_results:
                # 뉴스 검색 실패시 일반 검색 시도
                print(f"   ⚠️ 뉴스 검색 실패, 일반 검색으로 재시도...")
                ddg_results = list(ddgs.text(keywords=keyword, region="kr-kr", max_results=5))

            for r in ddg_results:
                # title과 body(또는 snippet)가 있는 경우만 수집
                title = r.get('title', '')
                body = r.get('body', r.get('snippet', ''))
                link = r.get('url', r.get('href', ''))
                if title and body:
                    results.append(f"제목: {title}\n내용: {body}\n링크: {link}")
                
    except Exception as e:
        print(f"⚠️ 검색 중 오류 발생: {e}")
    
    return "\n\n".join(results)

def fetch_data_from_gemini(category_name, raw_data):
    print(f"🤖 [Gemini] '{category_name}' 요약 및 정리 중...")
    
    prompt = f"""
    [Role]
    You are a K-Entertainment news editor.
    
    [Context]
    Raw search data for '{category_name}':
    {raw_data[:10000]} 

    [Task]
    Extract 10 news items and Top 10 rankings.
    Output must be strict JSON.

    [Output Format (JSON Only)]
    {{
      "news_updates": [
        {{
          "keyword": "Core Keyword",
          "title": "Korean Title",
          "summary": "Korean Summary (1 sentence)",
          "link": "URL"
        }}
      ],
      "rankings": [
        {{ "rank": 1, "title": "Name", "meta": "Info" }}
      ]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"❌ [Error] AI 응답 실패: {e}")
        return None

def update_database(category, data):
    # 1. 뉴스 저장
    news_list = data.get("news_updates", [])
    if news_list:
        clean_news = []
        for item in news_list:
            clean_news.append({
                "category": category,
                "keyword": item.get("keyword", category),
                "title": item.get("title", "제목 없음"),
                "summary": item.get("summary", ""),
                "link": item.get("link", ""),
                "created_at": "now()"
            })
        
        try:
            # 라이브 & 아카이브 동시 저장
            supabase.table("live_news").upsert(clean_news, on_conflict="category,keyword,title").execute()
            supabase.table("search_archive").upsert(clean_news, on_conflict="category,keyword,title").execute()
            print(f"   💾 뉴스 {len(clean_news)}개 저장 완료")
        except Exception as e:
            print(f"   ⚠️ 뉴스 저장 실패: {e}")

    # 2. 랭킹 저장
    rank_list = data.get("rankings", [])
    if rank_list:
        clean_ranks = []
        for item in rank_list:
            clean_ranks.append({
                "category": category,
                "rank": item.get("rank"),
                "title": item.get("title"),
                "meta_info": item.get("meta", ""),
                "updated_at": "now()"
            })
        try:
            supabase.table("live_rankings").upsert(clean_ranks, on_conflict="category,rank").execute()
            print(f"   🏆 랭킹 갱신 완료")
        except Exception:
            pass

def main():
    print("🚀 스크래퍼 시작 (DuckDuckGo + Auto-Gemini)")
    
    for category, search_keyword in CATEGORIES.items():
        # 1. 검색
        raw_text = search_web(search_keyword)
        
        if len(raw_text) < 50:
            print(f"⚠️ {category} 정보 부족으로 건너뜀")
            continue

        # 2. AI 요약
        data = fetch_data_from_gemini(category, raw_text)
        
        # 3. 저장
        if data:
            update_database(category, data)
        
        time.sleep(5) # 차단 방지 대기

    print("✅ 모든 작업 완료")

if __name__ == "__main__":
    main()
