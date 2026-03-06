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

    def get_groq_index(self) -> int:
        if not self.client: return 0
        try:
            res = self.client.table("system_status").select("run_count").eq("id", 1).execute()
            if res.data and len(res.data) > 0: return res.data[0]["run_count"]
            self.client.table("system_status").insert({"id": 1, "run_count": 0}).execute()
            return 0
        except: return 0

    def update_groq_index(self, new_index: int):
        if not self.client: return
        try: self.client.table("system_status").update({"run_count": new_index}).eq("id", 1).execute()
        except: pass

    # ==========================================
    # [핵심] 현재 DB에 살아있는 인물 명단 (중복 방지)
    # ==========================================
    def get_active_names(self, category: str) -> list:
        if not self.client: return []
        try:
            res = self.client.table("live_news").select("keyword").eq("category", category).execute()
            if res.data:
                return [row["keyword"] for row in res.data]
            return []
        except Exception as e:
            print(f"⚠️ Error fetching active names: {e}")
            return []

    def save_news_results(self, category: str, results: list):
        if not self.client or not results: return
        
        live_news_data = []
        now = datetime.utcnow().isoformat()

        for res in results:
            live_news_data.append({
                "category": category,
                "keyword": res.get("name", ""),
                "title": res.get("title", ""),
                "summary": res.get("summary", ""),
                "link": res.get("link", ""),
                # 💡 [치명적 버그 수정] 빈칸이었던 image_url을 드디어 제대로 받아서 넣습니다!
                "image_url": res.get("image_url", ""), 
                "score": res.get("score", 50), # AI가 부여한 화제성 평점 (기본값 50)
                "likes": 0,
                "created_at": now
            })

        try:
            # 새로운 10개 기사 무조건 추가
            self.client.table("live_news").insert(live_news_data).execute()
            print(f"✅ Saved {len(results)} new articles to '{category}'.")
            
            # [핵심] 50개 초과 시 '가장 오래된' 기사 삭제 (시간순 정리)
            self._enforce_max_50_limit(category)
        except Exception as e:
            print(f"❌ DB Save Error: {e}")

    def _enforce_max_50_limit(self, category: str):
        """카테고리당 최신 기사 50개만 남기고, 오래된 것은 삭제"""
        try:
            # 시간 내림차순(최신순)으로 정렬하여 데이터 조회
            res = self.client.table("live_news").select("id").eq("category", category).order("created_at", desc=True).execute()
            if res.data and len(res.data) > 50:
                # 50번째 이후의 오래된 기사들의 ID 추출
                ids_to_delete = [item["id"] for item in res.data[50:]]
                # 해당 ID들 일괄 삭제
                self.client.table("live_news").delete().in_("id", ids_to_delete).execute()
                print(f"🧹 Cleaned up {len(ids_to_delete)} old articles. Maintained exactly 50 for '{category}'.")
        except Exception as e:
            print(f"⚠️ Error enforcing max 50 limit: {e}")

    # 💡 [새로 추가된 함수] 차트 데이터를 DB에 저장 (오래된 차트는 지우고 새 차트로 덮어쓰기)
    def save_chart_results(self, category: str, results: list):
        if not self.client or not results: return
        
        # 1. 차트는 '최신 10개'만 유지하므로 기존 해당 카테고리의 차트를 지웁니다.
        try:
            self.client.table("live_rankings").delete().eq("category", category).execute()
        except Exception:
            pass # 기존 데이터가 없어도 무시

        # 2. 새로운 차트 10개 삽입
        chart_data = []
        now = datetime.utcnow().isoformat()
        
        for item in results:
            chart_data.append({
                "category": category,
                "rank": item.get("rank"),
                "title": item.get("title", ""),
                "info": item.get("info", ""),
                "updated_at": now
            })

        try:
            self.client.table("live_rankings").insert(chart_data).execute()
        except Exception as e:
            print(f"❌ Chart DB Save Error: {e}")
