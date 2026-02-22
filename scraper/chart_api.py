import os
import json
from datetime import datetime
from groq import Groq
from supabase import create_client

# 1. 초기 설정
GROQ_API_KEY = os.environ.get("GROQ_API_KEY1") # 로테이션 키 중 하나 사용
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_rankings_from_groq(category):
    """Groq에게 실시간 데이터를 물어보고 영문 JSON으로 받음"""
    
    # K-Culture의 경우 연예인 제외 조건을 프롬프트에 강력하게 주입
    category_constraints = ""
    if category == "k-culture":
        category_constraints = "STRICT RULE: Exclude ANY celebrities, idols, actors, or fan-related events. Focus only on locations, food, or traditional trends."

    prompt = f"""
    Today's date is {datetime.now().strftime('%B %d, %2026')}.
    Search and analyze the LATEST South Korean data (within the last 24 hours).
    Provide the Top 10 rankings for '{category}' in South Korea.
    
    {category_constraints}

    [OUTPUT RULES]
    1. Language: English (Translate all titles and info).
    2. Timeframe: Must be based on news/trends from the last 24 hours.
    3. Format: Return ONLY a JSON object:
       {{"top10": [{{"rank": 1, "title": "English Title", "info": "Brief English Info"}}, ...]}}
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-specdec", # 실시간 추론에 가장 강력한 모델
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1 # 정확도를 위해 낮게 설정
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ Groq Error for {category}: {e}")
        return {"top10": []}

def run_update():
    # 영화는 공식 API가 있으니 그대로 두고, 나머지만 Groq로 수집
    categories = ["k-pop", "k-drama", "k-entertain", "k-culture"]
    
    for cat in categories:
        print(f"🤖 Groq is searching for {cat}...")
        result = get_rankings_from_groq(cat)
        data = result.get("top10", [])
        
        if data:
            db_data = []
            for item in data:
                db_data.append({
                    "category": cat,
                    "rank": item.get('rank'),
                    "title": item.get('title'),
                    "meta_info": str(item.get('info', '')),
                    "score": 100,
                    "updated_at": datetime.now().isoformat()
                })
            
            # DB 갱신
            supabase.table('live_rankings').delete().eq('category', cat).execute()
            supabase.table('live_rankings').insert(db_data).execute()
            print(f"✅ {cat} updated in English via Groq.")
        else:
            print(f"⚠️ No data for {cat}.")

if __name__ == "__main__":
    run_update()
