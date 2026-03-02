import json
import time
from datetime import datetime
from chart_api import ChartEngine
from database import DatabaseManager 

def run_automation():
    print("🚀 Starting K-Trend Automation...", flush=True)

    try:
        engine = ChartEngine()
        db = DatabaseManager()
    except Exception as e:
        print(f"❌ Initialization Failed: {e}", flush=True)
        return

    if not db.supabase:
        print("❌ Supabase connection failed.", flush=True)
        return

    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]
    
    for cat in categories:
        print(f"\n⚡ Processing: {cat}", flush=True)
        
        try:
            json_str = engine.get_top10_chart(cat)
            
            if not json_str:
                print(f"⚠️ Empty response for {cat}", flush=True)
                continue

            try:
                parsed_json = json.loads(json_str)
                data = parsed_json.get("top10", [])
            except json.JSONDecodeError:
                print(f"⚠️ JSON Decode Error. Raw: {json_str[:100]}...", flush=True)
                continue
            
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
                
                db.save_rankings(db_data)
                print(f"✅ {cat} Saved successfully.", flush=True)
            else:
                print(f"⚠️ {cat} No data found.", flush=True)
                
        except Exception as e:
            print(f"❌ Error processing {cat}: {e}", flush=True)

        time.sleep(2)

if __name__ == "__main__":
    run_automation()
