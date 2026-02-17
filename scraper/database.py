import os
import json
from supabase import create_client, Client

class DatabaseManager:
    def __init__(self):
        # 환경 변수 로드 (main.py와 동일하게 맞춤)
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            print("⚠️ [DB Init] Warning: Supabase Credentials missing.")
            self.supabase = None
        else:
            try:
                self.supabase: Client = create_client(url, key)
            except Exception as e:
                print(f"⚠️ [DB Init] Failed to initialize Supabase Client: {e}")
                self.supabase = None

    def save_live_news(self, data_list):
        """
        public.live_news 테이블 저장
        전략: 'Live' 상태 유지를 위해 해당 카테고리의 기존 데이터를 삭제하고 새로 넣습니다.
        """
        if not self.supabase or not data_list: return
        
        category = data_list[0].get('category')
        try:
            # 1. 해당 카테고리의 기존 라이브 뉴스 삭제 (Clean Slate)
            if category:
                self.supabase.table("live_news").delete().eq("category", category).execute()
            
            # 2. 새로운 데이터 입력
            self.supabase.table("live_news").insert(data_list).execute()
            print(f"  > ✅ [DB] Live News updated successfully ({len(data_list)} items).")
            
        except Exception as e:
            # 에러 발생 시 상세 내용 출력 (디버깅용)
            print(f"❌ [DB Error] Live News Update Failed: {e}")
            # 데이터 샘플 출력해보기
            if data_list:
                print(f"    Sample Data: {json.dumps(data_list[0], default=str)}")

    def save_rankings(self, data_list):
        """
        public.live_rankings 테이블 저장
        전략: 랭킹은 1~10위가 고정되므로, 기존 카테고리 랭킹을 지우고 새로 씁니다.
        """
        if not self.supabase or not data_list: return
        
        category = data_list[0].get('category')
        try:
            # 1. 해당 카테고리의 기존 랭킹 삭제
            if category:
                self.supabase.table("live_rankings").delete().eq("category", category).execute()
                
            # 2. 새로운 랭킹 입력
            self.supabase.table("live_rankings").insert(data_list).execute()
            print(f"  > ✅ [DB] Rankings updated successfully ({len(data_list)} items).")
            
        except Exception as e:
            print(f"❌ [DB Error] Rankings Update Failed: {e}")

    def save_to_archive(self, article_data):
        """
        public.search_archive 테이블 저장 (히스토리용 - 무조건 추가)
        """
        if not self.supabase: return
        try:
            self.supabase.table("search_archive").insert(article_data).execute()
        except Exception as e:
            print(f"❌ [DB Error] Archive Insert Failed: {e}")
