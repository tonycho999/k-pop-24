import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from groq import Groq

# 한글 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

# [환경변수 설정]
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# [Supabase 클라이언트 초기화]
supabase: Client = None
if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ Warning (config.py): Supabase 환경변수가 설정되지 않았습니다.")
else:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Warning: Supabase 클라이언트 초기화 실패: {e}")

# [Groq 클라이언트 초기화]
groq_client = None
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except:
        pass

# [1. 씨앗 키워드 설정 (Seed Keywords)]
# 네이버 뉴스에서 '원석'을 캐기 위한 광범위한 키워드
CATEGORY_SEEDS = {
    "k-pop": ["멜론 차트 순위",
        "빌보드 K-pop 차트",
        "인기가요 1위",
        "K-pop 신곡 반응",
        "아이돌 뮤직비디오 조회수"],
    "k-drama": ["드라마 시청률 순위",
        "넷플릭스 한국 드라마 순위",
        "티빙 드라마 인기",
        "화제성 드라마 순위",
        "방영 예정 드라마 기대작"],
    "k-movie": ["박스오피스 예매율",
        "넷플릭스 영화 순위",
        "한국 영화 관객수",
        "개봉 영화 평점"],
    "k-entertain": ["예능 시청률 순위",
        "OTT 예능 트렌드",
        "유튜브 인기 예능",
        "화제성 예능 프로그램"],
    "k-culture": ["서울 핫플레이스 웨이팅",
        "한국 유행 음식",
        "성수동 팝업스토어",
        "한국 패션 트렌드",
        "한국 여행 필수 코스"]
}

# [2. 설정 상수]
TOP_RANK_LIMIT = 30  # 카테고리당 30위까지 선정
