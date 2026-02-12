import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from groq import Groq

# 한글 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

# Supabase 연결 (관리자 키 우선 사용)
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("🚨 오류: .env 파일에 Supabase URL 또는 Key가 없습니다.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# 카테고리 설정
CATEGORY_MAP = {
    "k-pop": ["컴백", "빌보드", "아이돌", "뮤직", "비디오", "챌린지", "포토카드", "월드투어", "가수"],
    "k-drama": ["드라마", "시청률", "넷플릭스", "OTT", "배우", "캐스팅", "대본리딩", "종영"],
    "k-movie": ["영화", "개봉", "박스오피스", "시사회", "영화제", "관객", "무대인사"],
    "k-entertain": ["예능", "유튜브", "개그맨", "코미디언", "방송", "개그우먼"],
    "k-culture": ["푸드", "뷰티", "웹툰", "팝업스토어", "패션", "음식", "해외반응"]
}
