import os
import sys
from datetime import datetime
import pytz
from database import Database
from naver_api import NaverNewsAPI
from chart_api import ChartAPI

def run_news(db):
    # [뉴스 모드] 1시간마다 1개의 카테고리만 로테이션 수집
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    hour = now_kst.hour

    categories = ['k-pop', 'k-movie', 'k-drama', 'k-entertain', 'k-culture']
    target_category = categories[hour % 5]

    print("=" * 60)
    print(f"🕒 [NEWS KST Time] {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📰 [Target Category] {target_category.upper()}")
    print("=" * 60)
    
    news_api = NaverNewsAPI(db)
    news_api.run_pipeline(target_category)
    print("\n✅ Hourly News Automation Job Completed.")

def run_chart(db):
    # [차트 모드] 12시간마다 실행되어 5개 카테고리 전부 한 번에 업데이트
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)

    print("=" * 60)
    print(f"🕒 [CHART KST Time] {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Starting Chart Data Update for ALL Categories...")
    print("=" * 60)

    chart_api = ChartAPI(db)
    categories = ['k-pop', 'k-movie', 'k-drama', 'k-entertain', 'k-culture']
    
    for cat in categories:
        chart_api.update_chart(cat)
        
    print("\n✅ 12-Hour Chart Automation Job Completed.")

def main():
    db = Database()
    if not db.client:
        print("❌ DB connection failed. Exiting.")
        return

    # 실행 시 전달된 인수(argument) 확인
    if len(sys.argv) > 1 and sys.argv[1].lower() == "chart":
        run_chart(db)
    else:
        # 인수가 없거나 'news'이면 뉴스로 실행 (기본값)
        run_news(db)

if __name__ == "__main__":
    main()
