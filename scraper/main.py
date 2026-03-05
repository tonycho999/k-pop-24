import sys
import time
from database import Database
from naver_api import NaverTrendEngine
from chart_api import ChartEngine # Top 10 차트 엔진 (이름은 설정하신 대로 맞추세요)

def run_hourly_news(db):
    print("▶️ [MODE: NEWS] Starting Hourly 10-Person Update...")
    # 여기에 아까 작성한 1시간마다 인물 10명 기사 쓰는 로직(for문)을 넣습니다.
    # engine = NaverTrendEngine(db=db) ...

def run_top10_charts(db):
    print("▶️ [MODE: CHART] Starting 6-Hour Top 10 Charts Update...")
    # 여기에 기존 Top 10 차트 긁어와서 DB에 넣는 로직을 넣습니다.
    # chart_engine = ChartEngine() ...

def main():
    print("========================================")
    print("🚀 K-Trend Hybrid Scraper Started")
    print("========================================")

    db = Database()
    
    # GitHub Actions에서 넘겨준 명령어를 확인합니다 (기본값은 'all')
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "news":
        run_hourly_news(db)
    elif mode == "chart":
        run_top10_charts(db)
    else:
        # 수동으로 그냥 실행했을 땐 둘 다 돌림
        run_hourly_news(db)
        run_top10_charts(db)

    print("\n🎉 All Requested Tasks Completed!")

if __name__ == "__main__":
    main()
