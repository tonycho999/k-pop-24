import os
import datetime
from supabase import create_client

class DatabaseManager:
    def __init__(self):
        # 환경 변수에서 Supabase 접속 정보 로드
        self.supa_url = os.environ.get("SUPABASE_URL")
        self.supa_key = os.environ.get("SUPABASE_KEY")
        
        # 클라이언트 연결
        if self.supa_url and self.supa_key:
            self.supabase = create_client(self.supa_url, self.supa_key)
        else:
            self.supabase = None
            print("⚠️ Supabase credentials not found.")

    def save_rankings(self, data):
        """
        [Phase 1] Top 10 차트 저장
        - Upsert 방식을 사용하여 기존의 (Category, Rank) 데이터를 최신 정보로 덮어씁니다.
        """
        if not self.supabase or not data:
            return

        try:
            # Upsert: Primary Key(보통 category + rank 조합)가 같으면 업데이트, 없으면 생성
            self.supabase.table('live_rankings').upsert(data).execute()
            print(f"   > [DB] Top 10 Rankings Saved/Updated ({len(data)} items).")
        except Exception as e:
            print(f"   > ⚠️ Ranking Save Error: {e}")

    def save_live_news(self, news_list):
        """
        [Phase 2] 라이브 뉴스 저장 및 자동 청소
        - 새로운 뉴스를 저장합니다.
        - 카테고리별로 최신 50개만 남기고, 나머지는 자동으로 삭제하여 용량을 관리합니다.
        """
        if not self.supabase or not news_list:
            return

        try:
            # 1. 새로운 뉴스 저장 (Upsert)
            self.supabase.table('live_news').upsert(news_list).execute()
            print(f"   > [DB] Live News Saved: {len(news_list)} items.")

            # 2. 자동 청소 (Cleanup): 카테고리별 50개 제한
            # 방금 업데이트된 카테고리 목록 추출 (중복 제거)
            categories = set([item['category'] for item in news_list])

            for cat in categories:
                # 해당 카테고리의 모든 기사 ID를 최신순(내림차순)으로 가져옴
                res = self.supabase.table('live_news') \
                    .select('id') \
                    .eq('category', cat) \
                    .order('created_at', desc=True) \
                    .execute()

                all_articles = res.data if res.data else []

                # 50개가 넘으면, 51번째부터 끝까지(오래된 것들) 삭제 대상
                if len(all_articles) > 50:
                    ids_to_remove = [item['id'] for item in all_articles[50:]]
                    
                    if ids_to_remove:
                        self.supabase.table('live_news') \
                            .delete() \
                            .in_('id', ids_to_remove) \
                            .execute()
                        print(f"   > 🧹 [Cleanup] Removed {len(ids_to_remove)} old articles from '{cat}' (Max 50).")

        except Exception as e:
            print(f"   > ⚠️ Live News Save Error: {e}")

    def save_to_archive(self, article_data):
        """
        [Phase 3] 아카이브 저장 및 데이터 수명 관리 (Retention Policy)
        - 순위 변동 추적을 위해 모든 기사 내역을 저장합니다.
        - 단, DB 용량 관리를 위해 7일이 지난 데이터는 자동으로 삭제합니다.
        """
        if not self.supabase or not article_data:
            return

        try:
            # 1. 아카이브에 기록 저장
            # (단일 딕셔너리가 들어오면 리스트로 감싸지 않아도 insert는 동작하지만, 안전하게 처리)
            self.supabase.table('search_archive').insert(article_data).execute()
            
            # 2. 데이터 수명 관리 (7일 지난 데이터 삭제)
            # 현재 시간에서 7일을 뺀 시각 계산
            seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            limit_date_str = seven_days_ago.strftime("%Y-%m-%d %H:%M:%S")

            # created_at이 7일 전보다 오래된 데이터 삭제 요청
            # lt = less than (보다 작음 -> 더 오래됨)
            self.supabase.table('search_archive') \
                .delete() \
                .lt('created_at', limit_date_str) \
                .execute()
                
            # print("   > 🧹 [Archive] Auto-cleaned data older than 7 days.") # 로그가 너무 많으면 주석 처리

        except Exception as e:
            print(f"   > ⚠️ Archive Save Error: {e}")
