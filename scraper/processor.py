import gemini_api
import database
import naver_api
from datetime import datetime

# 카테고리별 6단계 순환 질문 세트 (기사 개수 지침 수정)
PROMPT_VERSIONS = {
    "K-Pop": [
        "20년 차 베테랑 연예기자로서 지난 24시간 내 언급량이 가장 압도적인 K-pop 가수를 선정해. 해당 가수(그룹)에 대해 서로 다른 관점을 담은 심층 기사 1개를 작성하고, Top 10 Music Chart를 영어 JSON으로 줘.",
        "지난 24시간 내 차트 역주행이나 급상승으로 화제인 K-pop 가수를 선정해. 그 가수의 성공 비결과 화제성을 다룬 심층 기사 1개를 작성하고, Top 10 Music Chart를 영어 JSON으로 줘.",
        "최근 공개된 비하인드나 독점 인터뷰로 화제가 된 K-pop 가수를 선정해. 해당 가수의 숨겨진 면모와 비화를 담은 심층 기사 1개를 작성하고, Top 10 Music Chart를 영어 JSON으로 줘.",
        "빌보드나 해외 SNS에서 가장 핫한 K-pop 가수를 선정해. 그 가수의 글로벌 영향력을 다각도로 분석한 심층 기사 1개를 작성하고, Top 10 Music Chart를 영어 JSON으로 줘.",
        "현재 업계 내 뜨거운 논쟁이나 큰 반전의 주인공이 된 K-pop 가수를 선정해. 해당 가수를 둘러싼 이슈를 베테랑 기자의 시각으로 분석한 심층 기사 1개를 작성하고, Top 10 Music Chart를 영어 JSON으로 줘.",
        "컴백 직전이거나 대형 프로젝트를 시작한 K-pop 가수를 선정해. 해당 가수의 향후 행보와 기대감을 담은 심층 기사 1개를 작성하고, Top 10 Music Chart를 영어 JSON으로 줘."
    ],
    "K-Drama": [
        "시청률과 화제성이 가장 높은 드라마의 배우를 선정해. 해당 배우의 연기력과 캐릭터 분석을 담은 심층 기사 1개를 작성하고, Drama Ranking를 영어 JSON으로 줘.",
        "드라마 한 편으로 인생이 바뀐 라이징 배우를 선정해. 그 배우의 성장 과정과 매력을 다룬 심층 기사 1개를 작성하고, Drama Ranking를 영어 JSON으로 줘.",
        "촬영 현장 미담이나 캐스팅 비화로 화제인 배우를 선정해. 해당 배우의 인간적인 면모를 다룬 심층 기사 1개를 작성하고, Drama Ranking를 영어 JSON으로 줘.",
        "넷플릭스 등 글로벌 차트를 휩춘 드라마의 배우를 선정해. 글로벌 스타로 거듭난 해당 배우에 대한 심층 기사 1개를 작성하고, Drama Ranking를 영어 JSON으로 줘.",
        "캐스팅 논란이나 결말 관련 인터뷰로 화제인 배우를 선정해. 이슈의 중심에 선 해당 배우에 대한 심층 기사 1개를 작성하고, Drama Ranking를 영어 JSON으로 줘.",
        "차기작 소식이나 차세대 믿고 보는 배우로 꼽힌 배우를 선정해. 배우의 필모그래피와 미래를 다룬 심층 기사 1개를 작성하고, Drama Ranking를 영어 JSON으로 줘."
    ],
    "K-Movie": [
        "박스오피스 1위 영화의 핵심 배우나 감독을 선정해. 영화의 흥행 요소와 인물의 활약을 담은 심층 기사 1개를 작성하고, 한국 Box Office Top 10를 영어 JSON으로 줘.",
        "독립영화나 저예산 영화에서 발굴된 천재적 영화인을 선정해. 그 인물의 예술 세계를 다룬 심층 기사 1개를 작성하고, 한국 Box Office Top 10를 영어 JSON으로 줘.",
        "제작 과정의 어려움을 극복하거나 독특한 연출로 화제인 영화인을 선정해. 제작 비하인드를 담은 심층 기사 1개를 작성하고, 한국 Box Office Top 10를 영어 JSON으로 줘.",
        "해외 영화제 수상이나 해외 진출로 국위선양 중인 영화인을 선정해. 세계가 주목하는 이유를 담은 심층 기사 1개를 작성하고, 한국 Box Office Top 10를 영어 JSON으로 줘.",
        "최근 영화계 이슈나 논쟁의 중심이 된 영화인을 선정해. 베테랑 기자의 날카로운 비평을 담은 심층 기사 1개를 작성하고, 한국 Box Office Top 10를 영어 JSON으로 줘.",
        "대작 개봉을 앞두고 홍보 활동 중인 가장 핫한 영화인을 선정해. 신작에 대한 기대감을 담은 심층 기사 1개를 작성하고, 한국 Box Office Top 10를 영어 JSON으로 줘."
    ],
    "K-Entertain": [
        "현재 시청률 1위 예능을 이끄는 메인 예능인/MC를 선정해. 그의 리더십과 유머 감각을 다룬 심층 기사 1개를 작성하고, Variety Show Trends top 10를 영어 JSON으로 줘.",
        "유튜브나 OTT 예능에서 제2의 전성기를 맞은 예능인을 선정해. 달라진 위상과 트렌드를 분석한 심층 기사 1개를 작성하고, Variety Show Trends top 10를 영어 JSON으로 줘.",
        "출연진 간의 환상적인 케미로 화제인 예능인을 선정해. 관계성에서 오는 재미를 분석한 심층 기사 1개를 작성하고, Variety Show Trends top 10를 영어 JSON으로 줘.",
        "해외 버전 예능이나 글로벌 팬덤이 강력한 예능인을 선정해. 세계를 웃기는 그의 매력을 다룬 심층 기사 1개를 작성하고, Variety Show Trends top 10를 영어 JSON으로 줘.",
        "태도 논란이나 섭외 이슈 등 뜨거운 감자가 된 예능인을 선정해. 사건의 본질을 짚어주는 심층 기사 1개를 작성하고, Variety Show Trends top 10를 영어 JSON으로 줘.",
        "오랜만에 예능으로 복귀하거나 새 시즌을 시작한 예능인을 선정해. 그의 활약 전망을 담은 심층 기사 1개를 작성하고, Variety Show Trends top 10를 영어 JSON으로 줘."
    ],
    "K-Culture": [
        "현재 가장 핫한 전시나 팝업스토어를 기획한 문화인/기획자를 선정해. 기획 의도와 인기를 다룬 심층 기사 1개를 작성하고, K-Culture Hot Picks top 10를 영어 JSON으로 줘.",
        "MZ세대가 열광하는 새로운 문화를 선도하는 인플루언서/예술가를 선정해. 트렌드 분석을 담은 심층 기사 1개를 작성하고, K-Culture Hot Picks top 10를 영어 JSON으로 줘.",
        "전통을 힙하게 재해석해 화제가 된 장인/예술가를 선정해. 그의 철학과 작품 세계를 담은 심층 기사 1개를 작성하고, K-Culture Hot Picks top 10를 영어 JSON으로 줘.",
        "외국인들에게 K-푸드나 한국 문화를 알린 일등공신 인물을 선정해. 그의 영향력을 다룬 심층 기사 1개를 작성하고, K-Culture Hot Picks top 10를 영어 JSON으로 줘.",
        "지역 소멸 방지나 공익적 문화 활동으로 화제인 인물을 선정해. 변화하는 한국 문화를 기록한 심층 기사 1개를 작성하고, K-Culture Hot Picks top 10를 영어 JSON으로 줘.",
        "새로운 랜드마크 건립이나 초대형 축제를 총괄한 인물을 선정해. 미래의 한국 문화를 전망한 심층 기사 1개를 작성하고, K-Culture Hot Picks top 10를 영어 JSON으로 줘."
    ]
}

def run_category_process(category, run_count):
    print(f"\n🚀 [Autonomous Mode] {category} (Run #{run_count})")

    v_idx = run_count % 6
    base_prompt = PROMPT_VERSIONS[category][v_idx]

    # 프롬프트 규칙 강화: 반드시 1개만 작성하도록 명시
    final_prompt = base_prompt + """
    
    [STRICT JSON RULES]
    1. Write exactly 1 distinct articles in English.
    2. Return ONLY the JSON object. No other text.
    {
      "target_kr": "인물명",
      "target_en": "Name",
      "articles": [
        {"headline": "Title", "content": "Body"}
      ],
      "rankings": [
        {"rank": 1, "title_en": "English", "title_kr": "한국어", "score": 95}
      ]
    }
    """

    data = gemini_api.ask_gemini_with_search(final_prompt)
    if not data or "articles" not in data:
        print(f"❌ {category} 데이터 추출 실패 (AI 응답 오류)")
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
    print(f"🎉 성공: {target_en} 관련 기사 1개 발행 완료.")
