import sys
import time
from datetime import datetime
import pytz
import json

from database import Database
from naver_api import NaverTrendEngine
from chart_api import ChartEngine

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

def run_hourly_news(db):
    """1시간 간격: 인물 심층 기사 작성 (평점순, 최대 50개 유지)"""
    print("========================================")
    print("📰 [MODE: NEWS] Starting Hourly 10-Person Update")
    print("========================================")
    
    engine = NaverTrendEngine(db=db)
    time_context = get_time_context()
    print(f"⏰ Current Time Context: {time_context}")

    categories = {
        "k-movie": "한국 영화 배우",
        "k-pop": "K-POP 아이돌 가수",
        "k-drama": "드라마 배우",
        "k-entertain": "예능 출연진",
        "k-culture": "인플루언서"
    }

    for category_key, search_keyword in categories.items():
        print(f"\n\n▶️ Starting News Category: {category_key}")
        
        active_names = db.get_active_names(category_key)
        print(f"  > Currently active in DB: {len(active_names)} people")
        
        target_names = engine.get_target_10_people(search_keyword, exclude_names=active_names)
        
        if not target_names:
            print(f"⚠️ No new targets found for {category_key}. Skipping.")
            continue
            
        category_results = []
        for person in target_names:
            result_data = engine.process_person(person, time_context)
            if result_data:
                category_results.append(result_data)
                score = result_data.get('score', 0)
                print(f"  ✅ [Score: {score}점] {result_data['title']}")
            time.sleep(1)
            
        if category_results:
            db.save_news_results(category=category_key, results=category_results)


def run_top10_charts(db):
    """6시간 간격: 실시간 Top 10 차트 갱신"""
    print("========================================")
    print("📊 [MODE: CHART] Starting 6-Hour Top 10 Charts Update")
    print("========================================")
    
    chart_engine = ChartEngine(db=db)
    categories = ["k-movie", "k-pop", "k-drama", "k-entertain", "k-culture"]
    
    for category in categories:
        result_json_str = chart_engine.get_top10_chart(category)
        print(f"\n✅ Result for {category}:\n{result_json_str}")
        
        # 💡 [여기 수정됨] 뽑아온 JSON 문자열을 파이썬 딕셔너리로 변환 후 DB에 저장!
        if result_json_str:
            try:
                data = json.loads(result_json_str)
                top10_list = data.get("top10", [])
                
                if top10_list:
                    # 데이터베이스 클래스의 차트 저장 함수 호출 
                    db.save_chart_results(category=category, results=top10_list)
                    print(f"  💾 [DB 저장 성공] {category} 차트 {len(top10_list)}개 업데이트 완료!")
                else:
                    print(f"  ⚠️ [DB 저장 스킵] {category} 차트 데이터가 비어있습니다.")
            except Exception as e:
                print(f"  ❌ [DB 저장 에러] {category} 데이터 파싱 또는 저장 실패: {e}")
        
        time.sleep(2) # 각 사이트 크롤링 봇 차단 방지용 딜레이

def main():
    db = Database()
    
    # GitHub Actions의 명령어(sys.argv)를 읽어서 무슨 작업을 할지 결정
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "news":
        run_hourly_news(db)
    elif mode == "chart":
        run_top10_charts(db)
    else:
        # 명령어가 없으면 (로컬 테스트 등) 둘 다 실행
        run_hourly_news(db)
        run_top10_charts(db)

    print("\n🎉 All Requested Tasks Completed Successfully!")

if __name__ == "__main__":
    main()
