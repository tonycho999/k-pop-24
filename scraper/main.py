import json
import time
from datetime import datetime
from chart_api import ChartEngine
from database import DatabaseManager  # 사용자님이 만드신 파일 import

def run_automation():
    print("🚀 Starting K-Trend Automation...")

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
            # 1. 데이터 수집 및 번역 (ChartEngine)
            json_str = engine.get_top10_chart(cat)
            
            # 2. JSON 파싱
            try:
                data = json.loads(json_str).get("top10", [])
            except json.JSONDecodeError:
                print(f"⚠️ JSON Decode Error for {cat}. Raw: {json_str[:50]}...")
                continue
            
            # 3. 데이터 가공 및 DB 저장 (DatabaseManager)
            if data:
                db_data = []
                for item in data:
                    db_data.append({
                        "category": cat,
                        "rank": item.get('rank'),
                        "title": item.get('title'),
                        "meta_info": str(item.get('info', '')),
                        "score": 100, # 고정 점수
                        "updated_at": datetime.now().isoformat()
                    })
                
                # DatabaseManager의 save_rankings 메서드 사용
                # (내부에서 upsert 처리됨)
                db.save_rankings(db_data)
                
            else:
                print(f"⚠️ {cat} No valid data extracted.")
                
        except Exception as e:
            print(f"❌ Error processing {cat}: {e}")

        # Rate Limit 방지용 휴식
        time.sleep(2)

if __name__ == "__main__":
    run_automation()
