import os
import json
from datetime import datetime
from chart_api import ChartEngine
from supabase import create_client

# Supabase 클라이언트 설정
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

def run_automation():
    # 1. GitHub Secrets에서 API 키 가져오기
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not gemini_key:
        print("❌ CRITICAL: GEMINI_API_KEY is missing!")
        return

    # 2. 엔진 초기화 (Gemini + Kobis)
    engine = ChartEngine()
    engine.set_api_key(gemini_key) # Gemini 키 주입 및 모델 자동 선택
    
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]
    
    for cat in categories:
        print(f"\n📊 Processing {cat}...")
        
        # 3. 데이터 수집 및 번역 (API or Search)
        translated_json = engine.get_top10_chart(cat)
        
        try:
            # JSON 파싱
            data = json.loads(translated_json).get("top10", [])
            
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
                
                # 4. Supabase DB 업데이트 (기존 데이터 삭제 후 삽입)
                supabase.table('live_rankings').delete().eq('category', cat).execute()
                supabase.table('live_rankings').insert(db_data).execute()
                print(f"✅ {cat} Updated Successfully.")
            else:
                print(f"⚠️ {cat} No data found.")
                
        except json.JSONDecodeError:
            print(f"❌ {cat} JSON Parsing Error. Response was not valid JSON.")
        except Exception as e:
            print(f"❌ {cat} Unexpected Error: {e}")

if __name__ == "__main__":
    run_automation()
