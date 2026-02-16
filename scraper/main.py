import json
import re
import os
import time
from news_api import NewsEngine
from naver_api import NaverManager
from database import DatabaseManager
from supabase import create_client

# ---------------------------------------------------------
# [설정] 카운터 기반 스케줄링 (0 ~ 23 사이클)
# ---------------------------------------------------------
# K-Pop: 매번 실행 (조건 없음)
# 그 외 카테고리: 아래 리스트에 있는 '순서'에만 실행
TARGET_COUNTS_FOR_OTHERS = [5, 17] 

def clean_json_text(text):
    match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL)
    if match: text = match.group(1)
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1: return text[start:end+1]
    return text.strip()

# ---------------------------------------------------------
# [DB 연동] 실행 카운트 관리 함수
# ---------------------------------------------------------
supa_url = os.environ.get("SUPABASE_URL")
supa_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supa_url, supa_key)

def get_run_count():
    """DB에서 현재 run_count 가져오기 (기본값 0)"""
    try:
        # [수정] .from() -> .table()
        res = supabase.table('system_status').select('run_count').eq('id', 1).single().execute()
        
        # supabase-py 최신 버전에서는 .execute() 결과를 바로 사용하거나 .data로 접근
        if res.data:
            return res.data['run_count']
        return 0
    except Exception as e:
        # 테이블이 없거나 데이터가 없으면 0 리턴
        print(f"⚠️ Init Run Count Error (Using 0): {e}")
        return 0

def update_run_count(current):
    """
    실행이 끝나면 카운트를 1 올림
    """
    next_count = current + 1
    if next_count >= 24:
        next_count = 0
    
    try:
        # [수정] .from() -> .table()
        supabase.table('system_status').upsert({'id': 1, 'run_count': next_count}).execute()
        print(f"🔄 Cycle Count Updated: {current} -> {next_count}")
    except Exception as e:
        print(f"⚠️ Failed to update run count: {e}")

def is_target_run(category, run_count):
    """실행 여부 결정"""
    # 1. K-POP: 무조건 실행 (가장 중요)
    if category == 'k-pop':
        return True
        
    # 2. 나머지: 지정된 순서(5, 17)일 때만 실행
    if run_count in TARGET_COUNTS_FOR_OTHERS:
        return True
        
    print(f"  ⏭️ [Skip] {category} (Current Count: {run_count})")
    return False

# ---------------------------------------------------------
# [메인 로직]
# ---------------------------------------------------------
def run_automation():
    # 1. DB에서 '이번엔 몇 번째 순서인지' 확인
    run_count = get_run_count()
    print(f"🚀 Automation Started (Cycle: {run_count}/23)")
    
    db = DatabaseManager()
    engine = NewsEngine()
    naver = NaverManager()
    
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]

    for cat in categories:
        # 실행할 순서가 아니면 스킵
        if not is_target_run(cat, run_count):
            continue
            
        print(f"\n[{cat}] Processing...")

        try:
            # 1. 데이터 수집 (한국어 검색 -> 영어 JSON)
            raw_data_str, original_query = engine.get_trends_and_rankings(cat)
            
            cleaned_str = clean_json_text(raw_data_str)
            if not cleaned_str or cleaned_str == "{}":
                print(f"⚠️ [{cat}] No data returned.")
                continue

            parsed_data = json.loads(cleaned_str)
            
            # A. 랭킹 저장
            top10_list = parsed_data.get('top10', [])
            if top10_list:
                print(f"  > Saving {len(top10_list)} Rankings...")
                for item in top10_list:
                    db.save_rankings([{
                        "category": cat,
                        "rank": item.get('rank'),
                        "title": item.get('title'),
                        "meta_info": item.get('info', ''),
                        "score": 0
                    }])

            # B. 기사 작성
            people_list = parsed_data.get('people', [])
            if people_list:
                print(f"  > Processing {len(people_list)} Articles...")
                
                for person in people_list:
                    name_en = person.get('name_en')
                    name_kr = person.get('name_kr')
                    facts = person.get('facts')
                    
                    if not name_en: name_en = name_kr 
                    if not name_kr: name_kr = name_en
                    
                    if not name_en: continue

                    # Groq 기사 생성
                    full_text = engine.edit_with_groq(name_en, facts, cat)
                    
                    # 점수 파싱
                    score = 70
                    final_text = full_text
                    if "###SCORE:" in full_text:
                        try:
                            parts = full_text.split("###SCORE:")
                            final_text = parts[0].strip()
                            import re
                            score_match = re.search(r'\d+', parts[1])
                            if score_match: score = int(score_match.group())
                        except: pass

                    lines = final_text.split('\n')
                    title = lines[0].replace('Headline:', '').strip()
                    summary = "\n".join(lines[1:]).strip()
                    
                    # 이미지 검색
                    img_url = naver.get_image(name_kr)
                    
                    article_data = {
                        "category": cat,
                        "keyword": name_en,
                        "title": title,
                        "summary": summary,
                        "link": person.get('link', ''),
                        "image_url": img_url,
                        "score": score,
                        "likes": 0,
                        "query": original_query,
                        "raw_result": str(person),
                        "run_count": run_count 
                    }
                    
                    db.save_to_archive(article_data)
                    
                    live_data = {
                        "category": article_data['category'],
                        "keyword": article_data['keyword'],
                        "title": article_data['title'],
                        "summary": article_data['summary'],
                        "link": article_data['link'],
                        "image_url": article_data['image_url'],
                        "score": score,
                        "likes": 0
                    }
                    db.save_live_news([live_data])
                    print(f"    - Published: {name_en} (Score: {score})")

        except Exception as e:
            print(f"❌ [{cat}] Error: {e}")

    # 2. 모든 작업이 끝나면 다음 순서를 위해 카운트 +1
    update_run_count(run_count)

if __name__ == "__main__":
    run_automation()
