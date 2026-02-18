import feedparser
from groq import Groq

class NewsEngine:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        # 전문지 위주로 RSS URL 재구성
        self.rss_urls = [
            "https://news1.kr/rss/entertainment/",
            "https://www.joynews24.com/rss/entertainment.xml",
            "http://www.sportsseoul.com/rss/entertainment.xml",
            "https://www.yna.co.kr/rss/entertainment.xml" # 연합은 속보용으로 유지
        ]

    def fetch_all_rss_data(self):
        """전문지 RSS에서 데이터를 긁어모아 텍스트 뭉치 생성"""
        news_pool = []
        for url in self.rss_urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:20]: # 매체당 최신 20개
                    news_pool.append({
                        "title": entry.title,
                        "desc": entry.description,
                        "link": entry.link
                    })
            except Exception as e:
                print(f"📡 RSS Error ({url}): {e}")
        return news_pool

    def find_articles_for_targets(self, targets):
        """
        RSS 풀에서 인물 30인(targets) 중 기사가 있는 사람을 필터링합니다.
        targets: ['임영웅', '뉴진스', '에스파', ...]
        """
        news_pool = self.fetch_all_rss_data()
        matched_articles = {}

        for target in targets:
            content_for_target = ""
            for news in news_pool:
                if target in news['title'] or target in news['desc']:
                    content_for_target += f"{news['title']}\n{news['desc']}\n\n"
            
            if content_for_target:
                matched_articles[target] = content_for_target
        
        return matched_articles

    def generate_news(self, keyword, raw_context):
        """Groq AI를 통해 정제된 기사 한 건 생성"""
        prompt = f"""
        당신은 K-Enter 전문 에디터입니다. 아래 제공된 최신 뉴스 조각들을 분석하여 '{keyword}'에 대한 
        짧지만 강렬한 소식 한 편을 작성하세요.
        
        [지침]
        - 반드시 제공된 데이터에 기반할 것.
        - 제목: 독자의 호기심을 자극하는 한 줄.
        - 본문: 3개 문장 내외로 팩트 위주로 작성.
        - 데이터: {raw_context[:3000]}
        """
        try:
            chat = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192"
            )
            return chat.choices[0].message.content
        except:
            return None
