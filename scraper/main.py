import sys
from database import Database
from model_manager import ModelManager
from naver_api import NaverNewsAPI
from chart_api import ChartManager

def run_news_scraper():
    print("🚀 Starting 1-Hour News Engine (Auto-Scrubbing & Validation ON)...")
    db = Database()
    
    # ModelManager를 통해 Gemini 최적 모델 이름 획득
    model_mgr = ModelManager(provider="gemini")
    best_model_name = model_mgr.get_best_model()
    
    # 3중 방어망이 탑재된 뉴스 API 가동
    naver = NaverNewsAPI(db_client=db, model_name=best_model_name)
    news_results = naver.run_7_step_pipeline()
    
    # 대표님의 database.py에 있는 통합 저장 로직 호출 (자동 삭제 기능 포함)
    for category, items in news_results.items():
        if items:
            db.save_news_results(category, items)
            
    print("✅ 1-Hour News Cycle Complete. DB cleaned and updated.")

def run_chart_scraper():
    print("📊 Starting 4-Color Chart Engine (Twice a day)...")
    db = Database()
    
    model_mgr = ModelManager(provider="gemini")
    best_model_name = model_mgr.get_best_model()
    chart_mgr = ChartManager(model_name=best_model_name)
    
    categories = ["k-pop", "k-entertain", "k-actor", "k-culture"]
    
    for cat in categories:
        print(f"\n📊 --- Processing {cat} Chart ---")
        
        context = ""
        # 배우와 문화 차트는 오늘 하루(24시간) 작성된 뉴스 데이터를 컨텍스트로 사용
        if cat in ["k-actor", "k-culture"]:
            try:
                res = db.client.table("live_news").select("title, summary").eq("category", cat).execute()
                if res.data:
                    context = "\n".join([f"- {d['title']}: {d['summary']}" for d in res.data])
            except Exception as e:
                print(f"⚠️ Failed to load context for {cat}: {e}")
                
        # 팩트(음원/시청률) 또는 컨텍스트(뉴스)를 기반으로 차트 생성
        top10 = chart_mgr.process_chart(cat, context)
        
        if top10:
            db.save_chart_results(cat, top10)
            print(f"  💾 {cat} Top 10 Chart updated successfully!")
        else:
            print(f"  ❌ {cat} Chart generation failed.")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "news"
    
    if mode == "news":
        # 매시간 구동용 (기사 작성 및 신인 발굴)
        run_news_scraper()
    elif mode == "chart":
        # 하루 2번 구동용 (순위 차트 갱신)
        run_chart_scraper()
    else:
        print("Invalid mode. Use 'news' or 'chart'.")
