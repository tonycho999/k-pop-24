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
    
    news_results = naver.fetch_smart_news()
    
    if news_results:
        db.save_news(news_results)
        print(f"✅ Saved {len(news_results)} heavily vetted articles to DB!")
    else:
        print("⚠️ No news processed.")

def run_chart_scraper():
    print("📊 Starting 4-Color Chart Scraper...")
    db = Database()
    model = ModelManager()
    chart_mgr = ChartManager(model_manager=model)
    
    categories = ["k-pop", "k-entertain", "k-actor", "k-culture"]
    
    for cat in categories:
        print(f"\n📊 --- Processing {cat} ---")
        
        context = ""
        # 💡 배우와 문화 카테고리만 뉴스 DB에서 데이터를 꺼내옵니다.
        # K-Pop과 K-Entertain은 ChartManager 내부에서 직접 웹 검색을 돌리므로 context가 불필요합니다.
        if cat in ["k-actor", "k-culture"]:
            context = db.get_recent_news_context(cat)
            if not context:
                print(f"⚠️ [Skip] Valid real-time data not found for {cat}.")
                continue
            
        top10 = chart_mgr.process_chart(cat, context, "Naver News / Web Data")
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
