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

if GOOGLE_API_KEY:
    print(f"🔑 API Key 로드 완료: {GOOGLE_API_KEY[:5]}...")
else:
    print("❌ API Key가 없습니다!")

# ✅ [수정 1] K-Variety -> K-Entertain으로 변경 (DB 저장 이름도 바뀜)
CATEGORIES = {
    "K-Pop": "k-pop latest news trends",
    "K-Drama": "k-drama ratings news",
    "K-Movie": "korean movie box office news",
    "K-Entertain": "korean variety show news reality show trends", 
    "K-Culture": "seoul travel food trends"
}

def get_dynamic_model_url():
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
            print(f"✅ 최적 모델 발견: {valid_models[-1]}")
            return f"https://generativelanguage.googleapis.com/v1beta/{valid_models[-1]}:generateContent"
        return "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    except Exception:
        return "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

CURRENT_MODEL_URL = get_dynamic_model_url()

def get_fallback_image(keyword):
    """뉴스에 이미지가 없을 때, 이미지 검색을 통해 강제로 찾아내는 함수"""
    try:
        with DDGS() as ddgs:
            imgs = list(ddgs.images(keywords=keyword, region="kr-kr", safesearch="off", max_results=1))
            if imgs and len(imgs) > 0:
                return imgs[0].get('image')
    except Exception:
        return ""
    return ""

def search_web(keyword):
    """DuckDuckGo 검색: HTTPS만 수집 + 이미지 필수 + 내용 충실"""
    print(f"🔍 [Search] '{keyword}' 검색 중...")
    results = []
    
    try:
        with DDGS() as ddgs:
            # 1. 뉴스 검색
            ddg_results = list(ddgs.news(query=keyword, region="kr-kr", safesearch="off", max_results=15))
            
            for r in ddg_results:
                title = r.get('title', '')
                body = r.get('body', r.get('snippet', ''))
                link = r.get('url', r.get('href', ''))
                image = r.get('image', r.get('thumbnail', ''))

                # [필수] 제목, 본문, HTTPS 링크 체크
                if not title or not body or not link or not link.startswith("https"):
                    continue

                # ✅ 이미지가 없으면 -> 별도로 이미지 검색
                if not image:
                    image = get_fallback_image(title)
                    time.sleep(0.5) 

                # ✅ 그래도 이미지가 없으면? 과감히 버림 (이미지 필수 정책)
                if not image:
                    continue

                results.append(f"제목: {title}\n내용: {body}\n링크: {link}\n이미지: {image}")
                
    except Exception as e:
        print(f"⚠️ 검색 중 오류 (건너뜀): {e}")
    
    return "\n\n".join(results)

def call_gemini_api(category_name, raw_data):
    print(f"🤖 [Gemini] '{category_name}' 기사 작성 중 (20년차 베테랑 모드)...")
    
    headers = {"Content-Type": "application/json"}
    
    # ✅ [수정 2] 베테랑 기자 프롬프트 + 글자수 제한 (100~500자)
    prompt = f"""
    [Role]
    You are a veteran K-Entertainment journalist with 20 years of experience.
    Your writing style is analytical, insightful, and engaging. You provide context, not just facts.

    [Input Data]
    {raw_data[:20000]} 

    [Task]
    Select the Top 10 most impactful news items for '{category_name}' and rewrite them.
    
    [Content Requirements - STRICT]
    1. **Length**: Each summary MUST be between **100 and 500 characters** (Korean). Not too short, not too long.
    2. **Depth**: Include the background of the event or the public's reaction. Explain WHY this is important.
    3. **Tone**: Professional journalistic tone (e.g., "~할 것으로 보인다", "~에 이목이 집중된다").
    4. **Image**: You MUST map the 'image_url' from the raw data exactly.

    [Output Format (JSON Only)]
    {{
      "news_updates": [
        {{ 
          "keyword": "Main Subject", 
          "title": "Compelling Title (Korean)", 
          "summary": "Detailed Article (Korean, 100-500 chars)", 
          "link": "Original Link",
          "image_url": "URL starting with https"
        }}
      ],
      "rankings": [
        {{ "rank": 1, "title": "Name", "meta": "Short Info", "score": 98 }}
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
        elif response.status_code == 429:
            print(f"   ❌ API 한도 초과 (429): 잠시 대기 필요")
            return None
        elif response.status_code == 503:
             print(f"   ❌ 서버 과부하 (503): 잠시 대기 필요")
             return None
        else:
            print(f"   ❌ API 호출 실패 ({response.status_code}): {response.text[:200]}")
            return None
    except Exception as e:
        print(f"   ❌ 연결 오류: {e}")
        return None

def update_database(category, data):
    # 뉴스 저장
    news_list = data.get("news_updates", [])
    if news_list:
        clean_news = []
        for item in news_list:
            if not item.get("image_url"): continue

            summary = item.get("summary", "")
            
            # (옵션) 혹시라도 너무 짧으면 저장 안 하거나 점수 깎음
            if len(summary) < 50: 
                print(f"   ⚠️ 기사 내용이 너무 짧음 ({len(summary)}자). 건너뜀.")
                continue

            clean_news.append({
                "category": category,
                "keyword": item.get("keyword", category),
                "title": item.get("title", "제목 없음"),
                "summary": summary,
                "link": item.get("link", ""),
                "image_url": item.get("image_url"),
                "created_at": "now()",
                "likes": 0,
                "score": 80 + (len(summary) / 10) # 긴 글일수록 점수 높게 책정
            })
        
        if clean_news:
            try:
                supabase.table("live_news").upsert(clean_news, on_conflict="category,keyword,title").execute()
                supabase.table("search_archive").upsert(clean_news, on_conflict="category,keyword,title").execute()
                print(f"   💾 뉴스 {len(clean_news)}건 저장 완료")
            except Exception as e:
                print(f"   ⚠️ 뉴스 저장 실패: {e}")

    # 랭킹 저장 (live_rankings)
    rank_list = data.get("rankings", [])
    if rank_list:
        clean_ranks = []
        for item in rank_list:
            clean_ranks.append({
                "category": category,
                "rank": item.get("rank"),
                "title": item.get("title"),
                "meta_info": item.get("meta", ""),
                "score": item.get("score", 0),
                "updated_at": "now()"
            })
        try:
            supabase.table("live_rankings").upsert(clean_ranks, on_conflict="category,rank").execute()
            print(f"   🏆 랭킹 갱신 완료")
        except Exception as e:
             print(f"   ⚠️ 랭킹 저장 실패: {e}")

def main():
    print(f"🚀 스크래퍼 시작 (Veteran Journalist Mode)")
    for category, search_keyword in CATEGORIES.items():
        raw_text = search_web(search_keyword)
        
        if len(raw_text) < 50: 
            print(f"⚠️ {category} : 뉴스 데이터 부족으로 건너뜀")
            continue

        data = call_gemini_api(category, raw_text)
        if data:
            update_database(category, data)
        
        # 429 에러 방지용 대기
        print("⏳ 다음 카테고리 분석 전 15초 대기...")
        time.sleep(15) 

    print("✅ 모든 작업 완료")

if __name__ == "__main__":
    main()
