import time
from datetime import datetime
import pytz
from database import Database
from naver_api import NaverTrendEngine

def get_time_context():
    """현재 한국 시간을 기준으로 편집국장의 기사 뉘앙스 설정"""
    korea_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(korea_tz)
    hour = now.hour
    
    if 5 <= hour < 11:
        return "Morning (아침 출근길을 겨냥한 상쾌하거나 시선 집중형 리드문)"
    elif 11 <= hour < 17:
        return "Afternoon (점심/오후 시간대 검색어를 장악한 느낌의 리드문)"
    elif 17 <= hour < 23:
        return "Evening/Night (오늘 하루를 뜨겁게 달군 총결산 느낌의 리드문)"
    else:
        return "Late Night (심야 시간대, 속보나 감성적, 심층적인 느낌의 리드문)"

def main():
    print("========================================")
    print("🚀 Starting K-Trend Hourly Rolling System (Max 50, Sort by Score)")
    print("========================================")

    db = Database()
    engine = NaverTrendEngine(db=db)
    time_context = get_time_context()
    
    print(f"⏰ Current Time Context: {time_context}")

    categories = {
        "k-movie": "한국 영화 배우",
        "k-pop": "K-POP 아이돌 가수",
        "k-drama": "방영중 드라마 배우",
        "k-entertain": "예능 출연진",
        "k-culture": "인플루언서"
    }

    for category_key, search_keyword in categories.items():
        print(f"\n\n▶️ Starting Category: {category_key}")
        
        # 1. DB에 있는 현재 50명의 명단 가져오기 (중복 방지)
        active_names = db.get_active_names(category_key)
        print(f"  > Currently active in DB: {len(active_names)} people")
        
        # 2. 새로운 타겟 10명 추출
        target_names = engine.get_target_10_people(search_keyword, exclude_names=active_names)
        
        if not target_names:
            print(f"⚠️ No new targets found for {category_key}. Skipping.")
            continue
            
        category_results = []
        
        # 3. 10명에 대한 기사 & 평점 작성
        for person in target_names:
            result_data = engine.process_person(person, time_context)
            
            if result_data:
                category_results.append(result_data)
                score = result_data.get('score', 0)
                print(f"  ✅ [Score: {score}점] {result_data['title']}")
            
            time.sleep(1)
            
        # 4. DB 저장 및 가장 오래된 기사 밀어내기 (50개 유지)
        if category_results:
            db.save_news_results(category=category_key, results=category_results)
        
    print("\n🎉 Hourly Update Completed Successfully!")

if __name__ == "__main__":
    main()
