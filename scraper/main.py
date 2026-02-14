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

# API 키 확인
if GOOGLE_API_KEY:
    print(f"🔑 API Key 로드 완료: {GOOGLE_API_KEY[:5]}...")
else:
    print("❌ API Key가 없습니다!")

CATEGORIES = {
    "K-Pop": "k-pop latest news trends",
    "K-Drama": "k-drama ratings news",
    "K-Movie": "korean movie box office news",
    "K-Variety": "korean variety show news",
    "K-Culture": "seoul travel food trends"
}

# [핵심] 사용 가능한 모델을 동적으로 찾는 함수
def get_dynamic_model_url():
    print("🔍 구글 서버에 사용 가능한 모델 목록을 요청합니다...")
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GOOGLE_API_KEY}"
    
    try:
        response = requests.get(list_url)
        if response.status_code != 200:
            return "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
            
        data = response.json()
        models = data.get('models', [])
        
        valid_models = []
        for m in models:
            name = m['name'] 
            methods = m.get('supportedGenerationMethods', [])
            if 'generateContent' in methods and 'flash' in name:
                valid_models.append(name)
        
        if valid_models:
            best_model = valid_models[-1]
            print(f"✅ 사용 가능한 최적 모델 발견: {best_model}")
            return f"https://generativelanguage.googleapis.com/v1beta/{best_model}:generateContent"
        
        return "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

    except Exception as e:
        print(f"❌ 모델 탐색 중 에러: {e}")
        return "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

CURRENT_MODEL_URL = get_dynamic_model_url()

def search_web(keyword):
    """DuckDuckGo 검색 (이미지 포함)"""
    print(f"🔍 [Search] '{keyword}' 검색 중...")
    results = []
    try:
        with DDGS() as ddgs:
            # 1. 뉴스 검색
            ddg_results = list(ddgs.news(query=keyword, region="kr-kr", safesearch="off", max_results=10))
            
            # 2. 텍스트 검색 (백업)
            if not ddg_results:
                time.sleep(1)
                ddg_results = list(ddgs.text(query=keyword, region="kr-kr", max_results=5))

            for r in ddg_results:
                title = r.get('title', '')
                body = r.get('body', r.get('snippet', ''))
                link = r.get('url', r.get('href', ''))
                # ✅ [추가] 이미지 URL 추출 (없으면 빈 문자열)
                image = r.get('image', r.get('thumbnail', ''))

                if title and body:
                    # Gemini에게 줄 데이터에 이미지 정보도 포함시킴
                    results.append(f"제목: {title}\n내용: {body}\n링크: {link}\n이미지: {image}")
                
    except Exception as e:
        print(f"⚠️ 검색 중 오류 (건너뜀): {e}")
    
    return "\n\n".join(results)

def call_gemini_api(category_name, raw_data):
    print(f"🤖 [Gemini] '{category_name}' 분석 요청 중...")
    
    headers = {"Content-Type": "application/json"}
    
    # ✅ [수정] 프롬프트에 image_url 필드 추가 요청
    prompt = f"""
    You are a K-Entertainment news editor.
    Raw data: {raw_data[:20000]} 

    Task: Extract 10 news items and Top 10 rankings.
    IMPORTANT: You MUST include the 'image_url' from the raw data if available.

    Output must be strict JSON without Markdown.

    Format:
    {{
      "news_updates": [
        {{ 
          "keyword": "Subject", 
          "title": "Title", 
          "summary": "Summary", 
          "link": "URL",
          "image_url": "Image URL from Raw Data (or null)"
        }}
      ],
      "rankings": [
        {{ "rank": 1, "title": "Name", "meta": "Info", "score": 95 }}
      ]
    }}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        full_url = f"{CURRENT_MODEL_URL}?key={GOOGLE_API_KEY}"
        response = requests.post(full_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            try:
                text = response.json()['candidates'][0]['content']['parts'][0]['text']
                text = text.replace("```json", "").replace("```", "").strip()
                return json.loads(text)
            except Exception as e:
                print(f"   ⚠️ JSON 파싱 실패: {e}")
                return None
        else:
            print(f"   ❌ API 호출 실패 ({response.status_code}): {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"   ❌ 연결 오류: {e}")
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
                "image_url": item.get("image_url", ""), # ✅ DB에 이미지 저장
                "created_at": "now()",
                "likes": 0,    # 기본값
                "score": 50    # 기본값
            })
        
        try:
            # upsert 시 image_url도 같이 업데이트
            supabase.table("live_news").upsert(clean_news, on_conflict="category,keyword,title").execute()
            supabase.table("search_archive").upsert(clean_news, on_conflict="category,keyword,title").execute()
            print(f"   💾 뉴스 {len(clean_news)}개 저장 완료 (이미지 포함)")
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
                "score": item.get("score", 0), # ✅ 랭킹 점수도 저장
                "updated_at": "now()"
            })
        try:
            supabase.table("trending_rankings").upsert(clean_ranks, on_conflict="category,rank").execute()
            print(f"   🏆 랭킹 갱신 완료")
        except Exception as e:
             # 테이블 이름이 다를 수 있으니 에러 로그 확인용
             print(f"   ⚠️ 랭킹 저장 실패 (테이블 확인 필요): {e}")

def main():
    print(f"🚀 스크래퍼 시작 (Model: {CURRENT_MODEL_URL.split('/')[-1]})")
    
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
