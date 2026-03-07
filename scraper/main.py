import sys
import time
from datetime import datetime
import pytz
import json

from database import Database
from naver_api import NaverTrendEngine
from chart_api import ChartEngine

def get_time_context():
    korea_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(korea_tz)
    hour = now.hour
    
    if 5 <= hour < 11:
        return "Morning (오늘 아침을 달군 주인공, 상쾌하거나 시선 집중형 리드문)"
    elif 11 <= hour < 17:
        return "Afternoon (오전 내내 검색어 장악한, 점심/오후 시간대 화제 집중 리드문)"
    elif 17 <= hour < 23:
        return "Evening/Night (오늘 하루 가장 뜨거웠던, 하루를 총결산하는 느낌의 리드문)"
    else:
        return "Late Night (오늘 밤을 달구는 심야 속보, 감성적이고 심층적인 느낌의 리드문)"

def run_hourly_news(db):
    print("========================================")
    print("📰 [MODE: NEWS] Starting Hourly Update (Smart Routing & Global Deduplication)")
    print("========================================")
    
    engine = NaverTrendEngine(db=db)
    time_context = get_time_context()
    print(f"⏰ Current Time Context: {time_context}")

    # 💡 [핵심 수정] k-movie와 k-drama를 k-actor로 통합
    categories = {
        "k-actor": "한국 영화 드라마 배우",
        "k-pop": "K-POP 아이돌 가수",
        "k-entertain": "예능 출연진",
        "k-culture": "인플루언서"
    }

    # 💡 [핵심 수정] 결과 저장용 딕셔너리도 k-actor로 통합
    final_categorized_results = {
        "k-actor": [], "k-pop": [], "k-entertain": [], "k-culture": []
    }

    # 💡 [핵심 수정 1] 부서(카테고리) 상관없이 DB에 있는 '모든' 인물 명단을 하나로 합침 (전사적 통합 명단)
    global_active_names = []
    for cat in categories.keys():
        global_active_names.extend(db.get_active_names(cat))
    global_active_names = list(set(global_active_names)) # 중복 제거
    
    print(f"🌍 Global Active Names in DB: {len(global_active_names)} people")

    # 💡 [새로 추가] 이번 업데이트에서 이미 사용된 사진 URL을 기억하는 바구니
    global_used_images = set()

    for category_key, search_keyword in categories.items():
        print(f"\n\n▶️ Starting News Category: {category_key}")
        
        breaking_targets = []
        raw_top = engine.get_target_people(search_keyword, exclude_names=[])
        if raw_top:
            top_1 = raw_top[0]
            if top_1 in global_active_names:
                print(f"  🔥 [Breaking News] '{top_1}' 님은 화제성이 폭발하여 속보로 다룹니다!")
                breaking_targets.append(top_1)
        
        # 💡 [핵심 수정 2] 부서별 명단이 아닌 '전사적 통합 명단(global_active_names)'을 기준으로 제외 필터링
        strict_exclude = [n for n in global_active_names if n not in breaking_targets]
        target_names = engine.get_target_people(search_keyword, exclude_names=strict_exclude)
        
        if not target_names:
            print(f"⚠️ No new targets found for {category_key}. Skipping.")
            continue
            
        print(f"  > [Oversampling] {len(target_names)} candidates fetched for robust routing.")

        for person in target_names:
            current_context = time_context
            is_breaking = person in breaking_targets
            
            if is_breaking:
                current_context = "[긴급/속보] " + time_context

            # 💡 [수정] 엔진에게 기사를 쓸 때 '사용된 사진 바구니(global_used_images)'를 같이 쥐여줍니다!
            result_data = engine.process_person(person, current_context, used_image_urls=global_used_images)
            if result_data:
                score = result_data.get('score', 0)
                
                if score < 65:
                    print(f"  ⏭️ [Weak News Skip] '{person}' 님 기사 내용 부족 (Score: {score}점)")
                    continue
                
                if is_breaking:
                    result_data['title'] = "[BREAKING] " + result_data['title']
                
                actual_category = result_data.get('category', category_key)
                if actual_category not in final_categorized_results:
                    actual_category = category_key

                if actual_category != category_key:
                    print(f"  🔄 [Smart Routing] '{person}' 님의 기사가 내용에 맞게 '{category_key}'에서 '{actual_category}'(으)로 이동되었습니다!")

                final_categorized_results[actual_category].append(result_data)
                print(f"  ✅ [{actual_category}] {result_data['title']} (Score: {score})")
                
                # 💡 [핵심 수정 3] 기사를 한 번 쓴 사람은 즉시 '전사적 명단'에 추가하여, 다음 카테고리에서 또 나오는 것을 완벽 차단!
                if person not in global_active_names:
                    global_active_names.append(person)
                
            time.sleep(1)
            
    for final_cat, results in final_categorized_results.items():
        if results:
            print(f"💾 Saving {len(results)} articles to '{final_cat}' DB...")
            db.save_news_results(category=final_cat, results=results)

def run_top10_charts(db):
    print("========================================")
    print("📊 [MODE: CHART] Starting 6-Hour Top 10 Charts Update")
    print("========================================")
    
    chart_engine = ChartEngine(db=db)
    
    # 💡 [핵심 수정] 차트 부서도 k-movie/k-drama 대신 k-actor로 통일
    categories = ["k-actor", "k-pop", "k-entertain", "k-culture"]
    
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
