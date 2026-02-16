from news_api import NewsEngine
from naver_api import NaverManager
from database import DatabaseManager

def run_automation():
    db = DatabaseManager()
    engine = NewsEngine()
    naver = NaverManager()
    
    categories = ["k-pop", "k-drama", "k-movie", "k-entertain", "k-culture"]

    for cat in categories:
        # 1. 사이드바용 TOP 10 수집 (프로그램명 중심)
        # Perplexity에게 차트 정보를 묻고 바로 DB 저장
        # ... (생략)

        # 2. 본문용 인물 기사 수집 및 요약 (150인 중 일부 예시)
        raw_people_data = engine.fetch_trending_people(cat)
        # JSON 파싱 후 루프 실행
        for person in parsed_data:
            summary = engine.summarize_with_groq(person['news'], cat)
            img_url = naver.get_image(person['name'])
            
            db.save_live_news({
                "category": cat,
                "keyword": person['name'],
                "title": summary.split('\n')[0], # 첫 줄을 제목으로
                "summary": summary,
                "image_url": img_url
            })

if __name__ == "__main__":
    run_automation()
