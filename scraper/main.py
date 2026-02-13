import sys
import os

# 모듈 import 문제 방지
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import time
from datetime import datetime
from dotenv import load_dotenv

# 필수 모듈 불러오기
from scraper import crawler, ai_engine, repository, update_rankings
from scraper.config import CATEGORY_MAP # 백업용 고정 키워드 임포트

load_dotenv()

def run_master_scraper():
    print("🚀 구글 트렌드 기반 9단계 마스터 엔진 가동...")
    
    # [1단계] 구글 실시간 트렌드 키워드 수집
    raw_trending_keywords = crawler.get_google_trending_keywords()
    
    categorized_keywords = {}

    if raw_trending_keywords:
        print(f"🔥 구글 트렌드 키워드 {len(raw_trending_keywords)}개 수집 성공. AI 분류 시작...")
        # [2~3단계] AI 분류 및 카테고리별 상위 키워드 선정
        categorized_keywords = ai_engine.ai_filter_and_rank_keywords(raw_trending_keywords)
        
        if not categorized_keywords:
            print("⚠️ AI 분류 결과가 없습니다. 고정 키워드로 전환합니다.")
            categorized_keywords = CATEGORY_MAP
    else:
        # [Fallback] 구글 트렌드 실패 시 고정 키워드 사용
        print("⚠️ 구글 키워드 수집 실패. 설정 파일의 [고정 키워드]를 사용하여 작업을 계속합니다.")
        categorized_keywords = CATEGORY_MAP

    # 카테고리별 루프 시작
    for category, keywords in categorized_keywords.items():
        try:
            print(f"\n📂 {category.upper()} 부문 처리 중 (키워드: {keywords})")

            # [4단계] 네이버 뉴스 검색
            raw_news = []
            for kw in keywords: 
                raw_news.extend(crawler.get_naver_api_news(kw))
            
            # [5단계] DB 중복 체크
            existing_links = repository.get_existing_links(category)
            # 70개까지만 후보 선정
            new_candidate_news = [n for n in raw_news if n['link'] not in existing_links][:70]

            if not new_candidate_news:
                print(f"    ✨ 새로운 뉴스가 없습니다.")
                continue

            # 본문 1,500자 및 이미지 확보
            print(f"    🕷️ 본문 크롤링 중 ({len(new_candidate_news)}개)...")
            for news_item in new_candidate_news:
                full_text, image_url = crawler.get_article_data(news_item['link'])
                news_item['full_content'] = full_text  
                news_item['crawled_image'] = image_url 

            # [6단계] 3중 AI 엔진을 이용한 평점 및 3단계 요약
            analyzed_list = ai_engine.ai_category_editor(category, new_candidate_news)
            
            if analyzed_list:
                # 점수 높은 순 정렬 후 상위 30개 선정
                analyzed_list.sort(key=lambda x: x.get('score', 0), reverse=True)
                top_30_news = analyzed_list[:30]
                
                # [7단계] DB 저장
                new_data_list = []
                for art in top_30_news:
                    idx = art.get('original_index')
                    if idx is not None and idx < len(new_candidate_news):
                        orig = new_candidate_news[idx]
                        
                        # 이미지 URL 결정 (크롤링된 이미지 우선, 없으면 placeholder)
                        final_img = orig.get('crawled_image')
                        if not final_img:
                             final_img = f"https://placehold.co/600x400/111/cyan?text={category}"

                        new_data_list.append({
                            "category": category, 
                            "title": art.get('eng_title', orig['title']),
                            "summary": art.get('summary', 'Summary not available.'), 
                            "link": orig['link'], 
                            "image_url": final_img,
                            "score": art.get('score', 5.0), 
                            "likes": 0, "dislikes": 0, 
                            "created_at": datetime.now().isoformat(),
                            "published_at": orig.get('published_at', datetime.now()).isoformat()
                        })
                
                if new_data_list:
                    repository.save_news(new_data_list)

            # [8~9단계] 슬롯 관리
            repository.manage_slots(category)

        except Exception as e:
            print(f"⚠️ {category} 처리 중 오류: {e}")
            continue

    print("\n🎉 모든 카테고리 수집 및 처리 완료.")

def main():
    print("🚀 K-Enter AI News Bot Master Mode Started...")
    try: update_rankings.update_rankings() 
    except: pass
    
    run_master_scraper()

if __name__ == "__main__":
    main()
