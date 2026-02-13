import os
from supabase import create_client, Client
from datetime import datetime

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

def save_to_archive(news_list):
    """
    [New] 상위 랭킹 뉴스(Top 10)를 영구 보존용 아카이브에 저장
    """
    if not supabase or not news_list: return
    
    try:
        archive_data = []
        for n in news_list:
            archive_data.append({
                "category": n['category'],
                "keyword": n.get('keyword'),
                "title": n['title'],
                "summary": n['summary'],
                "rank": n.get('rank'),
                "image_url": n['image_url'],
                "link": None, # 아카이브에도 링크는 저장하지 않음
                "created_at": datetime.now().isoformat()
            })
            
        supabase.table("search_archive").insert(archive_data).execute()
        print(f"   🏆 Archive: Top {len(archive_data)} 건 저장 완료.")
    except Exception as e:
        print(f"   ⚠️ 아카이브 저장 실패: {e}")

def update_sidebar_rankings(category, news_list):
    """
    [New] 우측 사이드바용 순위표(trending_rankings) 업데이트
    """
    if not supabase or not news_list: return

    try:
        # 상위 10개만 추출
        top_10 = news_list[:10]
        
        ranking_data = []
        for n in top_10:
            ranking_data.append({
                "category": category,
                "rank": n['rank'],
                "keyword": n['keyword'],
                "delta": "NEW", # 변동폭은 일단 NEW로 고정 (추후 로직 고도화 가능)
                "image_url": n['image_url']
            })

        # 1. 해당 카테고리 기존 랭킹 삭제
        supabase.table("trending_rankings").delete().eq("category", category).execute()
        
        # 2. 신규 랭킹 입력
        if ranking_data:
            supabase.table("trending_rankings").insert(ranking_data).execute()
            # print(f"   📊 Sidebar: {category} 순위표 갱신 완료.")
            
    except Exception as e:
        print(f"   ⚠️ Sidebar 갱신 실패: {e}")

def refresh_live_news(category, news_list):
    """
    [Main] 메인 피드 데이터 교체
    (키워드 중복 제거 및 DB 스키마 매칭)
    """
    if not supabase or not news_list: return
    
    # 1. 중복 키워드 제거 (혹시 모를 중복 대비)
    unique_map = {}
    for item in news_list:
        kw = item.get('keyword')
        if kw:
            unique_map[kw] = item
            
    clean_list = list(unique_map.values())
    
    # 2. DB 입력용 데이터 포장 (필드 매칭)
    final_payload = []
    for item in clean_list:
        payload = {
            "category": item.get('category'),
            "rank": item.get('rank'),
            "keyword": item.get('keyword'),
            "title": item.get('title'),
            "summary": item.get('summary'),
            "link": None,  # 🚨 링크는 저장하지 않음 (NULL)
            "image_url": item.get('image_url'),
            "score": item.get('score'),
            "likes": item.get('likes', 0),
            "dislikes": item.get('dislikes', 0),
            "published_at": item.get('published_at', datetime.now().isoformat())
        }
        final_payload.append(payload)
    
    try:
        # 3. 기존 데이터 삭제
        supabase.table("live_news").delete().eq("category", category).execute()
        
        # 4. 새 데이터 삽입
        if final_payload:
            supabase.table("live_news").insert(final_payload).execute()
            print(f"   ✅ Live News: '{category}' {len(final_payload)}개 키워드 요약 저장 완료.")
        
        # 5. 사이드바 순위표도 같이 업데이트 (필수)
        update_sidebar_rankings(category, clean_list)
        
    except Exception as e:
        print(f"   ❌ Live News 저장 실패: {e}")

# 호환성 유지용 빈 함수
def get_existing_links(category): return set()
