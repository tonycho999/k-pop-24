import os
import json
from datetime import datetime
from chart_api import ChartEngine
from supabase import create_client

# Supabase 연결
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def run_automation():
    # 1. 시스템 상태 확인 (로테이션 키 결정)
    res = supabase.table('system_status').select('run_count').eq('id', 1).single().execute()
    run_count = res.data['run_count'] if res.data else 0
    key_idx = (run_count % 8) + 1
    api_key = os.environ.get(f"GROQ_API_KEY{key_idx}")

    print(f"🚀 [Cycle {run_count}] Using Key #{key_idx}")

    # 2. 엔진 초기화
    engine = ChartEngine()
    engine.set_groq_client(api_key)
    
    # 3. 카테고리별 수집 및 저장
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain"]
    for cat in categories:
        print(f"📊 Processing {cat}...")
        chart_json = engine.get_top10_chart(cat)
        data = json.loads(chart_json).get("top10", [])
        
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
            # 기존 데이터 삭제 후 새 데이터 삽입 (또는 Upsert)
            supabase.table('live_rankings').delete().eq('category', cat).execute()
            supabase.table('live_rankings').insert(db_data).execute()
            print(f"✅ {cat} Rankings Updated.")

    # 4. 다음 사이클을 위해 run_count 업데이트
    next_count = (run_count + 1) % 24
    supabase.table('system_status').update({"run_count": next_count}).eq('id', 1).execute()

if __name__ == "__main__":
    run_automation()
