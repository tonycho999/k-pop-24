import os
import sys
from datetime import datetime
import pytz
from database import Database
from naver_api import NaverNewsAPI
from chart_api import ChartAPI

def run_news(db):
    # [뉴스 모드] 4시간마다 실행되어 4개 카테고리 전부 한 번에 업데이트 (k-culture 제외)
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)

    # 💡 [핵심 수정] k-culture는 차트 봇이 전담하므로 제외, 4개만 남김
    categories = ['k-pop', 'k-movie', 'k-drama', 'k-entertain']

    print("=" * 60)
    print(f"🕒 [NEWS KST Time] {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
    print("📰 [Target Categories] ALL (4 Categories Batch Mode)")
    print("=" * 60)
    
    news_api = NaverNewsAPI(db)
    
    # 💡 [핵심 수정] 1개만 고르던 로직을 지우고, 4개를 연속으로 모두 실행!
    for cat in categories:
        news_api.run_pipeline(cat)
        
    print("\n✅ 4-Hour News Automation Job Completed.")

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
