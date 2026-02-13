import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# 모듈 import 문제 방지
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

# 필수 모듈 불러오기
from scraper import crawler, ai_engine, repository
from scraper.config import CATEGORY_SEEDS, TOP_RANK_LIMIT

load_dotenv()

def run_master_scraper():
    print(f"🚀 K-Enter Trend Master 가동 시작: {datetime.now()}")
    
    # 5개 카테고리 루프
    for category, seeds in CATEGORY_SEEDS.items():
        print(f"\n📂 [{category.upper()}] 트렌드 분석 시작")
        
        # [1단계] 씨앗 수집 (Seed Search)
        # 네이버 뉴스 API를 통해 광범위한 제목 수집 (차단 방지 & 최신성 확보)
        seed_titles = []
        try:
            for seed in seeds:
                # 각 시드당 20~30개 정도만 가져와서 믹스
                news = crawler.get_naver_api_news(seed, display=20)
                seed_titles.extend([n['title'] for n in news])
            
            # 중복 제거
            seed_titles = list(set(seed_titles))
            print(f"   🌱 원석 수집 완료: {len(seed_titles)}개의 제목 확보")
        except Exception as e:
            print(f"   ⚠️ 씨앗 수집 중 오류: {e}")
            continue
        
        # [2단계] 엔티티 추출 및 랭킹 (AI Mining)
        top_keywords = ai_engine.extract_top_entities(category, seed_titles)
        
        if not top_keywords:
            print("   ⚠️ 키워드 추출 실패. 다음 카테고리로 이동.")
            continue
            
        print(f"   💎 추출된 랭킹(Top {len(top_keywords)}): {', '.join(top_keywords[:5])}...")

        # [3단계] 정밀 검색 및 합성 (Deep Dive & Synthesis)
        category_news_list = []
        
        # 상위 N개(설정값 30개)만 처리
        target_keywords = top_keywords[:TOP_RANK_LIMIT]
        
        for rank, kw in enumerate(target_keywords):
            print(f"   🔍 Rank {rank+1}: '{kw}' 분석 중...")
            
            try:
                # 해당 키워드로 최신 뉴스 검색
                raw_articles = crawler.get_naver_api_news(kw, display=10)
                
                if not raw_articles:
                    continue

                # 본문 크롤링 (상위 3~5개 기사 합치기)
                full_contents = []
                main_image = None
                valid_link = raw_articles[0]['link']
                published_at = raw_articles[0].get('published_at', datetime.now()).isoformat()

                for art in raw_articles[:5]:
                    text, img = crawler.get_article_data(art['link'])
                    if text: full_contents.append(text)
                    # 첫 번째로 발견된 유효한 이미지를 메인 이미지로 사용
                    if not main_image and img: main_image = img

                # AI 요약 (브리핑 생성)
                if full_contents:
                    briefing = ai_engine.synthesize_briefing(kw, full_contents)
                    
                    # 이미지 없을 경우 플레이스홀더
                    final_img = main_image or f"https://placehold.co/600x400/111/cyan?text={kw}"

                    news_item = {
                        "category": category,
                        "rank": rank + 1,       # 랭킹 정보 추가
                        "keyword": kw,          # 키워드 정보 추가
                        "title": f"[{rank+1}] {kw}: Top Trending News", # 제목 포맷팅
                        "summary": briefing,
                        "link": valid_link,     # 대표 링크 하나 제공
                        "image_url": final_img,
                        "score": 10.0 - (rank * 0.1), # 랭킹 기반 점수 (1위 10점, 2위 9.9점...)
                        "likes": 0, "dislikes": 0,
                        "created_at": datetime.now().isoformat(),
                        "published_at": published_at
                    }
                    category_news_list.append(news_item)
                
                # API 보호를 위한 짧은 대기
                time.sleep(0.5)
                
            except Exception as e:
                print(f"      ⚠️ '{kw}' 처리 실패: {e}")
                continue

        # [4단계] DB 저장 (교체 방식)
        if category_news_list:
            # 1. 상위 10개 아카이브 저장
            repository.save_to_archive(category_news_list[:10])
            
            # 2. Live News 해당 카테고리 전체 교체
            repository.refresh_live_news(category, category_news_list)

    print("\n🎉 모든 카테고리 150개 뉴스 업데이트가 완료되었습니다.")

if __name__ == "__main__":
    run_master_scraper()
