import sys
import os
import time
from datetime import datetime, timedelta
from dateutil import parser
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from scraper import crawler, ai_engine, repository
from scraper.config import CATEGORY_SEEDS

load_dotenv()

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
        
        # [1단계] 씨앗 데이터 수집 (24시간 이내)
        raw_text_data = [] 
        
        try:
            for seed in seeds:
                news_items = crawler.get_naver_api_news(seed, display=20)
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
        
        # [2단계] AI 키워드 추출 및 정체 분류
        # (여기서 이미 Netflix, MBC 같은 organization은 걸러져서 옴)
        top_entities = ai_engine.extract_top_entities(category, "\n".join(raw_text_data))
        
        if not top_entities: 
            print("   ⚠️ 키워드 추출 실패")
            continue
            
        print(f"   💎 유효 키워드 (Top 5): {', '.join([e['keyword'] for e in top_entities[:5]])}...")

        # [3단계] 키워드별 심층 분석 (30위까지)
        category_news_list = []
        target_list = top_entities[:TARGET_RANK_LIMIT]
        
        for rank, entity in enumerate(target_list):
            kw = entity.get('keyword')
            k_type = entity.get('type', 'content') # person 또는 content
            
            print(f"   🔍 Rank {rank+1}: '{kw}' ({k_type}) 분석 중...")
            
            try:
                # 기사 검색
                raw_articles = crawler.get_naver_api_news(kw, display=50)
                if not raw_articles: continue

                full_contents = []
                main_image = None
                valid_article_count = 0
                
                for art in raw_articles:
                    if not is_within_24h(art.get('pubDate')): continue
                        
                       text, img = crawler.get_article_data(art['link'])
                    
                    if text: 
                        full_contents.append(text)
                        valid_article_count += 1
                        if not main_image and img:
                            if img.startswith("http://"): img = img.replace("http://", "https://")
                            main_image = img
                            
                    if valid_article_count >= 30: break

                if not full_contents:
                    print(f"      ☁️ '{kw}': 유효 기사 없음 (Skip)")
                    continue

                # [4단계] AI 브리핑 생성
                briefing = ai_engine.synthesize_briefing(kw, full_contents)
                
                if not briefing:
                    print(f"      🗑️ '{kw}': 내용 부실로 폐기")
                    continue
                
                ai_score = round(9.9 - (rank * 0.1), 1)
                if ai_score < 7.0: ai_score = 7.0

                final_img = main_image or f"https://placehold.co/600x400/111/cyan?text={kw}"

                news_item = {
                    "category": category,
                    "rank": rank + 1,
                    "keyword": kw,
                    "type": k_type,
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
                time.sleep(2.0) 
                
            except Exception as e:
                print(f"      ⚠️ '{kw}' 처리 중 에러: {e}")
                continue

        # [5단계] 데이터베이스 분산 저장
        if category_news_list:
            print(f"   💾 저장 시작: 총 {len(category_news_list)}개")
            
            # 1. Live News: 모든 뉴스 저장 (사람+작품)
            repository.refresh_live_news(category, category_news_list)
            
            # 2. Trending Rankings: 오직 'content' 타입만 골라서 랭킹 저장
            content_only_list = [n for n in category_news_list if n.get('type') == 'content']
            
            # (만약 content가 부족하면 어쩔 수 없이 섞지만, 기본적으로는 content만 저장)
            final_ranking_list = []
            if len(content_only_list) >= 3:
                source_list = content_only_list
            else:
                source_list = category_news_list # 비상시 섞어서

            # 랭킹 번호표 다시 붙이기 (1위부터 차례대로)
            for new_rank, item in enumerate(source_list[:10]):
                ranked_item = item.copy()
                ranked_item['rank'] = new_rank + 1
                final_ranking_list.append(ranked_item)
                
            repository.update_sidebar_rankings(category, final_ranking_list)
            
            # 3. Search Archive: 7.0점 이상
            high_score_news = [n for n in category_news_list if n['score'] >= 7.0]
            if high_score_news:
                repository.save_to_archive(high_score_news)

    print("\n🎉 전체 업데이트 완료.")

if __name__ == "__main__":
    run_master_scraper()
