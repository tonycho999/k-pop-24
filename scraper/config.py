import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from groq import Groq

# 한글 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

# [수정 1] 환경변수 이름 통일 (GitHub Actions YAML과 맞춤)
# YAML에서 설정한 이름(SUPABASE_URL)을 우선적으로 찾도록 변경
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# [수정 2] 강제 종료(exit) 제거 -> 경고만 출력하고 넘어감
supabase: Client = None
if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ Warning (config.py): Supabase 환경변수가 설정되지 않았습니다.")
else:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Warning: Supabase 클라이언트 초기화 실패: {e}")

# Groq 클라이언트 초기화 (안전하게)
groq_client = None
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except:
        pass

# 카테고리 설정
CATEGORY_MAP = {
    "k-pop": ["컴백", "빌보드", "아이돌", "뮤직", "비디오", "챌린지", "포토카드", "월드투어", "가수"],
    "k-drama": ["드라마", "시청률", "넷플릭스", "OTT", "배우", "캐스팅", "대본리딩", "종영"],
    "k-movie": ["영화", "개봉", "박스오피스", "시사회", "영화제", "관객", "무대인사"],
    "k-entertain": ["예능", "유튜브", "개그맨", "코미디언", "방송", "개그우먼"],
    "k-culture": ["푸드", "뷰티", "웹툰", "팝업스토어", "패션", "음식", "해외반응"]
}
