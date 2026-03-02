import os
import json
import time
from datetime import datetime
from chart_api import ChartEngine
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def run_test():
    print("🚀 Starting Test Run...")
    engine = ChartEngine()
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]
    
    for cat in categories:
        print(f"\n⚡ Processing: {cat}")
        try:
            json_str = engine.get_top10_chart(cat)
            
            # [디버깅] JSON이 비었거나 이상하면 로그 출력
            if not json_str or json_str.strip() == "":
                print(f"⚠️ Empty response from Groq for {cat}")
                continue

            try:
                data = json.loads(json_str).get("top10", [])
            except json.JSONDecodeError as e:
                # [핵심] 실패한 문자열을 보여줌
                print(f"⚠️ JSON Decode Error! Raw string below:\n{json_str}")
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
                
                supabase.table('live_rankings').delete().eq('category', cat).execute()
                supabase.table('live_rankings').insert(db_data).execute()
                print(f"✅ {cat} Saved ({len(db_data)} items).")
            else:
                print(f"⚠️ {cat} No valid items parsed.")
                
        except Exception as e:
            print(f"❌ System Error: {e}")
        
        time.sleep(2)

if __name__ == "__main__":
    run_test()
