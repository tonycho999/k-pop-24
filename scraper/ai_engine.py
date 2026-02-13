import os
import json
from groq import Groq

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("⚠️ GROQ_API_KEY가 없습니다.")
        return None
    return Groq(api_key=api_key)

def get_latest_models(client):
    """
    [완전 동적 방식]
    하드코딩된 리스트 없이, API에서 받아온 모델들을
    버전이 높은 순서(3.3 > 3.1)대로 자동 정렬하여 반환합니다.
    """
    try:
        # 1. Groq가 제공하는 모든 모델 가져오기
        all_models = client.models.list()
        model_ids = [m.id for m in all_models.data]
        
        # 2. 텍스트 생성용이 아닌 모델(Whisper 등) 제외
        text_models = [m for m in model_ids if "whisper" not in m and "vision" not in m]

        # 3. [핵심 로직] 역순 정렬 (Descending)
        # 문자열 정렬 특성상 "llama-3.3-..."이 "llama-3.1-..."보다 큽니다.
        # 따라서 역순으로 정렬하면 가장 높은 버전 숫자를 가진 모델이 0번 인덱스로 옵니다.
        # 예: ['llama-3.3-70b', 'llama-3.1-70b', 'gemma-2-9b']
        text_models.sort(reverse=True)
        
        # 로그로 현재 선택된 최신 모델 3개 보여주기 (확인용)
        # print(f"      📡 감지된 최신 모델 TOP 3: {text_models[:3]}")
        
        return text_models

    except Exception as e:
        print(f"      ⚠️ 모델 목록 조회 실패: {e}")
        # 만약 API 호출 자체가 실패할 경우를 대비한 최소한의 비상용 값
        return ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]

def ai_category_editor(category, news_list):
    client = get_groq_client()
    if not client: return []
    
    # [수정] 하드코딩 없이 현재 시점의 최신 모델들을 가져옴
    dynamic_models = get_latest_models(client)
    
    # [프롬프트] 요약 길이 40~50% 유지
    system_prompt = f"""
    You are an expert K-Content News Editor for '{category}'.
    
    [TASK]
    1. Select the most meaningful articles from the list.
    2. **Summary Requirement:** - The summary length must be **40% to 50% of the original text**.
       - It must be detailed and capture the full context.
       - Do NOT write single-sentence summaries.
    3. **Scoring:** Assign a score (0.0 - 10.0).
       - Score >= 5.0: Meaningful news.
       - Score < 5.0: Minor updates or spam.
    
    [OUTPUT FORMAT]
    Return a JSON array ONLY:
    [
        {{
            "original_index": (int) input index,
            "eng_title": "English Title",
            "summary": "Detailed summary (40-50% length)",
            "score": (float) 0.0-10.0,
            "rank": (int) priority
        }}
    ]
    """

    # 입력 데이터 (토큰 절약)
    input_data = [
        {"index": i, "title": n['title'], "body": n.get('originallink', n['link'])[:500]} 
        for i, n in enumerate(news_list)
    ]

    # [수정] 자동으로 정렬된 최신 모델부터 하나씩 시도
    for model_id in dynamic_models:
        try:
            # print(f"      🤖 시도 중: {model_id}...")
            
            completion = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(input_data, ensure_ascii=False)}
                ],
                temperature=0.3
            )
            
            result = completion.choices[0].message.content.strip()
            
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]
            
            return json.loads(result)

        except Exception as e:
            # print(f"      ⚠️ {model_id} 실패. 다음 모델 시도.")
            continue
            
    print("      ❌ 사용 가능한 모든 Groq 모델 시도 실패.")
    return []
