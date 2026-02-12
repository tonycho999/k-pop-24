from datetime import datetime, timedelta
from dateutil.parser import isoparse
from config import supabase, CATEGORY_MAP  # [수정] 점(.) 제거됨

def get_existing_links(category):
    """해당 카테고리의 기존 뉴스 링크 조회"""
    res = supabase.table("live_news").select("link").eq("category", category).execute()
    return {item['link'] for item in res.data}

def save_news(news_list):
    """뉴스 데이터 저장 (Upsert)"""
    if not news_list: return
    # 중복 링크 제거 (API 에러 방지)
    seen_links = set()
    unique_list = []
    for item in news_list:
        if item['link'] not in seen_links:
            unique_list.append(item)
            seen_links.add(item['link'])
            
    try:
        supabase.table("live_news").upsert(unique_list, on_conflict="link").execute()
        print(f"   ✅ 신규 {len(unique_list)}개 DB 저장 완료.")
    except Exception as e:
        print(f"   ⚠️ 저장 실패: {e}")

def manage_slots(category):
    """30개 유지 로직 (오래된 것 삭제 -> 점수 낮은 것 삭제)"""
    res = supabase.table("live_news").select("id", "created_at", "score").eq("category", category).execute()
    all_articles = res.data
    total_count = len(all_articles)
    
    print(f"   📊 현재 DB 총 개수: {total_count}개 (목표: 30개 유지)")

    if total_count > 30:
        delete_ids = []
        now = datetime.now()
        threshold = now - timedelta(hours=24)
        
        try: all_articles.sort(key=lambda x: isoparse(x['created_at']).replace(tzinfo=None))
        except: pass

        remaining_count = total_count
        
        # 전략 A: 24시간 지난 기사 삭제
        for art in all_articles:
            try: art_date = isoparse(art['created_at']).replace(tzinfo=None)
            except: art_date = datetime(2000, 1, 1)

            if art_date < threshold:
                if remaining_count > 30:
                    delete_ids.append(art['id'])
                    remaining_count -= 1
                else: break

        # 전략 B: 점수 낮은 순 삭제
        if remaining_count > 30:
            survivors = [a for a in all_articles if a['id'] not in delete_ids]
            survivors.sort(key=lambda x: x['score'])
            for art in survivors:
                if remaining_count > 30:
                    delete_ids.append(art['id'])
                    remaining_count -= 1
                else: break

        if delete_ids:
            supabase.table("live_news").delete().in_("id", delete_ids).execute()
            print(f"   🧹 공간 확보: {len(delete_ids)}개 삭제 완료 (현재 {remaining_count}개 유지).")

def archive_top_articles():
    """상위 랭크(Top 10) 기사 아카이빙"""
    print("🗄️ 상위 랭크(Top 10) 기사 아카이빙 시작...")
    for category in CATEGORY_MAP.keys():
        # [수정] ascending=True 대신 desc=False 사용
        res = supabase.table("live_news").select("*").eq("category", category).order("rank", desc=False).limit(10).execute()
        top_articles = res.data
        if top_articles:
            try:
                supabase.table("search_archive").upsert(top_articles, on_conflict="link").execute()
                print(f"   💾 {category.upper()}: Top {len(top_articles)}개 -> 아카이브 저장 완료.")
            except Exception as e:
                print(f"   ⚠️ 아카이브 저장 실패 ({category}): {e}")

def update_keywords_db(keywords):
    """키워드 분석 결과 DB 저장"""
    if not keywords: return
    supabase.table("trending_keywords").delete().neq("id", 0).execute()
    
    insert_data = []
    for i, item in enumerate(keywords):
        insert_data.append({
            "keyword": item.get('keyword'),
            "count": item.get('count', 0),
            "rank": item.get('rank', i + 1),
            "updated_at": datetime.now().isoformat()
        })
    
    if insert_data:
        supabase.table("trending_keywords").insert(insert_data).execute()
        print("   ✅ 키워드 랭킹 DB 업데이트 완료.")

def get_recent_titles(limit=100):
    res = supabase.table("live_news").select("title").order("created_at", desc=True).limit(limit).execute()
    return [item['title'] for item in res.data]
