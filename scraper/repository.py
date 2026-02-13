import os
from supabase import create_client, Client
from datetime import datetime, timedelta
from dateutil import parser 

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = None

def init_supabase():
    global supabase
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        except: pass

init_supabase()

def get_existing_links(category):
    if not supabase: return set()
    try:
        # 최근 3일치만 중복 검사
        ago = (datetime.now() - timedelta(days=3)).isoformat()
        res = supabase.table("live_news").select("link").eq("category", category).gt("created_at", ago).execute()
        return {item['link'] for item in res.data}
    except: return set()

def save_news(news_list):
    """
    [규칙 4 & 아카이빙]
    1. live_news 테이블 저장 (30개 선별된 것)
    2. 평점 7.0 이상은 search_archive에도 저장
    """
    if not supabase or not news_list: return
    
    try:
        # 1. Live News 저장
        supabase.table("live_news").insert(news_list).execute()
        print(f"   ✅ DB 저장: 신규 {len(news_list)}개 등록 완료.")

        # 2. Archive 저장 (평점 7.0 이상)
        high_score_news = [n for n in news_list if n.get('score', 0) >= 7.0]
        if high_score_news:
            try:
                supabase.table("search_archive").insert(high_score_news).execute()
                print(f"   🏆 Archive: 평점 7.0 이상 {len(high_score_news)}개 아카이브 저장.")
            except Exception as e:
                # 아카이브 중복은 무시
                pass

    except Exception as e:
        print(f"❌ DB 저장 오류: {e}")

def manage_slots(category):
    """
    [규칙 5 & 6] 슬롯 관리 (30개 유지)
    1. 24시간 지난 기사 삭제 (30개 될 때까지)
    2. 그래도 많으면 점수 낮은 순 삭제 (30개 될 때까지)
    """
    if not supabase: return

    try:
        # 전체 뉴스 가져오기 (시간, 점수 포함)
        res = supabase.table("live_news").select("*").eq("category", category).execute()
        all_items = res.data
        total_count = len(all_items)
        TARGET = 30 

        if total_count <= TARGET:
            print(f"   ✨ 현재 {total_count}개. 삭제 로직 건너뜀.")
            return

        now = datetime.now()
        # 날짜 파싱
        for item in all_items:
            try:
                item['dt'] = parser.parse(item['created_at']).replace(tzinfo=None)
            except:
                item['dt'] = now 

        # [규칙 5] 24시간 지난 기사 식별
        over_24h = [i for i in all_items if (now - i['dt']) > timedelta(hours=24)]
        
        delete_ids = []
        current_count = total_count

        # 24시간 지난 것 우선 삭제 (30개 유지 조건)
        for item in over_24h:
            if current_count > TARGET:
                delete_ids.append(item['id'])
                current_count -= 1
            else:
                break 

        # [규칙 6] 그래도 30개 초과 시 -> 점수 낮은 순 삭제
        if current_count > TARGET:
            # 삭제 예정이 아닌 남은 기사들
            survivors = [i for i in all_items if i['id'] not in delete_ids]
            # 점수 오름차순 정렬 (낮은 점수가 0번 인덱스)
            survivors.sort(key=lambda x: x.get('score', 0))

            for item in survivors:
                if current_count > TARGET:
                    delete_ids.append(item['id'])
                    current_count -= 1
                else:
                    break

        if delete_ids:
            supabase.table("live_news").delete().in_("id", delete_ids).execute()
            print(f"   🧹 슬롯 정리: {len(delete_ids)}개 삭제 (잔여 {current_count}개)")

    except Exception as e:
        print(f"⚠️ 슬롯 관리 오류: {e}")

def get_recent_titles():
    if not supabase: return []
    try:
        res = supabase.table("live_news").select("title").order("created_at", desc=True).limit(50).execute()
        return [item['title'] for item in res.data]
    except: return []

def update_keywords_db(k): pass
