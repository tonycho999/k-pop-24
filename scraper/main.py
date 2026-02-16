import json
import re
import os
from news_api import NewsEngine
from naver_api import NaverManager
from database import DatabaseManager

def clean_json_text(text):
    """AI 응답에서 순수 JSON만 추출"""
    # 1. 마크다운 제거
    match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    
    # 2. 괄호 기준으로 추출
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1:
        return text[start:end+1]
    return text.strip()

def run_automation():
    print("🚀 K-Enter24 Automation Started (English + Score Ver.)")
    
    db = DatabaseManager()
    engine = NewsEngine()
    naver = NaverManager()
    
    # 아카이브용 실행 번호
    run_count = int(os.environ.get("RUN_COUNT", 0))
    
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]

    for cat in categories:
        print(f"\n[{cat}] Processing...")
        try:
            # 1. Perplexity 데이터 수집 (한국 소스)
            raw_data_str, original_query = engine.get_trends_and_rankings(cat)
            
            # 2. JSON 파싱
            cleaned_str = clean_json_text(raw_data_str)
            if not cleaned_str or cleaned_str == "{}":
                print(f"⚠️ [{cat}] No data returned.")
                continue

            parsed_data = json.loads(cleaned_str)
            
            # ---------------------------------------------------
            # A. [사이드바] TOP 10 랭킹 저장
            # ---------------------------------------------------
            top10_list = parsed_data.get('top10', [])
            if top10_list:
                print(f"  > Saving {len(top10_list)} Rankings...")
                for item in top10_list:
                    # live_rankings 테이블에 저장 (run_count 없음)
                    db.save_rankings([{
                        "category": cat,
                        "rank": item.get('rank'),
                        "title": item.get('title'),
                        "meta_info": item.get('info', ''),
                        "score": 0 # 랭킹 아이템은 점수 0 처리
                    }])

            # ---------------------------------------------------
            # B. [메인 피드] 인물 뉴스 저장 (영어 기사 + 점수)
            # ---------------------------------------------------
            people_list = parsed_data.get('people', [])
            if people_list:
                print(f"  > Processing {len(people_list)} People Articles...")
                
                for person in people_list:
                    name = person.get('name')
                    facts = person.get('facts')
                    
                    if not name: continue

                    # Groq 기사 생성 (영어 + ###SCORE: XX)
                    full_text = engine.edit_with_groq(name, facts, cat)
                    
                    # --- 점수(Score) 파싱 로직 ---
                    score = 70 # 기본값
                    final_text = full_text
                    
                    if "###SCORE:" in full_text:
                        try:
                            parts = full_text.split("###SCORE:")
                            final_text = parts[0].strip() # 점수 제외한 본문
                            score_str = parts[1].strip()
                            # 숫자만 추출 (예: "85" 또는 "85/100")
                            score_match = re.search(r'\d+', score_str)
                            if score_match:
                                score = int(score_match.group())
                        except Exception as e:
                            print(f"    Warning: Score parsing failed ({e}). Defaulting to 70.")
                            score = 70
                    # ---------------------------

                    # 제목과 본문 분리
                    lines = final_text.split('\n')
                    # 제목에서 "Headline:", "Title:" 같은 접두어 제거
                    raw_title = lines[0]
                    title = re.sub(r'^(Headline:|Title:|Subject:)\s*', '', raw_title, flags=re.IGNORECASE).strip()
                    summary = "\n".join(lines[1:]).strip()
                    
                    # 네이버 이미지 검색 (한글 이름으로 검색해야 정확함)
                    img_url = naver.get_image(name)
                    
                    # 1. 아카이브 저장 (run_count 포함)
                    article_data = {
                        "category": cat,
                        "keyword": name,
                        "title": title,
                        "summary": summary,
                        "link": person.get('link', ''),
                        "image_url": img_url,
                        "score": score,  # AI가 부여한 점수
                        "likes": 0,
                        "query": original_query,
                        "raw_result": str(person),
                        "run_count": run_count 
                    }
                    db.save_to_archive(article_data)
                    
                    # 2. 라이브 뉴스 저장 (실시간 노출용)
                    live_data = {
                        "category": article_data['category'],
                        "keyword": article_data['keyword'],
                        "title": article_data['title'],
                        "summary": article_data['summary'],
                        "link": article_data['link'],
                        "image_url": article_data['image_url'],
                        "score": score, # AI가 부여한 점수 (정렬 기준이 됨)
                        "likes": 0
                    }
                    db.save_live_news([live_data])
                    print(f"    - Updated: {name} (Score: {score})")

        except json.JSONDecodeError:
            print(f"❌ [{cat}] JSON Parsing Error.")
        except Exception as e:
            print(f"❌ [{cat}] Unknown Error: {e}")

if __name__ == "__main__":
    run_automation()
