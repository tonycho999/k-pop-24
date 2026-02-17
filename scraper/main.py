import json
import re
import os
import time
from datetime import datetime, timedelta
from news_api import NewsEngine
from naver_api import NaverManager
from database import DatabaseManager
from supabase import create_client

# ---------------------------------------------------------
# [설정] 실행 사이클
# ---------------------------------------------------------
TARGET_COUNTS_FOR_OTHERS = [5, 17] 

def clean_json_text(text):
    match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL)
    if match: text = match.group(1)
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1: return text[start:end+1]
    return text.strip()

# ---------------------------------------------------------
# [DB 연동 (Main용)]
# ---------------------------------------------------------
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
    next_count = current + 1
    if next_count >= 24: next_count = 0
    try:
        supabase.table('system_status').upsert({'id': 1, 'run_count': next_count}).execute()
        print(f"🔄 Cycle Count Updated: {current} -> {next_count}")
    except Exception as e:
        print(f"⚠️ Failed to update run count: {e}")

# ---------------------------------------------------------
# [Helper] 이전 순위 기록 가져오기 (순위 변동 체크용)
# ---------------------------------------------------------
def get_previous_rank_map(category):
    """
    search_archive에서 최근 24시간 내 데이터를 조회하여
    { "인물이름": 랭킹숫자 } 형태의 맵을 반환합니다.
    """
    if not supabase: return {}
    try:
        # 최근 100건 조회 (충분한 양)
        res = supabase.table('search_archive') \
            .select('keyword, query') \
            .eq('category', category) \
            .order('created_at', desc=True) \
            .limit(100) \
            .execute()
            
        rank_map = {}
        if res.data:
            for item in res.data:
                kw = item['keyword']
                if kw in rank_map: continue # 최신 기록만 사용
                
                # query 필드에서 rank 파싱 ("k-pop top 30 rank 5")
                try:
                    match = re.search(r'rank (\d+)', item['query'])
                    if match:
                        rank_map[kw] = int(match.group(1))
                except: pass
        return rank_map
    except Exception as e:
        print(f"⚠️ Failed to fetch rank history: {e}")
        return {}

# ---------------------------------------------------------
# [메인 로직]
# ---------------------------------------------------------
def run_automation():
    run_count = get_run_count()
    print(f"🚀 Automation Started (Cycle: {run_count}/23)")
    
    db = DatabaseManager()
    engine = NewsEngine(run_count)
    naver = NaverManager()
    
    is_key1 = engine.is_using_primary_key()
    
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]

    for cat in categories:
        print(f"\n[{cat}] Analyzing Trends...")
        
        # 1. 이전 순위 정보 로드 (순위 변동 비교용)
        prev_ranks = get_previous_rank_map(cat)

        try:
            # -----------------------------------------------------------
            # Step 1. 리스트 확보
            # -----------------------------------------------------------
            list_json = engine.get_rankings_list(cat)
            cleaned_list = clean_json_text(list_json)
            if not cleaned_list or cleaned_list == "{}":
                print(f"⚠️ [{cat}] No list data returned.")
                continue
            
            parsed_list = json.loads(cleaned_list)
            
            # -----------------------------------------------------------
            # Step 2. Top 10 차트 저장
            # -----------------------------------------------------------
            should_update_chart = (cat == 'k-pop') or is_key1
            top10_data = parsed_list.get('top10', [])
            
            if top10_data and should_update_chart:
                print(f"  > 📊 Saving Top 10 Chart ({len(top10_data)} items)...")
                db_data = []
                for item in top10_data:
                    db_data.append({
                        "category": cat,
                        "rank": item.get('rank'),
                        "title": item.get('title'),
                        "meta_info": item.get('info', ''),
                        "score": 0
                    })
                db.save_rankings(db_data)
            elif top10_data:
                print(f"  > ⏩ Skipping Chart Update (Not Key 1).")

            # -----------------------------------------------------------
            # Step 3. 인물별 기사 작성 (순위 변동 로직 적용)
            # -----------------------------------------------------------
            people_list = parsed_list.get('people', [])
            if people_list:
                print(f"  > 👥 Reviewing {len(people_list)} People for updates...")
                live_news_buffer = [] 

                for person in people_list:
                    rank = person.get('rank')
                    name_en = person.get('name_en')
                    name_kr = person.get('name_kr')
                    
                    if not name_en or not rank: continue
                    if not name_kr: name_kr = name_en
                    
                    # [업데이트 결정 로직]
                    # 1. Top 3: 무조건 작성
                    # 2. 4~30위: 
                    #    - New Entry (이전에 없던 사람)
                    #    - Rank Change (이전 순위와 현재 순위가 다름)
                    
                    should_write = False
                    reason = ""
                    
                    if rank <= 3:
                        should_write = True
                        reason = "🔥 Top 3 Always"
                    elif name_en not in prev_ranks:
                        should_write = True
                        reason = "✨ New Entry"
                    elif prev_ranks[name_en] != rank:
                        should_write = True
                        reason = "📈 Rank Change"
                    
                    if should_write:
                        print(f"    -> 📝 #{rank} {name_en} ({reason})...")
                        
                        # (1) 기사 수집 (Perplexity) - rank에 따라 기사 수 자동 조절
                        facts = engine.fetch_article_details(name_kr, name_en, cat, rank)
                        if "Failed" in facts:
                            print("       ⚠️ Skip: Facts failed.")
                            continue

                        # (2) 기사 작성 (Groq)
                        full_text = engine.edit_with_groq(name_en, facts, cat)
                        
                        # (3) 파싱
                        score = 70
                        if "###SCORE:" in full_text:
                            try:
                                parts = full_text.split("###SCORE:")
                                full_text = parts[0].strip()
                                import re
                                m = re.search(r'\d+', parts[1])
                                if m: score = int(m.group())
                            except: pass
                            
                        lines = full_text.split('\n')
                        title = lines[0].replace('Headline:', '').strip()
                        summary = "\n".join(lines[1:]).strip()
                        img_url = naver.get_image(name_kr)
                        
                        article_data = {
                            "category": cat,
                            "keyword": name_en,
                            "title": title,
                            "summary": summary,
                            "link": "",
                            "image_url": img_url,
                            "score": score,
                            "likes": 0,
                            "query": f"{cat} top 30 rank {rank}",
                            "raw_result": str(person),
                            "run_count": run_count
                        }
                        
                        # (4) 아카이브 저장
                        db.save_to_archive(article_data)
                        
                        # (5) 라이브 뉴스 버퍼 추가
                        live_news_buffer.append({
                            "category": article_data['category'],
                            "keyword": article_data['keyword'],
                            "title": article_data['title'],
                            "summary": article_data['summary'],
                            "link": "",
                            "image_url": article_data['image_url'],
                            "score": score,
                            "likes": 0
                        })
                        time.sleep(1) # 안정성 확보
                    else:
                        pass # 순위 변동 없음

                # 배치 저장 실행
                if live_news_buffer:
                    print(f"  > 💾 Saving {len(live_news_buffer)} articles to Live News...")
                    db.save_live_news(live_news_buffer)
                else:
                    print("  > 💤 No updates needed (Ranks unchanged).")

        except Exception as e:
            print(f"❌ [{cat}] Error: {e}")

    update_run_count(run_count)

if __name__ == "__main__":
    run_automation()
