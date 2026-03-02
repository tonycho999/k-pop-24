import os
import json
import time
from datetime import datetime
from chart_api import ChartEngine
from supabase import create_client

# 환경변수 로드 확인
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Critical Error: Supabase credentials missing.")
    exit(1)

supabase = create_client(url, key)

def run_test():
    print("🚀 Starting Test Run (Tavily + KOBIS + Groq)...")

    # 엔진 초기화
    try:
        engine = ChartEngine()
    except Exception as e:
        print(f"❌ Engine Initialization Failed: {e}")
        return
    
    # 5개 카테고리
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]
    
    for cat in categories:
        print(f"\n⚡ Processing: {cat}")
        
        try:
            # 1. 데이터 가져오기 (Tavily/KOBIS -> Groq)
            json_str = engine.get_top10_chart(cat)
            
            # JSON 파싱 시도
            try:
                parsed_json = json.loads(json_str)
                data = parsed_json.get("top10", [])
            except json.JSONDecodeError:
                print(f"⚠️ JSON Decode Error for {cat}. Raw output: {json_str[:50]}...")
                data = []
            
            if data:
                db_data = []
                for item in data:
                    db_data.append({
                        "category": cat,
                        "rank": item.get('rank'),
                        "title": item.get('title'),
                        "meta_info": str(item.get('info', '')),
                        "score": 100, # 테스트용 고정 점수
                        "updated_at": datetime.now().isoformat()
                    })
                
                # 2. Supabase 저장
                # delete()로 기존 해당 카테고리 데이터 삭제 후 insert
                supabase.table('live_rankings').delete().eq('category', cat).execute()
                result = supabase.table('live_rankings').insert(db_data).execute()
                print(f"✅ {cat} Saved successfully ({len(db_data)} items).")
            else:
                print(f"⚠️ {cat} No valid data generated.")
                
        except Exception as e:
            print(f"❌ Error processing {cat}: {e}")

        # API 호출 간 2초 휴식
        time.sleep(4)

if __name__ == "__main__":
    run_test()
