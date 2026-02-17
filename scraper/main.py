import os
import json
import asyncio
from chart_api import ChartEngine
from database import DatabaseManager
from supabase import create_client
from groq import Groq

# Supabase 클라이언트 초기화
supa_url = os.environ.get("SUPABASE_URL")
supa_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supa_url, supa_key) if supa_url and supa_key else None

def get_run_count():
    """system_status 테이블에서 run_count 조회"""
    if not supabase: return 0
    try:
        res = supabase.table('system_status').select('run_count').eq('id', 1).single().execute()
        return res.data['run_count'] if res.data else 0
    except Exception as e:
        print(f"⚠️ Run count fetch error: {e}")
        return 0

def update_run_count(current):
    """run_count 업데이트 (0~23 순환)"""
    if not supabase: return
    next_count = (current + 1) % 24
    try:
        supabase.table('system_status').upsert({'id': 1, 'run_count': next_count}).execute()
        print(f"🔄 Cycle Updated: {current} -> {next_count}")
    except Exception as e:
        print(f"⚠️ Run count update error: {e}")

def analyze_with_groq(api_key, category):
    """Groq AI 자가 진단"""
    file_path = f"error_{category}.html"
    if not os.path.exists(file_path): return
    try:
        client = Groq(api_key=api_key)
        with open(file_path, "r", encoding="utf-8") as f:
            html_snippet = f.read()[:4000]
        prompt = f"HTML 소스를 분석하여 {category} 순위 태그의 새로운 CSS Selector를 제안하세요: {html_snippet}"
        chat = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama3-70b-8192")
        print(f"🤖 [AI Fix for {category}]:\n{chat.choices[0].message.content}")
    except Exception as e: print(f"AI Analysis error: {e}")

async def run_automation():
    # 1. 실행 카운트 확인 (에러 해결 지점)
    run_count = get_run_count()
    print(f"🚀 [Cycle {run_count}] Automation Started")
    
    # 2. Groq 키 및 차트 실행 여부 (1번, 5번 키)
    key_idx = (run_count % 8) + 1
    api_key = os.environ.get(f"GROQ_API_KEY{key_idx}")
    is_chart_time = key_idx in [1, 5]
    print(f"🔑 Using GROQ_API_KEY{key_idx} (Chart Mode: {is_chart_time})")

    db = DatabaseManager()

    if is_chart_time:
        engine = ChartEngine()
        categories = ["k-pop", "k-drama", "k-movie", "k-entertain"]
        for cat in categories:
            chart_json = await engine.get_top10_chart(cat, run_count)
            data = json.loads(chart_json).get("top10", [])
            
            if data and len(data) >= 5:
                # live_rankings 테이블에 저장
                db_rankings = [{"category": cat, "rank": i['rank'], "title": i['title'], "meta_info": i['info'], "score": 100} for i in data]
                db.save_rankings(db_rankings)
                print(f"✅ {cat} Rankings Saved.")
            else:
                analyze_with_groq(api_key, cat)

    # 3. [Phase 2] 기사 작성 로직 (news_api 연동 예정)
    print(f"📝 News generation with Key #{key_idx}...")

    # 4. 카운트 업데이트
    update_run_count(run_count)

if __name__ == "__main__":
    asyncio.run(run_automation())
