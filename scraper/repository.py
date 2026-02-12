from datetime import datetime, timedelta
from dateutil.parser import isoparse
from config import supabase, CATEGORY_MAP

def get_existing_links(category):
    """중복 체크를 위해 해당 카테고리의 모든 링크 조회"""
    res = supabase.table("live_news").select("link").eq("category", category).execute()
    return {item['link'] for item in res.data}

def save_news(news_list):
    """
    뉴스 저장: 
    1. 중복 기사 제거 (링크 기준)
    2. 점수 4.0점 미만 제거
    3. [NEW] 중복 이미지 제거 (시각적 다양성 확보)
    """
    if not news_list: return
    
    seen_links = set()
    seen_images = set() # [추가] 이미 등록된 이미지 URL 추적용
    unique_list = []
    
    # DB에 이미 저장된 이미지들도 확인하면 좋겠지만, 
    # 성능을 위해 현재 수집된 배치를 기준으로 중복 이미지를 걸러냅니다.
    
    for item in news_list:
        # [규칙 1] 점수 4.0 미만은 저장 안 함
        if item.get('score', 0) < 4.0:
            continue

        link = item['link']
        img_url = item.get('image_url', '')

        # [규칙 2] 링크 중복 체크
        if link in seen_links:
            continue

        # [규칙 3] 이미지 중복 체크 (다양성 확보)
        # 이미지가 없거나(빈 문자열), 플레이스홀더인 경우는 제외하고 체크
        if img_url and "placehold.co" not in img_url:
            if img_url in seen_images:
                # 이미 같은 사진을 쓰는 기사가 리스트에 있다면 이 기사는 건너뜀
                continue
            seen_images.add(img_url)

        # 통과된 기사 추가
        unique_list.append(item)
        seen_links.add(link)
            
    if not unique_list:
        print("   ℹ️ 저장할 기사가 없습니다 (점수 미달, 중복 링크, 또는 중복 이미지).")
        return

    try:
        supabase.table("live_news").upsert(unique_list, on_conflict="link").execute()
        print(f"   ✅ 신규 {len(unique_list)}개 DB 저장 완료 (이미지 중복 제거됨).")
    except Exception as e:
        print(f"   ⚠️ 저장 실패: {e}")

def manage_slots(category):
    """
    [슬롯 관리] 30개 유지 로직
    - 30개가 넘으면 오래된 것(24시간+) 삭제
    - 그래도 넘으면 점수 낮은 순 삭제
    - 남은 기사들의 랭킹(Rank) 업데이트 (참고용)
    """
    res = supabase.table("live_news").select("*").eq("category", category).execute()
    all_articles = res.data
    total_count = len(all_articles)
    
    print(f"   📊 {category.upper()}: 현재 {total_count}개 (목표: 30개)")

    if total_count <= 30:
        _update_rankings(all_articles)
        return

    # --- 삭제 로직 ---
    delete_ids = []
    now = datetime.now()
    threshold = now - timedelta(hours=24) 
    
    # 시간순 정렬
    try: 
        all_articles.sort(key=lambda x: isoparse(x['created_at']).replace(tzinfo=None))
    except: pass

    remaining_count = total_count
    
    # 1. 24시간 지난 기사 우선 삭제
    for art in all_articles:
        if remaining_count <= 30: break
        
        try: art_date = isoparse(art['created_at']).replace(tzinfo=None)
        except: art_date = datetime(2000, 1, 1)

        if art_date < threshold:
            delete_ids.append(art['id'])
            remaining_count -= 1

    # 2. 그래도 많으면 점수 낮은 순 삭제
    if remaining_count > 30:
        survivors = [a for a in all_articles if a['id'] not in delete_ids]
        survivors.sort(key=lambda x: x.get('score', 0)) # 오름차순 (낮은 점수 먼저)
        
        for art in survivors:
            if remaining_count <= 30: break
            delete_ids.append(art['id'])
            remaining_count -= 1

    if delete_ids:
        supabase.table("live_news").delete().in_("id", delete_ids).execute()
        print(f"   🧹 공간 확보: {len(delete_ids)}개 삭제 완료.")
    
    # 남은 기사 랭킹 재정렬
    final_survivors = [a for a in all_articles if a['id'] not in delete_ids]
    _update_rankings(final_survivors)

def _update_rankings(articles):
    """남은 기사 점수순 정렬 후 Rank 업데이트"""
    if not articles: return

    # 점수 높은 순 정렬
    articles.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    updates = []
    for i, art in enumerate(articles):
        new_rank = i + 1
        if art.get('rank') != new_rank:
            updates.append({"id": art['id'], "rank": new_rank})
            
    if updates:
        try:
            supabase.table("live_news").upsert(updates).execute()
        except: pass

def archive_top_articles():
    """
    [수정됨] 랭크 무시 -> 점수(Score) 7.0 이상인 기사 무조건 아카이빙
    """
    print("🗄️ 고득점(7.0+) 기사 아카이빙 체크...")
    
    try:
        # 카테고리 구분 없이 7.0점 이상 조회
        res = supabase.table("live_news")\
            .select("*")\
            .gte("score", 7.0)\
            .execute()
        
        high_score_articles = res.data
        
        if high_score_articles:
            archive_data = []
            for art in high_score_articles:
                archive_data.append({
                    "created_at": art['created_at'],
                    "category": art['category'],
                    "title": art['title'],
                    "summary": art['summary'],
                    "image_url": art['image_url'],
                    "original_link": art['link'],  # live_news의 link -> search_archive의 original_link
                    "score": art['score'],
                    "rank": 0 # 랭크는 이제 의미 없으므로 0 처리
                })
            
            # original_link 기준으로 upsert (중복 방지)
            supabase.table("search_archive").upsert(archive_data, on_conflict="original_link").execute()
            print(f"   💾 총 {len(archive_data)}개의 고득점 기사(7.0+) 아카이브 저장 완료.")
        else:
            print("   ℹ️ 저장할 고득점(7.0 이상) 기사가 없습니다.")
            
    except Exception as e:
        print(f"   ⚠️ 아카이브 저장 실패: {e}")

def update_keywords_db(keywords):
    if not keywords: return
    try:
        supabase.table("trending_keywords").delete().neq("id", 0).execute()
    except: pass 
    
    insert_data = []
    for i, item in enumerate(keywords):
        insert_data.append({
            "keyword": item.get('keyword'),
            "count": item.get('count', 0),
            "rank": item.get('rank', i + 1),
            "updated_at": datetime.now().isoformat()
        })
    
    if insert_data:
        try:
            supabase.table("trending_keywords").insert(insert_data).execute()
            print("   ✅ 키워드 랭킹 DB 업데이트 완료.")
        except: pass

def get_recent_titles(limit=100):
    res = supabase.table("live_news").select("title").order("created_at", desc=True).limit(limit).execute()
    return [item['title'] for item in res.data]
