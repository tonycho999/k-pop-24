# scraper/database.py
import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

# 상위 폴더의 .env 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    else:
        print("🚨 Supabase credentials missing in .env")
except Exception as e:
    print(f"🚨 Supabase Connection Error: {e}")

def is_keyword_used_recently(category, keyword, hours=4):
    """
    [도배 방지] 해당 카테고리에서 특정 키워드가 최근 N시간 내에 사용되었는지 확인
    True = 이미 씀 (사용 불가) / False = 안 씀 (사용 가능)
    """
    if not supabase: return False
    
    try:
        # 현재 시간(UTC) - N시간
        time_limit = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        # live_news 테이블에서 검사
        res = supabase.table("live_news")\
            .select("id", count="exact")\
            .eq("category", category)\
            .eq("keyword", keyword)\
            .gte("created_at", time_limit)\
            .execute()
            
        # 카운트가 0보다 크면 이미 쓴 것
        return res.count > 0
    except Exception as e:
        print(f"   ⚠️ DB Check Error: {e}")
        return False

def save_news_to_live(data_list):
    """[메인 전시용] live_news 테이블에 저장 (최신 30개 유지용)"""
    if not supabase or not data_list: return

    try:
        supabase.table("live_news").upsert(data_list).execute()
        print(f"   💾 [Live] Saved to 'live_news'.")
    except Exception as e:
        print(f"   ⚠️ DB Save Error (live_news): {e}")

def save_news_to_archive(data_list):
    """[영구 보관용] search_archive 테이블에 저장 (삭제 안 함)"""
    if not supabase or not data_list: return

    try:
        # 아카이브는 upsert 대신 insert (히스토리 보존)
        supabase.table("search_archive").insert(data_list).execute()
        print(f"   📦 [Archive] Saved to 'search_archive'.")
    except Exception as e:
        print(f"   ⚠️ DB Save Error (search_archive): {e}")

def save_rankings_to_db(rank_list):
    """[순위표] live_rankings 테이블에 저장"""
    if not supabase or not rank_list: return

    try:
        supabase.table("live_rankings").upsert(rank_list).execute()
        print(f"   🏆 Saved rankings.")
    except Exception as e:
        print(f"   ⚠️ DB Save Error (live_rankings): {e}")

def cleanup_old_data(category, max_limit=30):
    """[청소] live_news 테이블에서 오래된 데이터 삭제 (30개 유지)"""
    if not supabase: return

    try:
        # 1. 개수 확인
        res = supabase.table("live_news").select("id", count="exact").eq("category", category).execute()
        count = res.count

        if count > max_limit:
            # 2. 지워야 할 개수 계산
            items_to_remove = count - max_limit
            
            # 3. 오래된 순으로 ID 조회
            old_rows = supabase.table("live_news")\
                .select("id")\
                .eq("category", category)\
                .order("created_at", desc=False)\
                .limit(items_to_remove)\
                .execute()
            
            ids = [row['id'] for row in old_rows.data]
            
            if ids:
                supabase.table("live_news").delete().in_("id", ids).execute()
                print(f"   🧹 [Cleanup] Removed {len(ids)} old items from 'live_news'.")
                
    except Exception as e:
        print(f"   ⚠️ Cleanup Error: {e}")
