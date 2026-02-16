import json
import re
from news_api import NewsEngine
from naver_api import NaverManager
from database import DatabaseManager

def clean_json_text(text):
    """
    AI가 응답에 포함할 수 있는 마크다운 코드 블록(```json ... ```)을 제거하고
    순수 JSON 문자열만 추출하는 함수
    """
    # 1. ```json 과 ``` 사이의 내용만 추출 시도
    match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 2. 매칭 안 되면 원본 텍스트 반환 (이미 순수 JSON일 경우)
    return text.strip()

def run_automation():
    print("🚀 K-Enter24 자동화 시스템 시작...")
    
    # 1. 매니저 인스턴스 생성
    db = DatabaseManager()
    engine = NewsEngine()
    naver = NaverManager()
    
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]

    for cat in categories:
        print(f"\n[{cat}] 카테고리 작업 시작")
        try:
            # 2. Perplexity에게 데이터 요청 (인물 + 순위)
            # engine.get_trends_and_rankings 함수가 (JSON문자열, 질문텍스트)를 반환한다고 가정
            raw_data_str, original_query = engine.get_trends_and_rankings(cat)
            
            # 3. [핵심 수정] 문자열을 JSON(딕셔너리)으로 변환 (parsed_data 정의!)
            cleaned_str = clean_json_text(raw_data_str)
            parsed_data = json.loads(cleaned_str)
            
            # --- A. 사이드바용 TOP 10 저장 ---
            top10_list = parsed_data.get('top10', [])
            print(f"  > TOP 10 리스트 {len(top10_list)}개 발견")
            
            for i, item in enumerate(top10_list):
                db.save_rankings([{
                    "category": cat,
                    "rank": i + 1,
                    "title": item.get('title'),
                    "meta_info": item.get('info', '')
                }])

            # --- B. 본문용 인물 기사 저장 ---
            people_list = parsed_data.get('people', [])
            print(f"  > 화제 인물 {len(people_list)}명 발견. 기사 생성 시작...")

            for person in people_list:
                name = person.get('name')
                facts = person.get('facts')
                
                if not name or not facts:
                    continue

                # Groq으로 기사 요약/편집
                full_article = engine.edit_with_groq(name, facts, cat)
                
                # 네이버 이미지 검색
                img_url = naver.get_image(name)
                
                # 저장할 데이터 뭉치
                article_data = {
                    "category": cat,
                    "keyword": name,
                    "title": full_article.split('\n')[0].replace('제목:', '').strip(), # 첫 줄을 제목으로
                    "summary": full_article,
                    "link": person.get('link', ''),
                    "image_url": img_url,
                    "query": original_query,
                    "raw_result": str(person), # 나중을 위해 원본 데이터 백업
                    "score": 0, # 초기값
                    "likes": 0
                }

                # 1. 아카이브(전체 저장소)에 저장
                db.save_to_archive(article_data)
                
                # 2. 실시간 뉴스(메인 피드)에 저장
                # raw_result, query 등 불필요한 필드는 제외하고 live_news에 저장
                live_data = {
                    "category": article_data['category'],
                    "keyword": article_data['keyword'],
                    "title": article_data['title'],
                    "summary": article_data['summary'],
                    "link": article_data['link'],
                    "image_url": article_data['image_url'],
                    "score": 0,
                    "likes": 0
                }
                db.save_live_news([live_data])
                print(f"    - {name} 기사 발행 완료")

        except json.JSONDecodeError as e:
            print(f"⚠️ [{cat}] JSON 변환 실패: AI 응답이 올바른 JSON 형식이 아닙니다.\n에러내용: {e}")
        except Exception as e:
            print(f"❌ [{cat}] 처리 중 알 수 없는 오류 발생: {e}")

if __name__ == "__main__":
    run_automation()
