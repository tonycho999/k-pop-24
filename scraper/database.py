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
                "image_url": res.get("image_url", ""), 
                "score": res.get("score", 50),
                "likes": 0,
                "created_at": now
            })

        try:
            # 1. 메인 뉴스 테이블(live_news)에 추가
            self.client.table("live_news").insert(live_news_data).execute()
            
            # 2. search_archive (기록보관소) 에도 똑같이 복사해서 저장
            self.client.table("search_archive").insert(live_news_data).execute()
            
            print(f"✅ Saved {len(results)} new articles to '{category}' (live_news & search_archive).")
            
            # 3. live_news는 최신 50개 제한 유지
            self._enforce_max_50_limit(category)
            
            # 💡 4. [추가 완료] search_archive는 7일이 지난 데이터 자동 삭제
            self._cleanup_7days_archive()
            
        except Exception as e:
            print(f"❌ DB Save Error: {e}")

    def _enforce_max_50_limit(self, category: str):
        """live_news 테이블: 카테고리당 최신 기사 50개만 남기고 삭제"""
        try:
            res = self.client.table("live_news").select("id").eq("category", category).order("created_at", desc=True).execute()
            if res.data and len(res.data) > 50:
                ids_to_delete = [item["id"] for item in res.data[50:]]
                self.client.table("live_news").delete().in_("id", ids_to_delete).execute()
                print(f"🧹 Cleaned up {len(ids_to_delete)} old articles. Maintained exactly 50 for '{category}'.")
        except Exception as e:
            print(f"⚠️ Error enforcing max 50 limit: {e}")

    # 💡 [새로 추가된 함수] search_archive 일주일(7일) 경과 데이터 삭제
    def _cleanup_7days_archive(self):
        """search_archive 테이블: 현재 시간 기준 7일 전 데이터 삭제"""
        try:
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            
            # created_at이 7일 전 시간보다 과거(lt)인 데이터 일괄 삭제
            self.client.table("search_archive").delete().lt("created_at", seven_days_ago).execute()
        except Exception as e:
            print(f"⚠️ Error cleaning up 7-day old search_archive: {e}")

    def save_chart_results(self, category: str, results: list):
        if not self.client or not results: return
        
        try:
            self.client.table("live_rankings").delete().eq("category", category).execute()
        except Exception:
            pass 

        chart_data = []
        now = datetime.utcnow().isoformat()
        
        for item in results:
            chart_data.append({
                "category": category,
                "rank": item.get("rank"),
                "title": item.get("title", ""),
                "meta_info": item.get("info", ""), 
                "updated_at": now
            })

        try:
            self.client.table("live_rankings").insert(chart_data).execute()
        except Exception as e:
            print(f"❌ Chart DB Save Error: {e}")
