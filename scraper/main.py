import json
import re
import os
from news_api import NewsEngine
from naver_api import NaverManager
from database import DatabaseManager

def clean_json_text(text):
    """AI 응답에서 순수 JSON만 추출"""
    match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1:
        return text[start:end+1]
    return text.strip()

def run_automation():
    print("🚀 K-Enter24 Automation Started (KR Search -> EN Save)")
    
    db = DatabaseManager()
    engine = NewsEngine()
    naver = NaverManager()
    
    run_count = int(os.environ.get("RUN_COUNT", 0))
    
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]

    for cat in categories:
        print(f"\n[{cat}] Processing...")
        try:
            # 1. Perplexity: 한국어로 데이터 수집 (정확도 최우선)
            raw_data_str, original_query = engine.get_trends_and_rankings(cat)
            
            cleaned_str = clean_json_text(raw_data_str)
            if not cleaned_str or cleaned_str == "{}":
                print(f"⚠️ [{cat}] No data returned.")
                continue

            parsed_data = json.loads(cleaned_str)
            
            # ---------------------------------------------------
            # A. [사이드바] TOP 10 랭킹 (한국어 -> 영어 번역 후 저장)
            # ---------------------------------------------------
            korean_top10 = parsed_data.get('top10', [])
            if korean_top10:
                print(f"  > Translating {len(korean_top10)} Rankings to English...")
                
                # [핵심] Groq을 이용해 리스트 일괄 번역
                english_top10 = engine.translate_top10_to_english(korean_top10)
                
                for item in english_top10:
                    db.save_rankings([{
                        "category": cat,
                        "rank": item.get('rank'),
                        "title": item.get('title'), # 이제 영어 제목임
                        "meta_info": item.get('info', ''), # 이제 영어 설명임
                        "score": 0
                    }])

            # ---------------------------------------------------
            # B. [메인 피드] 인물 뉴스 (한국어 팩트 -> 영어 기사 작성)
            # ---------------------------------------------------
            people_list = parsed_data.get('people', [])
            if people_list:
                print(f"  > Processing {len(people_list)} People Articles...")
                
                for person in people_list:
                    name_kr = person.get('name')
                    facts_kr = person.get('facts')
                    
                    if not name_kr: continue

                    # Groq: 한국어 팩트를 읽고 영어 기사 + 점수 생성
                    full_text = engine.edit_with_groq(name_kr, facts_kr, cat)
                    
                    # 점수 파싱
                    score = 70
                    final_text = full_text
                    
                    if "###SCORE:" in full_text:
                        try:
                            parts = full_text.split("###SCORE:")
                            final_text = parts[0].strip()
                            score_match = re.search(r'\d+', parts[1])
                            if score_match:
                                score = int(score_match.group())
                        except:
                            pass

                    # 제목/본문 분리
                    lines = final_text.split('\n')
                    raw_title = lines[0]
                    title = re.sub(r'^(Headline:|Title:)\s*', '', raw_title, flags=re.IGNORECASE).strip()
                    summary = "\n".join(lines[1:]).strip()
                    
                    # 네이버 이미지 검색 (한국어 이름으로 검색해야 정확함)
                    img_url = naver.get_image(name_kr)
                    
                    # 아카이브 저장 (영어 데이터)
                    article_data = {
                        "category": cat,
                        "keyword": name_kr, # 검색용 키워드는 한국어로 남겨둘 수도, 영어로 바꿀 수도 있음. 여기선 원본 유지.
                        "title": title,     # 영어 제목
                        "summary": summary, # 영어 본문
                        "link": person.get('link', ''),
                        "image_url": img_url,
                        "score": score,
                        "likes": 0,
                        "query": original_query,
                        "raw_result": str(person),
                        "run_count": run_count 
                    }
                    db.save_to_archive(article_data)
                    
                    # 라이브 뉴스 저장
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
                    print(f"    - Published: {title[:30]}... (Score: {score})")

        except json.JSONDecodeError:
            print(f"❌ [{cat}] JSON Parsing Error.")
        except Exception as e:
            print(f"❌ [{cat}] Unknown Error: {e}")

if __name__ == "__main__":
    run_automation()
