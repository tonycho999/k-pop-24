import os
import json
import time
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 1. 설정: Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. 설정: Google Gemini
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") 
genai.configure(api_key=GOOGLE_API_KEY)

def get_best_flash_model():
    """
    사용 가능한 모델 목록을 조회하여, 
    무료 사용량이 넉넉한 'Flash' 계열 중 가장 최신 모델을 자동으로 선택합니다.
    """
    try:
        # 1. 모든 모델 목록 조회
        print("🔍 최신 AI 모델 탐색 중...")
        models = genai.list_models()
        
        # 2. 'generateContent' 기능이 있고, 이름에 'flash'가 포함된 모델만 필터링
        flash_models = []
        for m in models:
            if 'generateContent' in m.supported_generation_methods and 'flash' in m.name:
                flash_models.append(m.name)
        
        # 3. 모델이 있다면 정렬해서 가장 최신 것(버전 숫자가 높은 것) 선택
        if flash_models:
            # 보통 문자열 정렬 시 숫자가 높은 게 뒤로 감 (1.5 < 2.0)
            best_model = sorted(flash_models)[-1]
            print(f"✅ 선택된 최적 모델: {best_model}")
            return best_model
        
        # 4. Flash 모델을 못 찾으면 안전한 기본값 사용
        print("⚠️ Flash 모델을 찾지 못해 기본값(1.5-flash)을 사용합니다.")
        return 'models/gemini-1.5-flash'
        
    except Exception as e:
        print(f"⚠️ 모델 탐색 중 에러 발생({e}). 기본값을 사용합니다.")
        return 'models/gemini-1.5-flash'

# 동적으로 모델 선택
SELECTED_MODEL_NAME = get_best_flash_model()
model = genai.GenerativeModel(SELECTED_MODEL_NAME, tools='google_search_retrieval')

# 카테고리 정의
CATEGORIES = {
    "K-Pop": {
        "news_focus": "가수, 아이돌, 그룹 멤버의 활동 및 이슈",
        "rank_focus": "현재 음원 차트 상위권 노래 제목(Song Title)"
    },
    "K-Drama": {
        "news_focus": "드라마 출연 배우의 캐스팅, 인터뷰, 논란",
        "rank_focus": "현재 방영중이거나 OTT 상위권 드라마 제목(Drama Title)"
    },
    "K-Movie": {
        "news_focus": "영화 배우의 동향, 무대인사, 인터뷰",
        "rank_focus": "현재 박스오피스 상위권 영화 제목(Movie Title)"
    },
    "K-Variety": {
        "news_focus": "예능인, 방송인, 패널의 에피소드",
        "rank_focus": "현재 방영중인 예능 프로그램 제목(Show Title)"
    },
    "K-Culture": {
        "news_focus": "핫플레이스, 축제, 팝업스토어 (장소/Place 위주)",
        "rank_focus": "유행하는 음식, 뷰티템, 패션, 밈 (물건/Item 위주)"
    }
}

def fetch_data_from_gemini(category_name, instructions):
    print(f"🤖 [Gemini] '{category_name}' 검색 및 분석 중... (Model: {SELECTED_MODEL_NAME})")
    
    prompt = f"""
    [Role]
    당신은 20년 경력의 연예부 기자입니다. 팩트에 기반한 최신 트렌드를 분석합니다.

    [Task]
    현재 시점(Latest)의 '{category_name}' 관련 데이터를 검색하여 JSON으로 작성하십시오.

    [Requirements]
    1. **뉴스(News)**: {instructions['news_focus']} 중심으로 화제가 높은 10개를 선정하십시오.
       - 중복된 주제는 피하고 다양하게 구성하십시오.
       - 요약은 150자 내외로 핵심만 담으십시오.
    2. **랭킹(Ranking)**: {instructions['rank_focus']} 중심으로 인기 순위 TOP 10을 선정하십시오.
       - 뉴스에 나온 내용과 겹치지 않게 '작품/대상' 위주로 뽑으십시오.
       - 절대 중복된 항목이 있어서는 안 됩니다.

    [Output Format (JSON Only)]
    {{
      "news_updates": [
        {{
          "keyword": "주제어 (예: 뉴진스, 김수현)",
          "title": "기사 제목",
          "summary": "기사 요약",
          "link": "관련 기사 링크 (없으면 검색된 출처)"
        }},
        ... (10 items)
      ],
      "rankings": [
        {{ "rank": 1, "title": "제목/이름", "meta": "부가정보 (가수명/방송사 등)" }},
        ... (10 items)
      ]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"❌ [Error] {category_name} 처리 중 오류: {e}")
        return None

def update_database(category, data):
    # 1. 뉴스 저장 (Smart Upsert)
    news_list = data.get("news_updates", [])
    if news_list:
        clean_news = []
        for item in news_list:
            clean_news.append({
                "category": category,
                "keyword": item["keyword"],
                "title": item["title"],
                "summary": item["summary"],
                "link": item.get("link", ""),
                "created_at": "now()"
            })
        
        try:
            supabase.table("live_news").upsert(clean_news, on_conflict="category,keyword,title").execute()
            print(f"   💾 뉴스 {len(clean_news)}개 처리 완료")
        except Exception as e:
            print(f"   ⚠️ 뉴스 저장 실패: {e}")

    # 2. 뉴스 롤링 업데이트 (오래된 것 삭제)
    try:
        res = supabase.table("live_news").select("id").eq("category", category).order("created_at", desc=True).execute()
        all_ids = [row['id'] for row in res.data]
        
        if len(all_ids) > 30:
            ids_to_delete = all_ids[30:]
            supabase.table("live_news").delete().in_("id", ids_to_delete).execute()
            print(f"   🧹 오래된 뉴스 {len(ids_to_delete)}개 삭제 완료 (롤링 유지)")
    except Exception as e:
        print(f"   ⚠️ 롤링 업데이트 실패: {e}")

    # 3. 랭킹 저장 (덮어쓰기)
    rank_list = data.get("rankings", [])
    if rank_list:
        clean_ranks = []
        for item in rank_list:
            clean_ranks.append({
                "category": category,
                "rank": item["rank"],
                "title": item["title"],
                "meta_info": item.get("meta", ""),
                "updated_at": "now()"
            })
        
        try:
            supabase.table("live_rankings").upsert(clean_ranks, on_conflict="category,rank").execute()
            print(f"   🏆 랭킹 TOP 10 갱신 완료")
        except Exception as e:
            print(f"   ⚠️ 랭킹 저장 실패: {e}")

def main():
    print("🚀 뉴스 및 랭킹 업데이트 시작")
    print(f"ℹ️ 사용할 AI 모델: {SELECTED_MODEL_NAME}")
    
    for category, instructions in CATEGORIES.items():
        data = fetch_data_from_gemini(category, instructions)
        if data:
            update_database(category, data)
        time.sleep(2)

    print("✅ 모든 작업 완료")

if __name__ == "__main__":
    main()
