import sys
from database import Database
from model_manager import ModelManager
from naver_api import NaverNewsAPI
from chart_api import ChartManager

def run_news_scraper():
    print("🚀 Starting Smart News Scraper (Reverse Matching DB)...")
    db = Database()
    model = ModelManager()
    naver = NaverNewsAPI(db_client=db, model_manager=model)
    
    # 똑똑해진 역방향 엔진 가동 (50세 이하 연예인만 필터, 부서 자동 이동)
    news_results = naver.fetch_smart_news()
    
    if news_results:
        db.save_news(news_results)
        print(f"✅ Saved {len(news_results)} heavily vetted articles to DB!")
    else:
        print("⚠️ No news processed.")

def run_chart_scraper():
    print("📊 Starting Chart Scraper...")
    db = Database()
    model = ModelManager()
    chart_mgr = ChartManager(model_manager=model)
    
    categories = ["k-actor", "k-pop", "k-entertain", "k-culture"]
    
    for cat in categories:
        print(f"\n📊 --- Processing {cat} ---")
        # 기존에 DB에 저장된 뉴스 데이터를 기반으로 차트 생성
        context = db.get_recent_news_context(cat)
        
        if not context:
            print(f"⚠️ [Skip] Valid real-time data not found for {cat}.")
            continue
            
        top10 = chart_mgr.process_chart(cat, context, "Naver News DB")
        if top10:
            db.save_chart_results(cat, top10)
            print(f"  💾 [DB 저장 성공] {cat} 차트 10개 업데이트 완료!")
        else:
            print(f"  ❌ {cat} 차트 생성 실패.")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "news"
    
    if mode == "news":
        run_news_scraper()
    elif mode == "chart":
        run_chart_scraper()
    else:
        print("Invalid mode. Use 'news' or 'chart'.")
