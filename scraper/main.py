import os
import json
import time
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. 환경변수 로드
load_dotenv()

# 2. Supabase 클라이언트 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. Google Gemini 설정
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# ---------------------------------------------------------
# [기능 1] 최신 Flash 모델 자동 선택 (Lite/8b 제외)
# ---------------------------------------------------------
def get_best_flash_model():
    """
    Flash 모델 중 '검색 기능'이 지원되는 최신 버전을 찾습니다.
    Lite 버전이나 8b 버전은 검색 도구를 지원하지 않으므로 제외합니다.
    """
    try:
        print("🔍 최신 AI 모델(Flash) 탐색 중...")
        models = genai.list_models()
        
        valid_models = []
        for m in models:
            name = m.name.lower()
            # 1. 'flash'가 포함되어야 함
            if 'flash' not in name:
                continue
            # 2. 'lite'는 제외 (검색 기능 미지원)
            if 'lite' in name:
                continue
            # 3. '8b'도 제외 (혹시 모를 기능 제한 방지)
            if '8b' in name:
                continue
            # 4. 콘텐츠 생성이 가능한 모델이어야 함
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)
        
        if valid_models:
            # 이름순 정렬 후 가장 마지막(최신) 것 선택
            # 예: ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest'] -> latest 선택
            best_model = sorted(valid_models)[-1]
            print(f"✅ 선택된 최적 모델: {best_model}")
            return best_model
        
        print("⚠️ 적절한 Flash 모델을 찾지 못해 기본값(1.5-flash)을 사용합니다.")
        return 'models/gemini-1.5-flash'

    except Exception as e:
        print(f"⚠️ 모델 탐색 중 에러: {e}")
        return 'models/gemini-1.5-flash'

# 모델 초기화 (자동 선택된 모델 적용)
SELECTED_MODEL_NAME = get_best_flash_model()
model = genai.GenerativeModel(SELECTED_MODEL_NAME, tools='google_search_retrieval')

# ---------------------------------------------------------
# [설정] 카테고리별 프롬프트 가이드
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# [기능 2] Gemini 검색 및 데이터 생성
# ---------------------------------------------------------
def fetch_data_from_gemini(category_name, instructions):
    print(f"🤖 [Gemini] '{category_name}' 분석 중... (Model: {SELECTED_MODEL_NAME})")
    
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

# ---------------------------------------------------------
# [기능 3] 데이터베이스 저장 (Live + Archive + Ranking)
# ---------------------------------------------------------
def update_database(category, data):
    # 1. 뉴스 데이터 처리
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
        
        # [A] 아카이브 저장
        try:
            supabase.table("search_archive").upsert(clean_news, on_conflict="category,keyword,title").execute()
            print(f"   🗄️ [Archive] 뉴스 {len(clean_news)}개 보관 완료")
        except Exception as e:
            print(f"   ⚠️ 아카이브 저장 실패: {e}")

        # [B] 라이브 뉴스 저장
        try:
            supabase.table("live_news").upsert(clean_news, on_conflict="category,keyword,title").execute()
            print(f"   💾 [Live] 뉴스 {len(clean_news)}개 업데이트 완료")
        except Exception as e:
            print(f"   ⚠️ 라이브 저장 실패: {e}")

    # 2. 뉴스 롤링 업데이트
    try:
        res = supabase.table("live_news").select("id").eq("category", category).order("created_at", desc=True).execute()
        all_ids = [row['id'] for row in res.data]
        
        if len(all_ids) > 30:
            ids_to_delete = all_ids[30:]
            supabase.table("live_news").delete().in_("id", ids_to_delete).execute()
            print(f"   🧹 [Clean] 오래된 뉴스 {len(ids_to_delete)}개 삭제")
    except Exception as e:
        print(f"   ⚠️ 롤링 업데이트 실패: {e}")

    # 3. 랭킹 데이터 처리
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
    
    for category, instructions in CATEGORIES.items():
        data = fetch_data_from_gemini(category, instructions)
        if data:
            update_database(category, data)
        else:
            print(f"⚠️ {category} 데이터 수집 실패")
            
        time.sleep(2)

    print("✅ 모든 작업 완료")

if __name__ == "__main__":
    main()
