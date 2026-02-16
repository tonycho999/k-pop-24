import os
from supabase import create_client, Client

class DatabaseManager:
    def __init__(self):
        # 환경 변수 로드
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            print("⚠️ Warning: Supabase Credentials missing.")
            self.supabase = None
        else:
            self.supabase: Client = create_client(url, key)

    def save_live_news(self, data_list):
        """public.live_news 테이블에 데이터 저장"""
        if not self.supabase: return
        try:
            self.supabase.table("live_news").insert(data_list).execute()
        except Exception as e:
            print(f"  [DB Error] Live News Insert Failed: {e}")

    # [핵심 수정] main.py에서 이 함수 이름(save_rankings)을 호출하므로 반드시 있어야 합니다.
    def save_rankings(self, data_list):
        """public.live_rankings 테이블에 데이터 저장"""
        if not self.supabase: return
        try:
            # 말씀하신대로 테이블 이름은 'live_rankings'가 맞습니다.
            self.supabase.table("live_rankings").insert(data_list).execute()
        except Exception as e:
            print(f"  [DB Error] Rankings Insert Failed: {e}")

    def save_to_archive(self, article_data):
        """public.search_archive 테이블에 데이터 저장"""
        if not self.supabase: return
        try:
            self.supabase.table("search_archive").insert(article_data).execute()
        except Exception as e:
            print(f"  [DB Error] Archive Insert Failed: {e}")
