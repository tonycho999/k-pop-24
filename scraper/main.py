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
    
    # 💡 [핵심 1] 시간대별로 봇이 완벽하게 뉘앙스를 인식하도록 리드문 강화
    if 5 <= hour < 11:
        return "Morning (오늘 아침을 달군 주인공, 상쾌하거나 시선 집중형 리드문)"
    elif 11 <= hour < 17:
        return "Afternoon (오전 내내 검색어 장악한, 점심/오후 시간대 화제 집중 리드문)"
    elif 17 <= hour < 23:
        return "Evening/Night (오늘 하루 가장 뜨거웠던, 하루를 총결산하는 느낌의 리드문)"
    else:
        return "Late Night (오늘 밤을 달구는 심야 속보, 감성적이고 심층적인 느낌의 리드문)"

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
        
        # DB에서 최근 5시간 작성 명단 가져오기
        active_names = db.get_active_names(category_key)
        print(f"  > Currently active in DB (최근 5시간 롤링): {len(active_names)} people")
        
        # 💡 [핵심 2] 예외 처리 (Breaking News)
        # 압도적 1위의 언급량이 폭발했다면, 5시간 중복 룰을 무시하고 예외적으로 작성 허용!
        breaking_targets = []
        # 💡 [수정] get_target_10_people -> get_target_people 로 이름 변경
        raw_top = engine.get_target_people(search_keyword, exclude_names=[])
        if raw_top:
            top_1 = raw_top[0]
            if top_1 in active_names:
                print(f"  🔥 [Breaking News] '{top_1}' 님은 화제성이 폭발하여 5시간 룰을 무시하고 속보로 다룹니다!")
                breaking_targets.append(top_1)
        
        # 속보 대상자는 중복 제외(exclude) 명단에서 특별히 풀어줌
        strict_exclude = [n for n in active_names if n not in breaking_targets]
        
        # 엄격하게 필터링된 타겟 뽑기
        # 💡 [수정] get_target_10_people -> get_target_people 로 이름 변경
        target_names = engine.get_target_people(search_keyword, exclude_names=strict_exclude)
        
        if not target_names:
            print(f"⚠️ No new targets found for {category_key}. Skipping.")
            continue
            
        category_results = []
        for person in target_names:
            current_context = time_context
            is_breaking = person in breaking_targets
            
            # 속보 대상자면 AI에게 긴급 상황임을 인지시킴
            if is_breaking:
                current_context = "[긴급/속보] " + time_context

            result_data = engine.process_person(person, current_context)
            if result_data:
                score = result_data.get('score', 0)
                
                # 💡 [핵심 3] 하위권 인물 정보 부족 대비책 (AI 환각 방지)
                # 뉴스 퀄리티(점수)가 65점 미만이면 DB를 망치지 않게 과감히 스킵!
                if score < 65:
                    print(f"  ⏭️ [Weak News Skip] '{person}' 님은 기사 내용이 부족하여 제외합니다. (Score: {score}점)")
                    continue
                
                # 화면 표시를 위해 제목에 태그 달아주기
                if is_breaking:
                    result_data['title'] = "[BREAKING] " + result_data['title']
                
                category_results.append(result_data)
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
        
        if result_json_str:
            try:
                data = json.loads(result_json_str)
                top10_list = data.get("top10", [])
                
                if top10_list:
                    db.save_chart_results(category=category, results=top10_list)
                    print(f"  💾 [DB 저장 성공] {category} 차트 {len(top10_list)}개 업데이트 완료!")
                else:
                    print(f"  ⚠️ [DB 저장 스킵] {category} 차트 데이터가 비어있습니다.")
            except Exception as e:
                print(f"  ❌ [DB 저장 에러] {category} 데이터 파싱 또는 저장 실패: {e}")
        
        time.sleep(2) 

def main():
    db = Database()
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "news":
        run_hourly_news(db)
    elif mode == "chart":
        run_top10_charts(db)
    else:
        run_hourly_news(db)
        run_top10_charts(db)

    print("\n🎉 All Requested Tasks Completed Successfully!")

if __name__ == "__main__":
    main()
