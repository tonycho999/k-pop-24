import os
import sys
import json
import urllib.request
import urllib.parse
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

# 1. 환경 설정
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
groq_api_key = os.environ.get("GROQ_API_KEY")
naver_client_id = os.environ.get("NAVER_CLIENT_ID")
naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET")

if not all([supabase_url, supabase_key, groq_api_key, naver_client_id, naver_client_secret]):
    print("❌ Error: .env 키 확인 필요 (Supabase, Groq, Naver API 키 모두 필요)")
    sys.exit(1)

supabase: Client = create_client(supabase_url, supabase_key)
groq_client = Groq(api_key=groq_api_key)
AI_MODEL = "llama-3.3-70b-versatile"

# 검색 키워드
SEARCH_KEYWORDS = ["K-POP 아이돌", "한국 인기 드라마", "한국 영화 화제", "한국 예능 레전드"]

def get_real_news_image(link):
    """
    뉴스 기사 링크에 접속해서 실제 보도 사진을 가져오는 강화된 함수
    """
    try:
        # 실제 브라우저처럼 보이게 헤더 강화
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://search.naver.com/'
        }
        
        # 기사 페이지 접속 (리다이렉트 허용 및 타임아웃 설정)
        response = requests.get(link, headers=headers, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1순위: og:image (대표 이미지 메타 태그)
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                img_url = og_image['content']
                # 네이버 기본 아이콘이나 로고는 제외
                if "static.naver.net" not in img_url and "default" not in img_url:
                    return img_url
            
            # 2순위: 네이버 뉴스 본문 내 첫 번째 이미지 (네이버 뉴스 전용 구조 탐색)
            # dic_area(본문), articleBodyContents(구버전 본문) 등
            selectors = ['#dic_area img', '#articleBodyContents img', '.article_kanvas img', '#img1']
            for selector in selectors:
                img = soup.select_one(selector)
                if img and img.get('src'):
                    return img['src']

    except Exception as e:
        print(f"⚠️ 이미지 추출 실패: {link[:30]}... -> {e}")
    
    return None

def get_naver_api_news(keyword):
    encText = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/news?query={encText}&display=15&sort=sim"
    
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", naver_client_id)
    request.add_header("X-Naver-Client-Secret", naver_client_secret)
    
    try:
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('items', [])
    except Exception as e:
        print(f"📡 API Error: {e}")
    return []

def ai_chief_editor(news_batch):
    news_text = ""
    for idx, item in enumerate(news_batch):
        clean_title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
        news_text += f"{idx+1}. {clean_title}\n"

    prompt = f"""
    Role: Chief Editor of 'K-ENTER 24'.
    Task: Analyze news and select Top 12.
    Output JSON strictly:
    {{
        "global_insight": "English Trend summary...",
        "articles": [
            {{
                "category": "K-POP", 
                "artist": "Subject Name",
                "title": "English Headline",
                "summary": "Short summary...",
                "score": 9,
                "reactions": {{"excitement": 80, "sadness": 0, "shock": 20}},
                "original_title_index": 1 
            }}
        ]
    }}
    Raw Titles:
    {news_text}
    """
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=AI_MODEL,
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        print(f"📝 AI Editor Error: {e}")
        return None

def run():
    print(f"=== {datetime.now()} K-Enter 24 실전 뉴스 수집 시작 ===")
    
    all_news = []
    for keyword in SEARCH_KEYWORDS:
        print(f"📡 키워드 검색 중: {keyword}")
        all_news.extend(get_naver_api_news(keyword))
    
    if not all_news:
        print("❌ 검색 결과가 없습니다.")
        return

    print(f"📝 AI 분석 및 이미지 {len(all_news)}건 추출 시도...")
    result = ai_chief_editor(all_news)
    if not result: return

    saved_count = 0
    for article in result.get('articles', []):
        idx = article.get('original_title_index', 1) - 1
        if idx < 0 or idx >= len(all_news): idx = 0
        original = all_news[idx]

        # 실제 기사 본문에서 이미지 추출 시도
        real_img = get_real_news_image(original['link'])
        
        # 이미지를 못 찾았을 경우에만 백업용 플레이스홀더 사용
        if not real_img:
            subject = article.get('artist', 'K-News')
            real_img = f"https://placehold.co/600x400/111/cyan?text={subject.replace(' ', '+')}"

        try:
            # 중복 체크 (제목 기준)
            if supabase.table("live_news").select("id").eq("title", article['title']).execute().data:
                continue
            
            data = {
                "category": article.get('category', 'General'),
                "artist": article.get('artist', 'Trend'),
                "title": article['title'],
                "summary": article['summary'],
                "score": article.get('score', 5),
                "link": original['link'],
                "source": "Naver News",
                "image_url": real_img,
                "reactions": article['reactions'],
                "is_published": True,
                "created_at": datetime.now().isoformat()
            }
            supabase.table("live_news").insert(data).execute()
            print(f"✅ 저장 성공: {article['title']}")
            saved_count += 1
        except Exception as e:
            print(f"💾 저장 실패: {e}")

    print(f"=== 완료: {saved_count}개의 진짜 뉴스가 업데이트되었습니다 ===")

if __name__ == "__main__":
    run()
