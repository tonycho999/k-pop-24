import gemini_api
import database
import naver_api
from datetime import datetime

PROMPT_VERSIONS = {
    "K-Pop": [
        "최근 24시간 내 언급량이 가장 압도적인 K-pop 가수(그룹)를 선정해 심층 기사 1개를 쓰고 Top 10 곡 순위를 알려줘.",
        "현재 차트 역주행이나 급상승으로 화제인 K-pop 가수를 선정해 심층 기사 1개를 쓰고 Top 10 곡 순위를 알려줘.",
        "비하인드 뉴스나 독점 인터뷰로 화제인 K-pop 가수를 선정해 심층 기사 1개를 쓰고 Top 10 곡 순위를 알려줘.",
        "글로벌 팬덤 및 SNS 반응이 폭발적인 K-pop 가수를 선정해 심층 기사 1개를 쓰고 Top 10 곡 순위를 알려줘.",
        "업계 내 뜨거운 논쟁이나 반전 이슈의 주인공인 K-pop 가수를 선정해 심층 기사 1개를 쓰고 Top 10 곡 순위를 알려줘.",
        "컴백 예고나 대형 프로젝트를 시작한 K-pop 가수를 선정해 심층 기사 1개를 쓰고 Top 10 곡 순위를 알려줘."
    ],
    "K-Drama": [
        "화제성 1위 드라마의 주연 배우를 선정해 심층 기사 1개를 쓰고 드라마 순위 1~10위를 알려줘.",
        "드라마 한 편으로 인생이 바뀐 라이징 배우를 선정해 심층 기사 1개를 쓰고 드라마 순위 1~10위를 알려줘.",
        "촬영 현장 비화나 캐스팅 소식으로 화제인 배우를 선정해 심층 기사 1개를 쓰고 드라마 순위 1~10위를 알려줘.",
        "글로벌 OTT 차트를 휩쓴 드라마의 배우를 선정해 심층 기사 1개를 쓰고 드라마 순위 1~10위를 알려줘.",
        "결말 논란이나 인터뷰로 화제인 배우를 선정해 심층 기사 1개를 쓰고 드라마 순위 1~10위를 알려줘.",
        "차기작이 기대되는 '믿보배' 배우를 선정해 심층 기사 1개를 쓰고 드라마 순위 1~10위를 알려줘."
    ],
    "K-Movie": [
        "박스오피스 1위 영화의 핵심 배우나 감독을 선정해 심층 기사 1개를 쓰고 영화 순위 1~10위를 알려줘.",
        "독립영화나 저예산 영화에서 발굴된 천재 영화인을 선정해 심층 기사 1개를 쓰고 영화 순위 1~10위를 알려줘.",
        "독특한 연출이나 제작 비화로 화제인 영화인을 선정해 심층 기사 1개를 쓰고 영화 순위 1~10위를 알려줘.",
        "해외 시상식 수상이나 해외 진출로 화제인 영화인을 선정해 심층 기사 1개를 쓰고 영화 순위 1~10위를 알려줘.",
        "영화계 이슈나 논쟁의 중심인 영화인을 선정해 심층 기사 1개를 쓰고 영화 순위 1~10위를 알려줘.",
        "대작 개봉을 앞두고 홍보 중인 핫한 영화인을 선정해 심층 기사 1개를 쓰고 영화 순위 1~10위를 알려줘."
    ],
    "K-Entertain": [
        "시청률 1위 예능의 메인 출연진을 선정해 심층 기사 1개를 쓰고 예능 순위 1~10위를 알려줘.",
        "유튜브나 OTT 예능에서 제2의 전성기를 맞은 예능인을 선정해 심층 기사 1개를 쓰고 예능 순위 1~10위를 알려줘.",
        "출연진 간의 케미로 화제인 예능인을 선정해 심층 기사 1개를 쓰고 예능 순위 1~10위를 알려줘.",
        "해외 팬덤이 강력한 글로벌 예능인을 선정해 심층 기사 1개를 쓰고 예능 순위 1~10위를 알려줘.",
        "태도 논란이나 섭외 이슈로 화제인 예능인을 선정해 심층 기사 1개를 쓰고 예능 순위 1~10위를 알려줘.",
        "새 시즌 복귀나 컴백으로 화제인 예능인을 선정해 심층 기사 1개를 쓰고 예능 순위 1~10위를 알려줘."
    ],
    "K-Culture": [
        "가장 핫한 전시나 팝업스토어를 기획한 문화인을 선정해 심층 기사 1개를 쓰고 문화 핫픽 1~10위를 알려줘.",
        "MZ세대 트렌드를 선도하는 예술가나 인물을 선정해 심층 기사 1개를 쓰고 문화 핫픽 1~10위를 알려줘.",
        "전통을 힙하게 재해석한 장인이나 인물을 선정해 심층 기사 1개를 쓰고 문화 핫픽 1~10위를 알려줘.",
        "K-푸드나 한국 문화를 세계에 알린 인물을 선정해 심층 기사 1개를 쓰고 문화 핫픽 1~10위를 알려줘.",
        "공익적 문화 활동이나 지역 살리기로 화제인 인물을 선정해 심층 기사 1개를 쓰고 문화 핫픽 1~10위를 알려줘.",
        "랜드마크 건립이나 대형 축제를 이끄는 인물을 선정해 심층 기사 1개를 쓰고 문화 핫픽 1~10위를 알려줘."
    ]
}

def run_category_process(category, run_count):
    print(f"\n🚀 [Autonomous Mode] {category} (Run #{run_count})")

    v_idx = run_count % 6
    task = PROMPT_VERSIONS[category][v_idx]

    # [절대 규칙] 한국어 지시 사항 강화
    final_prompt = f"""
    실시간 뉴스 검색을 사용하여 다음 과제를 수행해: {task}
    
    [출력 규칙 - 반드시 지킬 것]
    1. 반드시 아래 JSON 구조로만 응답해.
    2. JSON 외에 '알겠습니다' 같은 인사말이나 설명을 절대 하지 마.
    3. 코드 블록(```json)을 쓰지 말고 순수 텍스트로만 보내.
    4. 구글 검색 출처 번호(예: [1], [2])를 본문에 절대 포함하지 마.
    5. 기사 본문과 제목은 영어(English)로 작성해.
    
    {{
      "target_kr": "인물명(한국어)",
      "target_en": "Name(English)",
      "articles": [
        {{"headline": "English Title", "content": "English Content"}}
      ],
      "rankings": [
        {{"rank": 1, "title_en": "Title(En)", "title_kr": "제목(Kr)", "score": 95}}
      ]
    }}
    """

    data = gemini_api.ask_gemini_with_search(final_prompt)
    if not data or "articles" not in data:
        print(f"❌ {category} 데이터 추출 실패 (응답 포맷 오류)")
        return

    # 랭킹 저장
    database.save_rankings_to_db(data.get("rankings", []))

    # 이미지 수집
    target_kr = data.get("target_kr")
    final_image = naver_api.get_target_image(target_kr)

    # 기사 저장
    target_en = data.get("target_en")
    news_items = []
    for art in data.get("articles", []):
        news_items.append({
            "category": category,
            "keyword": target_en,
            "title": art.get("headline"),
            "summary": art.get("content"),
            "image_url": final_image,
            "score": 100,
            "created_at": datetime.now().isoformat(),
            "likes": 0
        })
    
    database.save_news_to_live(news_items)
    print(f"🎉 성공: {target_en} 관련 기사 발행 완료.")
