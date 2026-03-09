import os
from datetime import datetime
import pytz
from database import Database
from naver_api import NaverNewsAPI
from chart_api import ChartAPI

def main():
    db = Database()
    if not db.client:
        print("❌ DB connection failed. Exiting.")
        return

    # KST 기준 현재 시간을 구해 5개의 카테고리로 당번을 정합니다.
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    hour = now_kst.hour

    categories = ['k-pop', 'k-movie', 'k-drama', 'k-entertain', 'k-culture']
    target_category = categories[hour % 5]

    print("=" * 60)
    print(f"🕒 [KST Time] {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 [Target Category] {target_category.upper()}")
    print("=" * 60)

    # 1. 차트/랭킹 업데이트 (KOBIS & 시청률 등)
    print("\n📊 Starting Chart Data Update...")
    chart_api = ChartAPI(db)
    chart_api.update_chart(target_category)

    # 2. 메인 뉴스 직수집 파이프라인 가동
    print(f"\n📰 Starting Direct Scraping Pipeline for {target_category.upper()}...")
    news_api = NaverNewsAPI(db)
    news_api.run_pipeline(target_category)

    print("\n✅ Hourly Automation Job Completed Successfully.")

if __name__ == "__main__":
    main()
