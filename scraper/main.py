import os
import json
import time
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
from ddgs import DDGS

# 1. 환경변수 로드
load_dotenv()

# 2. Supabase 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. Gemini API 키 설정
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# API 키 확인 (보안을 위해 앞 5자리만 출력)
if GOOGLE_API_KEY:
    print(f"🔑 API Key 로드 완료: {GOOGLE_API_KEY[:5]}...")
else:
    print("❌ API Key가 설정되지 않았습니다! GitHub Secrets를 확인하세요.")

CATEGORIES = {
    "K-Pop": "k-pop latest news trends",
    "K-Drama": "k-drama ratings news",
    "K-Movie": "korean movie box office news",
    "K-Variety": "korean variety show news",
    "K-Culture": "seoul travel food trends"
}

def search_web(keyword):
    """DuckDuckGo 검색 (안정성 강화)"""
    print(f"🔍 [Search] '{keyword}' 검색 중...")
    results = []
    try:
        with DDGS() as ddgs:
            # 1. 뉴스 검색 (파라미터: query)
            ddg_results = list(ddgs.news(query=keyword, region="kr-kr", safesearch="off", max_results=10))
            
            # 2. 텍스트 검색 (뉴스 없을 경우)
            if not ddg_results:
                time.sleep(1)
                ddg_results = list(ddgs.text(query=keyword, region="kr-kr", max_results=5))

            for r in ddg_results:
                title = r.get('title', '')
                body = r.get('body', r.get('snippet', ''))
                link = r.get('url', r.get('href', ''))
                if title and body:
                    results.append(f"제목: {title}\n내용: {body}\n링크: {link}")
                
    except Exception as e:
        print(f"⚠️ 검색 중 오류 (건너뜀): {e}")
    
    return "\n\n".join(results)

def call_gemini_api(category_name, raw_data):
    print(f"🤖 [Gemini] '{category_name}' 분석 요청 중...")
    
    # [핵심 수정] 정식 버전(v1)과 구체적인 모델명 사용
    endpoints = [
        # 1순위: 1.5 Flash 정식 버전 (v1beta -> v1)
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
        # 2순위: 1.5 Flash 구체적 버전 (001)
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-001:generateContent",
        # 3순위: 구형 Pro 모델 (최후의 보루)
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
    ]
    
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""
    You are a K-Entertainment news editor.
    Raw data: {raw_data[:15000]} 

    Task: Extract 10 news items and Top 10 rankings.
    Output must be strict JSON without Markdown code blocks.

    Format:
    {{
      "news_updates": [
        {{ "keyword": "Subject", "title": "Title", "summary": "Summary", "link": "URL" }}
      ],
      "rankings": [
        {{ "rank": 1, "title": "Name", "meta": "Info" }}
      ]
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for url in endpoints:
        try:
            full_url = f"{url}?key={GOOGLE_API_KEY}"
            response = requests.post(full_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                print(f"   ✅ 성공! (모델: {url.split('models/')[1].split(':')[0]})")
                try:
                    text = response.json()['candidates'][0]['content']['parts'][0]['text']
                    # JSON 클리닝
                    text = text.replace("```json", "").replace("```", "").strip()
                    return json.loads(text)
                except Exception as e:
                    print(f"   ⚠️ JSON 파싱 실패: {e}")
                    continue 
            else:
                # [디버깅] 왜 실패했는지 상세 메시지 출력
                print(f"   ⚠️ 실패 ({response.status_code}): {response.text[:200]}")
                continue
                
        except Exception as e:
            print(f"   ❌ 연결 오류: {e}")
            continue

    print("❌ 모든 모델 시도 실패")
    return None

def update_database(category, data):
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
            supabase.table("live_news").upsert(clean_news, on_conflict="category,keyword,title").execute()
            supabase.table("search_archive").upsert(clean_news, on_conflict="category,keyword,title").execute()
            print(f"   💾 뉴스 {len(clean_news)}개 저장 완료")
        except Exception as e:
            print(f"   ⚠️ 뉴스 저장 실패: {e}")

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
    print("🚀 스크래퍼 시작 (Direct REST API v1)")
    
    for category, search_keyword in CATEGORIES.items():
        raw_text = search_web(search_keyword)
        
        if len(raw_text) < 10: 
            print(f"⚠️ {category} 정보 부족으로 건너뜀")
            continue

        data = call_gemini_api(category, raw_text)
        
        if data:
            update_database(category, data)
        
        time.sleep(3)

    print("✅ 모든 작업 완료")

if __name__ == "__main__":
    main()
