import sqlite3
import datetime
import random
import json

class NewsEngine:
    def __init__(self, run_count=0, db_path="news_history.db"):
        self.run_count = run_count
        self.db_path = db_path
        self.cool_down_hours = 6  # 쿨타임 6시간
        self._init_db()

    def _init_db(self):
        """작성 기록을 저장할 SQLite DB 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS article_history (
                name TEXT PRIMARY KEY,
                category TEXT,
                last_written_at DATETIME
            )
        ''')
        conn.commit()
        conn.close()

    def is_using_primary_key(self):
        """API 키 상태 확인 (기존 로직 유지용)"""
        return True

    # ---------------------------------------------------------
    # [Step 1] 순위 데이터 가져오기 (30명 버퍼 수집)
    # ---------------------------------------------------------
    def get_top10_chart(self, category):
        # 실제 구현시: Perplexity/GPT를 통해 차트 정보 수집
        # 여기서는 빈 JSON 혹은 예시 반환
        return json.dumps({"top10": []})

    def get_top30_people(self, category):
        """
        카테고리별 상위 30명 인물 리스트를 반환
        (실제 환경에서는 LLM/Search API를 호출하여 최신 트렌드를 가져와야 합니다)
        """
        print(f"📡 [{category}] Fetching Top 30 Candidates...")
        
        # [Placeholder] 실제 API 연동이 필요한 부분입니다.
        # 예시 데이터를 생성해서 반환합니다.
        people_data = []
        for i in range(1, 31):
            people_data.append({
                "rank": i,
                "name_en": f"Person_{i}", # 실제 API에서는 실제 이름
                "name_kr": f"인물_{i}",
                "info": "Example info"
            })
        
        return json.dumps({"people": people_data})

    # ---------------------------------------------------------
    # [Step 2 & 5] 쿨타임 관리 (DB)
    # ---------------------------------------------------------
    def is_in_cooldown(self, name):
        """최근 작성 여부 확인"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT last_written_at FROM article_history WHERE name = ?', (name,))
            row = cursor.fetchone()
            conn.close()

            if row:
                last_time = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                time_diff = datetime.datetime.now() - last_time
                if time_diff.total_seconds() < (self.cool_down_hours * 3600):
                    print(f"    ⏳ [Cooldown] '{name}' (Last written: {int(time_diff.total_seconds()/60)}m ago)")
                    return True
            return False
        except Exception as e:
            print(f"    ⚠️ DB Check Error: {e}")
            return False

    def update_history(self, name, category):
        """기사 작성 성공 시 DB 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO article_history (name, category, last_written_at) 
                VALUES (?, ?, ?) 
                ON CONFLICT(name) DO UPDATE SET last_written_at = ?
            ''', (name, category, now, now))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"    ⚠️ DB Update Error: {e}")

    # ---------------------------------------------------------
    # [Step 3] 뉴스 유무 확인 및 기사 내용 수집
    # ---------------------------------------------------------
    def check_naver_news_exists(self, name_kr):
        """네이버 뉴스 검색 결과가 있는지 확인"""
        # [실제 적용] requests + BeautifulSoup으로 네이버 뉴스 검색 결과 수 확인 권장
        # 여기서는 시뮬레이션을 위해 랜덤 처리 (80% 확률로 뉴스 있음)
        has_news = random.choices([True, False], weights=[0.8, 0.2])[0]
        if not has_news:
            print(f"    🚫 [No News] '{name_kr}' - 네이버 기사 없음.")
        return has_news

    def fetch_article_details(self, name_kr, name_en, category, rank):
        """뉴스 내용 수집 (Naver)"""
        if not self.check_naver_news_exists(name_kr):
            return "NO NEWS FOUND"
        
        # [Placeholder] 실제로는 여기서 네이버 뉴스를 크롤링하거나 요약합니다.
        return f"Fact details regarding {name_en} from Naver News..."

    # ---------------------------------------------------------
    # [Step 4] 기사 작성 (Groq)
    # ---------------------------------------------------------
    def edit_with_groq(self, name, facts, category):
        """LLM을 이용한 기사 작성"""
        return f"""Headline: Top News about {name}
In-depth analysis of {name} in {category}.
{facts}
###SCORE: 85
"""
