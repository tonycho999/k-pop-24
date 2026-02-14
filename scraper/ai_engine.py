import os
import sys
import json
import re
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from groq import Groq

# 한글 깨짐 방지
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

# =========================================================
# [1. 환경변수 및 클라이언트 설정]
# =========================================================
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Supabase 초기화 실패: {e}")

# =========================================================
# [2. 수집 및 분류 설정 상수]
# =========================================================
# 네이버 API 수집 개수를 최대치(100)로 설정하여 24시간 내 뉴스를 최대한 확보합니다.
NAVER_DISPLAY_COUNT = 100
TOP_RANK_LIMIT = 30  # 카테고리당 분석 대상 순위

CATEGORY_SEEDS = {
    "k-pop": ["멜론 차트 순위", "빌보드 K-pop 차트", "인기가요 1위", "아이돌 신곡 반응"],
    "k-drama": ["드라마 시청률 순위", "넷플릭스 한국 드라마 순위", "티빙 인기 드라마", "방영 예정 드라마"],
    "k-movie": ["박스오피스 예매율", "한국 영화 관객수", "개봉 영화 평점"],
    "k-entertain": ["예능 시청률 순위", "OTT 예능 트렌드", "유튜브 인기 예능", "미스트롯 미스터트롯"], # 예능 시드 보강
    "k-culture": ["서울 핫플레이스", "한국 유행 음식", "성수동 팝업스토어", "K-패션 트렌드"]
}

# =========================================================
# [3. AI 모델 로직 (Groq)]
# =========================================================
def get_groq_text_models():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return []
    try:
        client = Groq(api_key=api_key)
        all_models = client.models.list()
        valid_models = [m.id for m in all_models.data if not any(x in m.id.lower() for x in ['vision', 'whisper', 'audio', 'guard', 'safe'])]
        valid_models.sort(key=lambda x: '70b' in x, reverse=True) 
        return valid_models
    except: return []

def clean_ai_response(text):
    if not text: return ""
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        for part in parts:
            if "{" in part or "[" in part:
                cleaned = part.replace("json", "").strip()
                break
    return cleaned

def ask_ai_master(system_prompt, user_input):
    groq_key = os.getenv("GROQ_API_KEY")
    models = get_groq_text_models()
    if not groq_key or not models: return ""
    
    client = Groq(api_key=groq_key)
    for model_id in models:
        try:
            completion = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
                temperature=0.2 # 분류 정확도를 위해 온도를 낮춤
            )
            res = completion.choices[0].message.content.strip()
            if res: return clean_ai_response(res)
        except: continue
    return ""

def parse_json_result(text):
    try: return json.loads(text)
    except:
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match:
            try: return json.loads(match.group(0))
            except: pass
    return []

# =========================================================
# [4. 카테고리별 엄격 분류 (Mistrot 방지 로직 추가)]
# =========================================================
def extract_top_entities(category, news_text_data):
    # 미스트롯과 같은 예능이 드라마로 분류되는 것을 막기 위한 강력한 배타적 규칙
    specific_rule = ""
    if category.lower() == 'k-drama':
        specific_rule = """
        [STRICT K-DRAMA MODE]
        1. 'content' MUST be a Scripted Series (Drama) title only.
        2. NEVER include Variety, Audition, or Survival shows (e.g., 'Mistrot', 'Singles Inferno', 'Transit Love').
        3. These audition/variety shows belong to 'k-entertain', NOT drama.
        """
    elif category.lower() == 'k-entertain':
        specific_rule = """
        [STRICT K-ENTERTAIN MODE]
        1. INCLUDE all Audition, Survival, Reality, and Talk shows (e.g., 'Mistrot', 'I Live Alone').
        2. EXCLUDE scripted dramas or movies.
        """
    elif category.lower() == 'k-pop':
        specific_rule = """
        [STRICT K-POP MODE]
        1. 'content' MUST be a Song, Album, or Idol Group name.
        2. EXCLUDE all TV show or Drama titles.
        """
    elif category.lower() == 'k-movie':
        specific_rule = """
        [STRICT K-MOVIE MODE]
        1. 'content' MUST be a theatrical film title only.
        """
    elif category.lower() == 'k-culture':
        specific_rule = """
        [STRICT K-CULTURE MODE]
        1. Focus on Lifestyle, Food, Places, and Social Trends.
        2. EXCLUDE specific celebrities or entertainment titles.
        """

    system_prompt = f"""
    You are an expert K-Content Analyst. Your goal is to extract the most trending keywords for '{category}'.
    
    {specific_rule}
    
    [CLASSIFICATION]
    1. 'content': The official TITLE of the work (Drama, Song, Movie).
    2. 'person': The name of the artist or actor.

    [OUTPUT]
    - Return a JSON LIST: [{"keyword": "English Title", "type": "content/person"}]
    - Translate all Korean titles to English.
    - If no relevant '{category}' items exist, return [].
    """
    
    user_input = news_text_data[:20000] 
    raw_result = ask_ai_master(system_prompt, user_input)
    parsed = parse_json_result(raw_result)
    
    if isinstance(parsed, list):
        seen = set()
        unique_list = []
        for item in parsed:
            if isinstance(item, dict) and 'keyword' in item and 'type' in item:
                kw = item['keyword']
                if kw not in seen:
                    seen.add(kw)
                    unique_list.append(item)
        return unique_list
    return []

# =========================================================
# [5. 뉴스 브리핑 생성]
# =========================================================
def synthesize_briefing(keyword, news_contents):
    system_prompt = f"""
    You are a Professional News Editor. 
    Topic: {keyword}
    [TASK] Write a 10-line news briefing in ENGLISH based on provided news.
    [RULE] No preamble, no <think> tags. If contents are irrelevant, return "INVALID_DATA".
    """
    user_input = "\n\n".join(news_contents)[:40000] 
    result = ask_ai_master(system_prompt, user_input)
    
    if not result or "INVALID_DATA" in result or len(result) < 50:
        return None
    return result
