import os
from datetime import datetime, timedelta
from supabase import create_client, Client

class Database:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            print("❌ Supabase URL or Key is missing!")
            self.client = None
        else:
            self.client: Client = create_client(url, key)
            print("✅ Supabase connection established.")

    # ==========================================
    # 1. Groq API 순번 관리 (system_status 테이블)
    # ==========================================
    def get_groq_index(self) -> int:
        """system_status 테이블에서 run_count 값을 가져와 몇 번째 API를 쓸지 결정"""
        if not self.client: return 0
        try:
            # id=1 인 row의 run_count 값을 가져옴
            res = self.client.table("system_status").select("run_count").eq("id", 1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]["run_count"]
            else:
                # 데이터가 아예 없으면 기본값 0 세팅 후 생성
                self.client.table("system_status").insert({"id": 1, "run_count": 0}).execute()
                return 0
        except Exception as e:
            print(f"⚠️ Error reading system_status: {e}")
            return 0

    def update_groq_index(self, new_index: int):
        """Groq API가 에러 났을 때 다음 번호로 업데이트"""
        if not self.client: return
        try:
            self.client.table("system_status").update({"run_count": new_index}).eq("id", 1).execute()
            print(f"🔄 Groq API index updated to {new_index} in DB.")
        except Exception as e:
            print(f"⚠️ Error updating system_status: {e}")

    # ==========================================
    # 2. 오래된 기사 삭제 (search_archive 테이블)
    # ==========================================
    def cleanup_old_archives(self):
        """1주일(7일)이 지난 기사를 search_archive에서 삭제"""
        if not self.client: return
        try:
            one_week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            res = self.client.table("search_archive").delete().lt("created_at", one_week_ago).execute()
            print(f"🧹 Cleaned up old articles from search_archive (Older than 7 days).")
        except Exception as e:
            print(f"⚠️ Error cleaning up search_archive: {e}")

    # ==========================================
    # 3. 새로운 기사 저장 (live_news & search_archive)
    # ==========================================
    def save_news_results(self, category: str, results: list):
        if not self.client or not results: return
        
        live_news_data = []
        archive_data = []
        now = datetime.utcnow().isoformat()

        for res in results:
            # 공통 매핑 데이터 (스크린샷 컬럼명 기준)
            base_row = {
                "category": category,
                "keyword": res.get("name", ""),
                "title": res.get("title", ""),
                "summary": res.get("summary", ""),
                "link": res.get("link", ""),
                "image_url": "", # 네이버 본문 긁기라 이미지는 공란 처리
                "score": res.get("rank", 0),
                "likes": 0,
                "created_at": now
            }
            
            live_news_data.append(base_row)
            
            # search_archive 테이블 전용 추가 컬럼
            archive_row = base_row.copy()
            archive_row["query"] = res.get("name", "")
            archive_row["raw_result"] = str(res)
            archive_data.append(archive_row)

        try:
            # 1. live_news는 최신성을 위해 해당 카테고리 기존 데이터 싹 지우고 새로 덮어쓰기
            self.client.table("live_news").delete().eq("category", category).execute()
            self.client.table("live_news").insert(live_news_data).execute()
            
            # 2. search_archive는 아카이브(누적)이므로 그냥 계속 Insert
            self.client.table("search_archive").insert(archive_data).execute()
            print(f"✅ Saved {len(results)} items to DB for '{category}'.")
        except Exception as e:
            print(f"❌ DB Save Error: {e}")
