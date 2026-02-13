import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from scraper import crawler, ai_engine, repository
from scraper.config import CATEGORY_SEEDS

load_dotenv()

# 총 30위까지 분석
TARGET_RANK_LIMIT = 30 

def run_master_scraper():
    print(f"🚀 K-Enter Trend Master 가동 시작: {datetime.now()}")
    
    for category, seeds in CATEGORY_SEEDS.items():
        print(f"\n📂 [{category.upper()}] 트렌드 분석 시작")
        
        # [1단계] 씨앗 수집
        seed_titles = []
        try:
            for seed in seeds:
                news = crawler.get_naver_api_news(seed, display=20)
                seed_titles.extend([n['title'] for n in news])
            seed_titles = list(set(seed_titles))
            print(f"   🌱 원석 수집 완료: {len(seed_titles)}개")
        except Exception as e:
            print(f"   ⚠️ 씨앗 수집 오류: {e}")
            continue
        
        # [2단계] 키워드 추출 (사람/작품 분류 포함)
        # top_entities는 [{'keyword': 'BTS', 'type': 'person'}, ...] 형태
        top_entities = ai_engine.extract_top_entities(category, seed_titles)
        if not top_entities: continue
            
        print(f"   💎 추출된 키워드 (Top 5): {', '.join([e['keyword'] for e in top_entities[:5]])}...")

        # [3단계] 키워드별 심층 분석 (30위까지)
        category_news_list = []
        
        # 30개까지만 처리
        target_list = top_entities[:TARGET_RANK_LIMIT]
        
        for rank, entity in enumerate(target_list):
            kw = entity.get('keyword')
            k_type = entity.get('type', 'content') # 기본값 content
            
            print(f"   🔍 Rank {rank+1}: '{kw}' ({k_type}) 처리 중...")
            
            try:
                # 3-1. 기사 검색
                raw_articles = crawler.get_naver_api_news(kw, display=10)
                if not raw_articles: continue

                full_contents = []
                main_image = None
                
                # 3-2. 본문 크롤링
                for art in raw_articles[:5]:
                    text, img = crawler.get_article_data(art['link'], target_keyword=kw)
                    
                    if text: full_contents.append(text)
                    if not main_image and img:
                        if img.startswith("http://"): img = img.replace("http://", "https://")
                        main_image = img

                # 3-3. (비상용) 본문 실패 시 API Description 사용
                if not full_contents:
                    for art in raw_articles[:5]:
                        if art.get('description'):
                            full_contents.append(art['description'])

                if not full_contents:
                    print(f"      ☁️ '{kw}': 정보 부족으로 스킵")
                    continue

                # 3-4. AI 요약
                briefing = ai_engine.synthesize_briefing(kw, full_contents)
                
                # 평점 계산 (기본 7.0 이상)
                ai_score = round(9.9 - (rank * 0.1), 1)
                if ai_score < 7.0: ai_score = 7.0

                final_img = main_image or f"[https://placehold.co/600x400/111/cyan?text=](https://placehold.co/600x400/111/cyan?text=){kw}"

                news_item = {
                    "category": category,
                    "rank": rank + 1,
                    "keyword": kw,
                    "type": k_type, # 타입 정보 저장 (나중에 필터링용)
                    "title": f"[{kw}] News Update",
                    "summary": briefing,
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
                print(f"      ⚠️ '{kw}' 처리 실패: {e}")
                continue

        # [4단계] 저장 (사용자 요구사항 반영)
        if category_news_list:
            # 1. Live News: 1~30위 전부 저장 (사람 포함)
            repository.refresh_live_news(category, category_news_list)
            
            # 2. Trending Rankings: 'content' 타입인 것만 골라서 Top 10 저장
            # (사람 이름 제외, 곡명/작품명만)
            content_only_list = [n for n in category_news_list if n.get('type') == 'content']
            
            # 만약 content 타입이 너무 적으면 어쩔 수 없이 섞이지 않도록, 있는 것만이라도 저장
            repository.update_sidebar_rankings(category, content_only_list[:10])
            
            # 3. Search Archive: 평점 7.0 이상만 저장
            high_score_news = [n for n in category_news_list if n['score'] >= 7.0]
            if high_score_news:
                repository.save_to_archive(high_score_news)

    print("\n🎉 전체 업데이트 완료.")

if __name__ == "__main__":
    run_master_scraper()
