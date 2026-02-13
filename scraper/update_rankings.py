import os
from supabase import create_client, Client
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# [수정] exit() 대신 함수 내부에서 처리하도록 구조 변경
# (함수가 실행될 때 체크하고 안전하게 리턴함)

# AI가 분석한 트렌드 데이터 (이 부분은 유지보수를 위해 길게 두었습니다)
RANKING_DATA = [
    # K-Pop
    {"category": "K-Pop", "rank": 1, "title": "NewJeans 'How Sweet'", "sub_title": "Melon Top 100 #1", "link_url": "https://www.youtube.com/watch?v=Q3K0TOvTOno", "image_url": "https://i.ytimg.com/vi/Q3K0TOvTOno/maxresdefault.jpg"},
    {"category": "K-Pop", "rank": 2, "title": "aespa 'Supernova'", "sub_title": "Trending Worldwide", "link_url": "#", "image_url": "https://upload.wikimedia.org/wikipedia/en/3/36/Aespa_-_Supernova.png"},
    {"category": "K-Pop", "rank": 3, "title": "Zico (feat. Jennie)", "sub_title": "SPOT!", "link_url": "#", "image_url": ""},
    {"category": "K-Pop", "rank": 4, "title": "IVE 'HEYA'", "sub_title": "", "link_url": "#", "image_url": ""},
    {"category": "K-Pop", "rank": 5, "title": "ILLIT 'Magnetic'", "sub_title": "Long-run Hit", "link_url": "#", "image_url": ""},

    # K-Drama
    {"category": "K-Drama", "rank": 1, "title": "Queen of Tears", "sub_title": "Netflix Global #1", "link_url": "https://www.netflix.com", "image_url": "https://upload.wikimedia.org/wikipedia/en/e/e0/Queen_of_Tears_poster.jpg"},
    {"category": "K-Drama", "rank": 2, "title": "Lovely Runner", "sub_title": "tvN & Viki", "link_url": "#", "image_url": ""},
    {"category": "K-Drama", "rank": 3, "title": "The Atypical Family", "sub_title": "Rising Star", "link_url": "#", "image_url": ""},
    {"category": "K-Drama", "rank": 4, "title": "Parasyte: The Grey", "sub_title": "Netflix Series", "link_url": "#", "image_url": ""},
    {"category": "K-Drama", "rank": 5, "title": "Chief Detective 1958", "sub_title": "Disney+", "link_url": "#", "image_url": ""},

    # K-Movie
    {"category": "K-Movie", "rank": 1, "title": "The Roundup: Punishment", "sub_title": "10M Viewers", "link_url": "#", "image_url": ""},
    {"category": "K-Movie", "rank": 2, "title": "Exhuma", "sub_title": "Occult Mystery", "link_url": "#", "image_url": ""},
    {"category": "K-Movie", "rank": 3, "title": "Following", "sub_title": "New Release", "link_url": "#", "image_url": ""},
    {"category": "K-Movie", "rank": 4, "title": "Wonderland", "sub_title": "Coming Soon", "link_url": "#", "image_url": ""},
    {"category": "K-Movie", "rank": 5, "title": "Smugglers", "sub_title": "VOD Hot", "link_url": "#", "image_url": ""},

    # K-Entertain
    {"category": "K-Entertain", "rank": 1, "title": "Running Man", "sub_title": "SBS Sunday", "link_url": "#", "image_url": ""},
    {"category": "K-Entertain", "rank": 2, "title": "I Live Alone", "sub_title": "MBC Friday", "link_url": "#", "image_url": ""},
    {"category": "K-Entertain", "rank": 3, "title": "Knowing Bros", "sub_title": "JTBC", "link_url": "#", "image_url": ""},
    {"category": "K-Entertain", "rank": 4, "title": "You Quiz on the Block", "sub_title": "tvN Talk Show", "link_url": "#", "image_url": ""},
    {"category": "K-Entertain", "rank": 5, "title": "Eun-chae's Star Diary", "sub_title": "YouTube Hot", "link_url": "#", "image_url": ""},

    # K-Culture
    {"category": "K-Culture", "rank": 1, "title": "Seongsu-dong Cafe Street", "sub_title": "Seoul's Brooklyn", "link_url": "#", "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR_xxx"},
    {"category": "K-Culture", "rank": 2, "title": "Olive Young Myeongdong", "sub_title": "K-Beauty Mecca", "link_url": "#", "image_url": ""},
    {"category": "K-Culture", "rank": 3, "title": "The Hyundai Seoul", "sub_title": "Yeouido Hotspot", "link_url": "#", "image_url": ""},
    {"category": "K-Culture", "rank": 4, "title": "London Bagel Museum", "sub_title": "Must-visit Bakery", "link_url": "#", "image_url": ""},
    {"category": "K-Culture", "rank": 5, "title": "Gentle Monster Haus", "sub_title": "Dosan Park", "link_url": "#", "image_url": ""}
]

def update_rankings():
    # [안전 장치] 환경변수가 없으면 에러 내지 말고 그냥 함수 종료 (뉴스 수집은 계속되게)
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Warning: .env 파일을 찾을 수 없어 순위 업데이트를 건너뜁니다.")
        return

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        print("📊 Updating Trend Rankings...")
        
        # 1. 기존 데이터 안전하게 삭제 (전체 삭제 후 재입력 방식)
        try:
            supabase.table("trending_rankings").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception as e:
            print(f"Clean up warning: {e}")

        # 2. 새 데이터 삽입
        for item in RANKING_DATA:
            supabase.table("trending_rankings").insert(item).execute()
            print(f"   + Inserted: {item['category']} - {item['title']}")
        
        print("✅ Ranking Update Complete!")

    except Exception as e:
        print(f"❌ Ranking Update Error: {e}")

if __name__ == "__main__":
    update_rankings()
