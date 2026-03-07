import sys
import time
from datetime import datetime, timedelta, timezone
import pytz
import json

from database import Database
from naver_api import NaverTrendEngine
from chart_api import ChartEngine

def run_garbage_collection(db):
    print("========================================")
    print("🧹 [MODE: CLEANUP] Garbage Collection (DB 청소)")
    print("========================================")
    try:
        # DB에 supabase 클라이언트가 연결되어 있다고 가정하고 오래된 데이터 강제 삭제
        if hasattr(db, 'supabase'):
            now_utc = datetime.now(timezone.utc)
            time_24h_ago = (now_utc - timedelta(hours=24)).isoformat()
            time_7d_ago = (now_utc - timedelta(days=7)).isoformat()
            
            db.supabase.table('live_news').delete().lt('created_at', time_24h_ago).execute()
            db.supabase.table('search_archive').delete().lt('created_at', time_7d_ago).execute()
            print("  ✅ [GC 완료] 24시간 지난 기사 & 7일 지난 검색기록 삭제 완료!")
        else:
            print("  ⚠️ [GC 알림] db.supabase 객체가 없어 외부 청소를 스킵합니다. (내부 로직 의존)")
    except Exception as e:
        print(f"  ❌ [GC 에러] DB 청소 실패: {e}")

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
    print("📰 [MODE: NEWS] Starting Hourly Update (Smart Routing & Scoring)")
    print("========================================")
    
    engine = NaverTrendEngine(db=db)
    time_context = get_time_context()
    print(f"⏰ Current Time Context: {time_context}")

    # 💡 4대 핵심 부서 편제
    categories = {
        "k-actor": "한국 영화 드라마 배우",
        "k-pop": "K-POP 아이돌 가수 노래",
        "k-entertain": "예능 프로그램 시청률 화제",
        "k-culture": "한국 핫플레이스 바이럴 트렌드"
    }

    final_categorized_results = {
        "k-actor": [], "k-pop": [], "k-entertain": [], "k-culture": []
    }

    global_active_names = []
    for cat in categories.keys():
        global_active_names.extend(db.get_active_names(cat))
    global_active_names = list(set(global_active_names))
    
    print(f"🌍 Global Active Names in DB: {len(global_active_names)} items")

    # 💡 전사적 이미지 중복 검열 바구니
    global_used_images = set()

    for category_key, search_keyword in categories.items():
        print(f"\n\n▶️ Starting News Category: {category_key}")
        
        breaking_targets = []
        raw_top = engine.get_target_people(search_keyword, exclude_names=[])
        if raw_top:
            top_1 = raw_top[0]
            if top_1 in global_active_names:
                print(f"  🔥 [Breaking News] '{top_1}' 키워드가 화제성 폭발 중입니다!")
                breaking_targets.append(top_1)
        
        strict_exclude = [n for n in global_active_names if n not in breaking_targets]
        target_names = engine.get_target_people(search_keyword, exclude_names=strict_exclude)
        
        if not target_names:
            print(f"⚠️ No new targets found for {category_key}. Skipping.")
            continue
            
        print(f"  > [Oversampling] {len(target_names)} candidates fetched.")

        for person in target_names:
            current_context = time_context
            is_breaking = person in breaking_targets
            
            if is_breaking:
                current_context = "[긴급/속보] " + time_context

            # 이미지 바구니를 쥐여주고 기사 작성을 지시
            result_data = engine.process_person(person, current_context, used_image_urls=global_used_images)
            if result_data:
                score = result_data.get('score', 0)
                
                if score < 60:
                    print(f"  ⏭️ [Weak News Skip] '{person}' 기사 파급력 부족 (Score: {score}점)")
                    continue
                
                if is_breaking:
                    result_data['title'] = "[BREAKING] " + result_data['title']
                
                actual_category = result_data.get('category', category_key)
                if actual_category not in final_categorized_results:
                    actual_category = category_key

                final_categorized_results[actual_category].append(result_data)
                print(f"  ✅ [{actual_category}] {result_data['title']} (Score: {score})")
                
                if person not in global_active_names:
                    global_active_names.append(person)
                
            time.sleep(1)
            
    for final_cat, results in final_categorized_results.items():
        if results:
            print(f"💾 Saving {len(results)} articles to '{final_cat}' DB...")
            db.save_news_results(category=final_cat, results=results)

def run_top10_charts(db):
    print("========================================")
    print("📊 [MODE: CHART] Starting Top 10 Charts Update")
    print("========================================")
    
    chart_engine = ChartEngine(db=db)
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
    
    # 💡 항상 DB 청소부터 시작
    run_garbage_collection(db)

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
