import os
import json
import re
import time
from chart_api import ChartEngine
from database import DatabaseManager
from supabase import create_client

def clean_json_text(text):
    if not text: return "{}"
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1: return text[start:end+1]
    return text.strip()

# Supabase 연결 설정
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
    next_count = (current + 1) % 24 # 0~23 순환
    try:
        supabase.table('system_status').upsert({'id': 1, 'run_count': next_count}).execute()
        print(f"🔄 Cycle Count Updated: {current} -> {next_count}")
    except Exception as e:
        print(f"⚠️ Failed to update run count: {e}")

def get_groq_config(run_count):
    """
    8개의 Groq 키 중 이번 시간에 사용할 키를 결정합니다.
    사용자 요청: 1번, 5번 키 시간일 때 차트 수집 실행.
    """
    key_idx = (run_count % 8) + 1  # 1, 2, 3, 4, 5, 6, 7, 8
    key_name = f"GROQ_API_KEY{key_idx}"
    api_key = os.environ.get(key_name)
    
    # 차트 실행 여부 (1번 키 또는 5번 키일 때만 True)
    should_run_chart = key_idx in [1, 5]
    
    return api_key, key_idx, should_run_chart

def run_automation():
    run_count = get_run_count()
    print(f"🚀 [Cycle {run_count}/23] Automation Started")
    
    # 1. Groq 키 로테이션 및 차트 실행 여부 판단
    groq_api_key, key_num, is_chart_time = get_groq_config(run_count)
    print(f"🔑 Using GROQ_API_KEY{key_num}")
    
    db = DatabaseManager()
    
    # 2. [Phase 1] 차트 수집 (1번, 5번 키 시간일 때만 수행)
    if is_chart_time:
        print(f"📊 Chart Update Time! (Key #{key_num} active)")
        engine = ChartEngine()
        categories = ["k-pop", "k-drama", "k-movie", "k-entertain"]

        for cat in categories:
            print(f"[{cat}] Scraping...")
            chart_json = engine.get_top10_chart(cat, run_count)
            cleaned_chart = clean_json_text(chart_json)
            
            try:
                parsed_chart = json.loads(cleaned_chart)
                top10_list = parsed_chart.get('top10', [])
                
                if top10_list:
                    print(f"  > Saving {len(top10_list)} items to DB...")
                    db_data = []
                    for item in top10_list:
                        db_data.append({
                            "category": cat,
                            "rank": item.get('rank'),
                            "title": item.get('title'),
                            "meta_info": item.get('info', ''),
                            "score": 100
                        })
                    db.save_rankings(db_data)
                else:
                    print(f"  > ⚠️ No data for {cat}")
            except Exception as e:
                print(f"  > ❌ Error: {e}")
    else:
        print(f"⏭️ Skipping Chart Scrape (Key #{key_num} is for News only)")

    # 3. [Phase 2] 기사 작성 (news_api.py 연동 구역)
    # 이 섹션은 매시간(Every Cycle) 실행됩니다.
    print(f"📝 Starting News Article Generation with Key #{key_num}...")
    # TODO: news_api.process(groq_api_key) 호출 예정

    update_run_count(run_count)

if __name__ == "__main__":
    run_automation()
