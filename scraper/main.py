import os
import json
import time
from datetime import datetime
from chart_api import ChartEngine
from supabase import create_client

# Supabase 연결
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def run_test():
    # Tavily 키 확인
    if not os.environ.get("TAVILY_API_KEY"):
        print("❌ Error: TAVILY_API_KEY is missing in GitHub Secrets.")
        return

    # 엔진 시작
    engine = ChartEngine()
    
    # 5개 카테고리 정의
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]
    
    print("🚀 Starting Test Run (Tavily Search + Groq Summary)...")

    for cat in categories:
        print(f"\n📊 Processing {cat}...")
        
        try:
            # 1. 데이터 가져오기 (Tavily -> Groq)
            json_str = engine.get_top10_chart(cat)
            data = json.loads(json_str).get("top10", [])
            
            if data:
                db_data = []
                for item in data:
                    # DB 형식에 맞게 데이터 가공
                    db_data.append({
                        "category": cat,
                        "rank": item.get('rank'),
                        "title": item.get('title'),
                        "meta_info": str(item.get('info', '')),
                        "score": 100, # 테스트용 고정 점수
                        "updated_at": datetime.now().isoformat()
                    })
                
                # 2. Supabase 저장 (기존 데이터 지우고 새로 쓰기)
                supabase.table('live_rankings').delete().eq('category', cat).execute()
                supabase.table('live_rankings').insert(db_data).execute()
                print(f"✅ {cat} Saved to DB (Total {len(db_data)} items).")
            else:
                print(f"⚠️ {cat} No data found from search.")
                
        except Exception as e:
            print(f"❌ Error processing {cat}: {e}")

        # 3. 2초 휴식 (API 보호)
        time.sleep(2)

if __name__ == "__main__":
    run_test()
