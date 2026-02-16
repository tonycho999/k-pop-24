import os
from supabase import create_client, Client

class DatabaseManager:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase: Client = create_client(url, key)

    def save_to_archive(self, article_data):
        """사용자가 검색 활용 가능한 전체 기사 아카이브 저장"""
        try:
            self.supabase.table("search_archive").insert(article_data).execute()
        except Exception as e:
            print(f"Archive 저장 실패: {e}")

    def update_live_news(self, news_data):
        """본문 인물 중심 실시간 피드 저장"""
        try:
            self.supabase.table("live_news").insert(news_data).execute()
        except Exception as e:
            print(f"Live News 저장 실패: {e}")

    def update_live_rankings(self, ranking_data):
        """사이드바 프로그램/콘텐츠 TOP 10 저장"""
        try:
            self.supabase.table("live_rankings").insert(ranking_data).execute()
        except Exception as e:
            print(f"Rankings 저장 실패: {e}")

    def clean_old_data(self, table, category, limit=30):
        """실시간성을 위해 기존 데이터 정리 (Archive 제외)"""
        try:
            # 카테고리별로 최신 순 정렬 후 limit 밖의 데이터 삭제 로직
            # 실제 운영 환경에 맞춰 SQL 함수 호출 혹은 파이썬 로직 구현
            pass
        except Exception as e:
            print(f"Data Cleaning 실패: {e}")
