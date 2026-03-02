import json
import time
from datetime import datetime
from chart_api import ChartEngine
from database import DatabaseManager 

def run_automation():
    print("🚀 Starting K-Trend Automation (Final Fix)...")

    # 1. 엔진 & DB 초기화
    try:
        engine = ChartEngine()
        db = DatabaseManager()
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return

    # DB 연결 확인
    if not db.supabase:
        print("❌ Supabase connection failed. Check credentials.")
        return

    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]
    
    for cat in categories:
        print(f"\n⚡ Processing: {cat}")
        
        try:
            # 1. 데이터 수집 및 번역
            json_str = engine.get_top10_chart(cat)
            
            # 2. JSON 파싱
            if not json_str or json_str.strip() == "":
                print(f"⚠️ Empty response for {cat}")
                continue

            try:
                parsed_json = json.loads(json_str)
                data = parsed_json.get("top10", [])
            except json.JSONDecodeError:
                print(f"⚠️ JSON Decode Error. Raw: {json_str[:50]}...")
                continue
            
            # 3. DB 저장
            if data:
                db_data = []
                for item in data:
                    db_data.append({
                        "category": cat,
                        "rank": item.get('rank'),
                        "title": item.get('title'),
                        "meta_info": str(item.get('info', '')),
                        "score": 100, 
                        "updated_at": datetime.now().isoformat()
                    })
                
                # DatabaseManager를 통해 저장 (upsert)
                db.save_rankings(db_data)
                
            else:
                print(f"⚠️ {cat} No data found.")
                
        except Exception as e:
            print(f"❌ Error processing {cat}: {e}")

        time.sleep(2)

if __name__ == "__main__":
    run_automation()
