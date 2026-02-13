import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from scraper import crawler, ai_engine, repository
from scraper.config import CATEGORY_SEEDS, TOP_RANK_LIMIT

load_dotenv()

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
            print(f"   ⚠️ 씨앗 수집 중 오류: {e}")
            continue
        
        # [2단계] 키워드 추출
        top_keywords = ai_engine.extract_top_entities(category, seed_titles)
        if not top_keywords: continue
            
        print(f"   💎 추출된 랭킹: {', '.join(top_keywords[:5])}...")

        # [3단계] 키워드별 심층 분석
        category_news_list = []
        target_keywords = top_keywords[:TOP_RANK_LIMIT]
        
        for rank, kw in enumerate(target_keywords):
            print(f"   🔍 Rank {rank+1}: '{kw}' 요약 중...")
            
            try:
                raw_articles = crawler.get_naver_api_news(kw, display=10)
                if not raw_articles: continue

                full_contents = []
                main_image = None
                
                # 상위 5개 기사 확인
                for art in raw_articles[:5]:
                    # 🚨 [핵심] get_article_data에 키워드를 넘겨서 검증시킴
                    text, img = crawler.get_article_data(art['link'], target_keyword=kw)
                    
                    if text: 
                        full_contents.append(text)
                    
                    if not main_image and img:
                        if img.startswith("http://"):
                            img = img.replace("http://", "https://")
                        main_image = img

                # 유효한 본문이 하나도 없으면 건너뜀 (쓰레기 요약 방지)
                if not full_contents:
                    print(f"      ☁️ '{kw}': 관련 본문 없음 (Skip)")
                    continue

                # AI 요약 수행
                briefing = ai_engine.synthesize_briefing(kw, full_contents)
                
                # AI가 '정보 없음'이라고 답했으면 저장 안 함
                if "No specific news" in briefing:
                     print(f"      ☁️ '{kw}': AI가 요약할 정보가 없다고 판단함.")
                     continue

                final_img = main_image or f"https://placehold.co/600x400/111/cyan?text={kw}"

                news_item = {
                    "category": category,
                    "rank": rank + 1,
                    "keyword": kw,
                    "title": f"[{kw}] Key Trends & Issues",
                    "summary": briefing,
                    "link": None,            # 링크 X
                    "image_url": final_img,  # 이미지 O (HTTPS)
                    "score": 10.0 - (rank * 0.1),
                    "likes": 0, "dislikes": 0,
                    "created_at": datetime.now().isoformat(),
                    "published_at": datetime.now().isoformat()
                }
                category_news_list.append(news_item)
                time.sleep(0.5)
                
            except Exception as e:
                print(f"      ⚠️ '{kw}' 처리 실패: {e}")
                continue

        # [4단계] 저장
        if category_news_list:
            repository.save_to_archive(category_news_list[:10])
            repository.refresh_live_news(category, category_news_list)

    print("\n🎉 업데이트 완료.")

if __name__ == "__main__":
    run_master_scraper()
