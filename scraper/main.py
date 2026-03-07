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
        if hasattr(db, 'supabase'):
            now_utc = datetime.now(timezone.utc)
            # 24시간 지난 뉴스 삭제
            time_24h_ago = (now_utc - timedelta(hours=24)).isoformat()
            # 7일 지난 검색 기록 삭제
            time_7d_ago = (now_utc - timedelta(days=7)).isoformat()
            
            db.supabase.table('live_news').delete().lt('created_at', time_24h_ago).execute()
            db.supabase.table('search_archive').delete().lt('created_at', time_7d_ago).execute()
            print("  ✅ [GC 완료] 24시간 지난 기사 & 7일 지난 검색기록 완벽 삭제!")
        else:
            print("  ⚠️ [GC 알림] 외부 청소를 스킵합니다.")
    except Exception as e:
        print(f"  ❌ [GC 에러] DB 청소 실패: {e}")

def get_time_context():
    korea_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(korea_tz)
    hour = now.hour
    
    if 5 <= hour < 11: return "Morning Update"
    elif 11 <= hour < 17: return "Afternoon Update"
    elif 17 <= hour < 23: return "Evening Update"
    else: return "Late Night Breaking"

def run_hourly_news(db):
    print("========================================")
    print("📰 [MODE: NEWS] Starting Pure API News Update")
    print("========================================")
    
    engine = NaverTrendEngine(db=db)
    time_context = get_time_context()
    print(f"⏰ Current Time Context: {time_context}")

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
    
    print(f"🌍 Global Active Subjects in DB: {len(global_active_names)} items")

    global_used_images = set()

    for category_key, search_keyword in categories.items():
        print(f"\n\n▶️ Starting News Category: {category_key}")
        
        target_names = engine.get_target_people(search_keyword, exclude_names=global_active_names, category=category_key)
        
        if not target_names:
            print(f"⚠️ No new targets found for {category_key}. Skipping.")
            continue
            
        print(f"  > Fetched {len(target_names)} trending subjects.")

        for person in target_names:
            result_data = engine.process_person(
                person_name=person, 
                time_context=time_context, 
                used_image_urls=global_used_images,
                category=category_key
            )
            
            if result_data:
                score = result_data.get('score', 0)
                if score < 60:
                    print(f"  ⏭️ [Skip] '{person}' 기사 화제성 부족 (Score: {score})")
                    continue
                
                final_categorized_results[category_key].append(result_data)
                print(f"  ✅ [{category_key}] {result_data['title']} (Score: {score})")
                
                if person not in global_active_names:
                    global_active_names.append(person)
                
            time.sleep(1) # API Rate limit 보호
            
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
    
    # 항상 쓰레기통 비우고 시작!
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
