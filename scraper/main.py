import time
from database import Database
from naver_api import NaverTrendEngine

def main():
    print("========================================")
    print("🚀 Starting K-Trend 30-Person Deep Analysis System")
    print("========================================")

    # 1. DB 초기화
    db = Database()
    
    # 2. 1주일 지난 오래된 아카이브 삭제 실행
    db.cleanup_old_archives()

    # 3. 분석 엔진 초기화 (DB 객체 전달하여 Groq 순번 관리)
    engine = NaverTrendEngine(db=db)

    # 타겟 카테고리 설정
    categories = {
        "k-movie": "한국 영화 배우",
        "k-pop": " K-POP 가수",
        "k-drama": "방영중 드라마 배우",
        "k-entertain": "예능 출연진",
        "k-culture": "인플루언서 팝업"
        }

    # 4. 카테고리별 순회하며 추출 -> 요약 -> DB 저장
    for category_key, search_keyword in categories.items():
        print(f"\n\n▶️ Starting Category: {category_key} (Keyword: {search_keyword})")
        
        # 30명 명단 뽑기
        top_30_names = engine.get_top_30_people(search_keyword)
        
        if not top_30_names:
            print(f"⚠️ Skipped {category_key} due to extraction failure.")
            continue
            
        category_results = []
        
        # 각 인물별 심층 기사 요약
        for idx, person in enumerate(top_30_names):
            rank = idx + 1
            result_data = engine.process_person(person, rank)
            
            if result_data:
                category_results.append(result_data)
                print(f"  ✅ [Rank {rank}] Completed: {result_data['title']}")
            
            # 네이버 API Rate Limit 방지를 위해 살짝 휴식
            time.sleep(1)
            
        # 완성된 해당 카테고리 30인 리스트를 통째로 DB에 쏴줌
        if category_results:
            db.save_news_results(category=category_key, results=category_results)
        
    print("\n🎉 All Processing Completed Successfully!")

if __name__ == "__main__":
    main()
