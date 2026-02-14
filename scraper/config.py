# scraper/config.py

# 실행 순서
CATEGORY_ORDER = ["K-Pop", "K-Drama", "K-Movie", "K-Entertain", "K-Culture"]

# [수정됨] 카테고리별 검색어 리스트 (각 3개씩)
SEARCH_QUERIES = {
    "K-Pop": [
        "음원 순위",    # 성적/차트 위주
        "아이돌",  # 신곡/컴백 위주
        "K팝 콘서트"   # 공연/행사 위주
    ],
    "K-Drama": [
        "드라마 시청률",       # 인기/성적 위주
        "넷플릭스 한국 드라마", # OTT 위주
        "드라마 캐스팅"      # 제작/캐스팅 위주
    ],
    "K-Movie": [
        "박스오피스",      # 흥행 성적 위주
        "영화 개봉",       # 개봉작 위주
        "영화 시사회"  
    ],
    "K-Entertain": [
        "예능 시청률",             # 인기 위주
        "예능 MC",  # 인기 프로그램 위주
        "OTT 예능 신작"          # 새로운 플랫폼 위주
    ],
    "K-Culture": [
        "서맛집 추천",   # 음식 (K-Food)
        "추천 여행지",   # 여행 (K-Travel)
        "축제 행사"     # 문화/행사 (K-Tradition)
    ]
}

# DB 유지 개수
MAX_ITEMS_PER_CATEGORY = 30
