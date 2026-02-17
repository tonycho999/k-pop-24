import os
import json
import re
import time
from chart_api import ChartEngine # 수정된 엔진 임포트
from database import DatabaseManager
from supabase import create_client

def clean_json_text(text):
    if not text: return "{}"
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1: return text[start:end+1]
    return text.strip()

supa_url = os.environ.get("SUPABASE_URL")
supa_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supa_url, supa_key) if supa_url and supa_key else None

def get_run_count():
    if not supabase: return 0
    try:
        res = supabase.table('system_status').select('run_count').eq('id', 1).single().execute()
        return res.data['run_count'] if res.data else 0
    except: return 0

def update_run_count(current):
    if not supabase: return
    next_count = (current + 1) % 24
    try:
        supabase.table('system_status').upsert({'id': 1, 'run_count': next_count}).execute()
        print(f"🔄 Cycle Count Updated: {current} -> {next_count}")
    except Exception as e:
        print(f"⚠️ Failed to update run count: {e}")

def run_automation():
    run_count = get_run_count()
    print(f"🚀 Bot Automation Started (Cycle: {run_count}/23)")
    
    db = DatabaseManager()
    engine = ChartEngine()
    
    # 우선 테스트할 카테고리 설정
    categories = ["k-pop"]

    for cat in categories:
        print(f"\n[{cat}] Starting Direct Scraping...")
        
        try:
            # 봇이 가져온 텍스트 JSON
            chart_json = engine.get_top10_chart(cat)
            cleaned_chart = clean_json_text(chart_json)
            
            parsed_chart = json.loads(cleaned_chart)
            top10_list = parsed_chart.get('top10', [])
            
            if top10_list:
                print(f"  > 📊 Found {len(top10_list)} items. Saving to Database...")
                db_data = []
                for item in top10_list:
                    # 로그용 출력
                    print(f"    #{item['rank']} {item['title']} - {item['info']}")
                    
                    db_data.append({
                        "category": cat,
                        "rank": item.get('rank'),
                        "title": item.get('title'),
                        "meta_info": item.get('info', ''),
                        "score": 100 # 봇 수집 데이터는 최상위 신뢰도
                    })
                db.save_rankings(db_data)
            else:
                print("  > ⚠️ No data extracted from the page.")
                
        except Exception as e:
            print(f"  > ❌ Scraping Phase Error: {e}")

    update_run_count(run_count)

if __name__ == "__main__":
    run_automation()
