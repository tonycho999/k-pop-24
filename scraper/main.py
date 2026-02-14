import sys
import os
import time
from datetime import datetime, timedelta
from dateutil import parser
from dotenv import load_dotenv

# 상위 디렉토리 참조 설정
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from scraper import crawler, ai_engine, repository
from scraper.config import CATEGORY_SEEDS

load_dotenv()

# 유료 버전의 화력을 활용해 분석 범위를 30위까지 확대
TARGET_RANK_LIMIT = 30 

def is_within_24h(date_str):
    if not date_str: return False
    try:
        pub_date = parser.parse(date_str)
        if pub_date.tzinfo:
            pub_date = pub_date.replace(tzinfo=None)
        now = datetime.now()
        diff = now - pub_date
        return diff <= timedelta(hours=24)
    except:
        return False

def run_master_scraper():
    print(f"🚀 K-Enter Trend Master 가동 시작: {datetime.now()}")
    
    for category, seeds in CATEGORY_SEEDS.items():
        print(f"\n📂 [{category.upper()}] 트렌드 분석 시작")
        
        # [1단계] 씨앗 데이터 수집 (24시간 이내 뉴스 요약본들)
        raw_text_data = [] 
        
        try:
            for seed in seeds:
                # [수정] 24시간 이내 뉴스를 더 많이 확보하기 위해 display를 100으로 상향
                news_items = crawler.get_naver_api_news(seed, display=100)
                for item in news_items:
                    if is_within_24h(item.get('pubDate')):
                        combined_text = f"Title: {item['title']}\nSummary: {item['description']}"
                        raw_text_data.append(combined_text)
            
            # AI 입력용 데이터 제한
            raw_text_data = raw_text_data[:60]
            print(f"   🌱 24시간 내 유효 기사 수집: {len(raw_text_data)}개")
            
            if len(raw_text_data) < 1:
                print("   ⚠️ 기사가 너무 적어 스킵합니다.")
                continue
                
        except Exception as e:
            print(f"   ⚠️ 씨앗 수집 오류: {e}")
            continue
        
        # [2단계] AI 키워드 추출
        top_entities = ai_engine.extract_top_entities(category, "\n".join(raw_text_data))
        
        if not top_entities: 
            print("   ⚠️ 키워드 추출 실패 혹은 유효한 키워드 없음")
            continue
            
        print(f"   💎 유효 키워드 (Top 5): {', '.join([e['keyword'] for e in top_entities[:5]])}...")

        # [3단계] 키워드별 심층 분석 (30위까지)
        category_news_list = []
        target_list = top_entities[:TARGET_RANK_LIMIT]
        
        for rank, entity in enumerate(target_list):
            kw = entity.get('keyword')
            k_type = entity.get('type', 'content')
            
            print(f"   🔍 Rank {rank+1}: '{kw}' ({k_type}) 분석 중...")
            
            try:
                # [수정] 특정 키워드 검색 시에도 기사를 100개로 상향
                raw_articles = crawler.get_naver_api_news(kw, display=100)
                if not raw_articles: continue

                full_contents = []
                main_image = None
                valid_article_count = 0
                
                for art in raw_articles:
                    if not is_within_24h(art.get('pubDate')): continue
                    
                    # [들여쓰기 수정] 에러가 났던 부분의 공백을 주변 코드와 맞췄습니다.
                    text, img = crawler.get_article_data(art['link'])
                    
                    if text: 
                        full_contents.append(text)
                        valid_article_count += 1
                        if not main_image and img:
                            if img.startswith("http://"): 
                                img = img.replace("http://", "https://")
                            main_image = img
                            
                    if valid_article_count >= 30: 
                        break

                if not full_contents:
                    print(f"      ☁️ '{kw}': 유효 기사 수집 실패 (Skip)")
                    continue

                # [4단계] AI 브리핑 및 제목 생성
                # [수정] 이제 AI가 제목(title)과 내용(summary)을 딕셔너리로 반환합니다.
                ai_data = ai_engine.synthesize_briefing(kw, full_contents)
                
                if not ai_data or not ai_data.get('summary'):
                    print(f"      🗑️ '{kw}': 브리핑 생성 실패로 폐기")
                    continue
                
                ai_score = round(9.9 - (rank * 0.1), 1)
                if ai_score < 7.0: ai_score = 7.0

                final_img = main_image or f"https://placehold.co/600x400/111/cyan?text={kw}"

                news_item = {
                    "category": category,
                    "rank": rank + 1,
                    "keyword": kw,
                    "type": k_type,
                    # [수정] 고정된 제목 대신 AI가 생성한 제목을 사용합니다.
                    "title": ai_data.get('title', f"[{kw}] Special Report"),
                    "summary": ai_data.get('summary'),
                    "link": None,
                    "image_url": final_img,
                    "score": ai_score,
                    "likes": 0, "dislikes": 0,
                    "created_at": datetime.now().isoformat(),
                    "published_at": datetime.now().isoformat()
                }
                category_news_list.append(news_item)
                
                time.sleep(0.5) 
                
            except Exception as e:
                print(f"      ⚠️ '{kw}' 처리 중 에러: {e}")
                continue

        # [5단계] 데이터베이스 분산 저장
        if category_news_list:
            print(f"   💾 저장 시작: 총 {len(category_news_list)}개")
            repository.refresh_live_news(category, category_news_list)
            
            content_only_list = [n for n in category_news_list if n.get('type') == 'content']
            final_ranking_list = []
            source_list = content_only_list if len(content_only_list) >= 3 else category_news_list

            for new_rank, item in enumerate(source_list[:10]):
                ranked_item = item.copy()
                ranked_item['rank'] = new_rank + 1
                final_ranking_list.append(ranked_item)
                
            repository.update_sidebar_rankings(category, final_ranking_list)
            repository.save_to_archive(category_news_list)

    print("\n🎉 전체 업데이트 완료.")

if __name__ == "__main__":
    run_master_scraper()
