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

def save_error_log(error_data):
    """
    [디버깅용] AI 파싱 실패 시 원문 및 에러 메시지를 error_logs 테이블에 저장
    """
    if not supabase or not error_data: return

    try:
        # 데이터가 딕셔너리인지 확인 후 저장
        supabase.table("error_logs").insert(error_data).execute()
        print(f"📁 [Debug] AI Response raw data logged to 'error_logs'.")
    except Exception as e:
        print(f"🚨 [Debug Error] Failed to save error log: {e}")

def is_keyword_used_recently(category, keyword, hours=4):
    """
    [도배 방지] 해당 카테고리에서 특정 키워드가 최근 N시간 내에 사용되었는지 확인
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
            
        return res.count > 0
    except Exception as e:
        print(f"   ⚠️ DB Check Error: {e}")
        return False

def save_news_to_live(data_list):
    """[메인 전시용] live_news 테이블에 저장"""
    if not supabase or not data_list: return

    try:
        # upsert 사용 (기존 데이터 업데이트 또는 신규 삽입)
        supabase.table("live_news").upsert(data_list).execute()
        print(f"   💾 [Live] Saved {len(data_list)} items to 'live_news'.")
    except Exception as e:
        print(f"   ⚠️ DB Save Error (live_news): {e}")

def save_news_to_archive(data_list):
    """[영구 보관용] search_archive 테이블에 저장"""
    if not supabase or not data_list: return

    try:
        # [중요 수정] ID 충돌 방지 로직
        clean_data = []
        for item in data_list:
            new_item = item.copy() # 복사
            if 'id' in new_item:
                del new_item['id'] # live_news에서 생긴 ID 제거
            clean_data.append(new_item)

        # 아카이브에 저장
        supabase.table("search_archive").insert(clean_data).execute()
        print(f"   📦 [Archive] Saved {len(clean_data)} items to 'search_archive'.")
    except Exception as e:
        print(f"   ⚠️ DB Save Error (search_archive): {e}")

def save_rankings_to_db(rank_list):
    """[순위표] live_rankings 테이블에 저장 (기존 순위 삭제 후 갱신)"""
    if not supabase or not rank_list: return

    try:
        # 1. 해당 카테고리의 기존 랭킹 싹 지우기 (초기화)
        category = rank_list[0].get("category")
        if category:
            supabase.table("live_rankings").delete().eq("category", category).execute()

        # 2. 새로운 랭킹 저장
        supabase.table("live_rankings").insert(rank_list).execute()
        print(f"   🏆 Updated rankings for {category}.")
        
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
