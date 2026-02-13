import os
import json
import time
import re
import requests
from groq import Groq
from scraper.config import CATEGORIES, EXCLUDE_KEYWORDS

# =========================================================
# 1. [핵심] 지능형 모델 필터링 (Text Generation Only)
# =========================================================

def get_groq_text_models():
    """
    [Groq] 전체 모델 중 'Vision', 'Whisper' 등 글 못 쓰는 모델 제외
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return []
    
    try:
        client = Groq(api_key=api_key)
        all_models = client.models.list()
        
        valid_models = []
        for m in all_models.data:
            mid = m.id.lower()
            # ⛔ 블랙리스트: 이미지(vision), 음성(whisper, audio) 모델 제외
            if 'vision' in mid or 'whisper' in mid or 'audio' in mid:
                continue
            valid_models.append(m.id)
            
        # 최신 모델이 위로 오도록 역순 정렬 (Llama-3.3 > 3.1)
        valid_models.sort(reverse=True)
        # print(f"      ✅ Groq 텍스트 모델 선별 완료: {len(valid_models)}개")
        return valid_models
    except Exception as e:
        print(f"      ⚠️ Groq 모델 조회 실패: {e}")
        return []

def get_openrouter_text_models():
    """
    [OpenRouter] 전체 중 'Instruct', 'Chat'만 포함하고 'Diffusion' 등 제외
    """
    try:
        res = requests.get("https://openrouter.ai/api/v1/models", timeout=5)
        if res.status_code != 200: return []
        
        data = res.json().get('data', [])
        valid_models = []
        
        for m in data:
            mid = m['id'].lower()
            
            # ✅ 화이트리스트: 무료(:free)이면서 대화형(chat, instruct, gpt)인 것
            if ':free' in mid and ('chat' in mid or 'instruct' in mid or 'gpt' in mid):
                # ⛔ 블랙리스트: 그림 그리는 모델(diffusion, image, vision) 철저히 배제
                if 'diffusion' in mid or 'image' in mid or 'vision' in mid or '3d' in mid:
                    continue
                valid_models.append(m['id'])
        
        valid_models.sort(reverse=True)
        # print(f"      ✅ OpenRouter 텍스트 모델 선별 완료: {len(valid_models)}개")
        return valid_models
    except Exception as e:
        # print(f"      ⚠️ OpenRouter 모델 조회 실패: {e}")
        return []

def get_hf_text_models():
    """
    [Hugging Face] API 자체 필터링 기능 사용 (pipeline_tag=text-generation)
    """
    try:
        # 'text-generation' 태그가 달린 모델만 상위 5개 가져오기
        url = "https://huggingface.co/api/models?pipeline_tag=text-generation&sort=downloads&direction=-1&limit=5"
        res = requests.get(url, timeout=5)
        
        if res.status_code == 200:
            return [m['modelId'] for m in res.json()]
    except:
        pass
    return ["mistralai/Mistral-7B-Instruct-v0.3"] # 실패 시 안전빵 모델

# =========================================================
# 2. 마스터 AI 실행 엔진 (순차적 시도)
# =========================================================

def ask_ai_master(system_prompt, user_input):
    """
    Groq -> OpenRouter -> HF 순서로 '텍스트 전용 모델'만 골라서 시도
    """
    
    # 1. Groq 시도
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        models = get_groq_text_models()
        client = Groq(api_key=groq_key)
        
        for model_id in models:
            try:
                # print(f"      🤖 Groq 시도: {model_id}")
                completion = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
                    temperature=0.3
                )
                return completion.choices[0].message.content.strip()
            except Exception:
                continue

    # 2. OpenRouter 시도 (Groq 실패 시)
    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        print("      🚨 Groq 실패 -> OpenRouter 가동")
        models = get_openrouter_text_models()
        
        for model_id in models:
            try:
                # print(f"      🤖 OR 시도: {model_id}")
                res = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {or_key}"},
                    json={
                        "model": model_id,
                        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
                        "temperature": 0.3
                    },
                    timeout=20
                )
                if res.status_code == 200:
                    content = res.json()['choices'][0]['message']['content']
                    if content: return content
            except:
                continue

    # 3. Hugging Face 시도 (최후의 보루)
    hf_token = os.getenv("HF_API_TOKEN")
    if hf_token:
        print("      💀 OpenRouter 실패 -> HF 가동")
        models = get_hf_text_models()
        
        for model_id in models:
            try:
                API_URL = f"https://api-inference.huggingface.co/models/{model_id}"
                headers = {"Authorization": f"Bearer {hf_token}"}
                payload = {"inputs": f"<s>[INST] {system_prompt}\n\n{user_input} [/INST]"}
                res = requests.post(API_URL, headers=headers, json=payload, timeout=20)
                
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and 'generated_text' in data[0]:
                        return data[0]['generated_text']
                    elif isinstance(data, dict) and 'generated_text' in data:
                        return data['generated_text']
            except: continue

    return ""

# =========================================================
# 3. 강력한 JSON 파서 (AI 사족 제거기)
# =========================================================

def parse_json_result(text):
    """
    AI가 "Here is the JSON:" 같은 말을 붙여도 무조건 순수 JSON만 추출
    """
    if not text: return []
    
    # 1. 가장 깔끔한 경우
    try: return json.loads(text)
    except: pass
    
    # 2. 마크다운 코드블럭 (```json) 제거
    try:
        if "```" in text:
            # ```json 뒤에 있는 내용 추출
            text = text.split("```json")[-1].split("```")[0].strip()
            # 만약 json 안쓰고 그냥 ``` 만 썼을 경우 대비
            if not text.startswith("[") and not text.startswith("{"):
                 text = text.split("```")[-1].split("```")[0].strip()
            return json.loads(text)
    except: pass
    
    # 3. 정규표현식으로 [ ... ] 또는 { ... } 패턴 강제 추출 (가장 강력)
    try:
        # 대괄호(리스트)나 중괄호(객체)로 시작하고 끝나는 부분을 찾음
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except: pass
    
    return []

# =========================================================
# 4. 외부 호출 인터페이스
# =========================================================

def ai_filter_and_rank_keywords(raw_keywords):
    system_prompt = f"""
    You are the Chief Editor of 'K-Enter24'. 
    Filter keywords for: {json.dumps(CATEGORIES, indent=2)}.
    Exclude: {', '.join(EXCLUDE_KEYWORDS)}.
    Return JSON object ONLY: {{"k-pop": ["keyword1"], ...}}
    """
    # 리스트를 JSON 문자열로 변환해서 전달
    raw_result = ask_ai_master(system_prompt, json.dumps(raw_keywords, ensure_ascii=False))
    
    parsed = parse_json_result(raw_result)
    return parsed if isinstance(parsed, dict) else {}

def ai_category_editor(category, news_list):
    system_prompt = f"""
    You are an expert K-Content News Editor for '{category}'.
    Summarize these articles.
    
    [OUTPUT FORMAT]
    Return a VALID JSON ARRAY strictly like this:
    [
        {{
            "original_index": 0,
            "eng_title": "Translated Title",
            "summary": "Context... Development... Impact...",
            "score": 8.5
        }}
    ]
    """
    
    input_data = []
    # AI 입력 토큰 제한을 위해 기사 본문 길이 조절 (최대 1000자)
    for i, n in enumerate(news_list):
        input_data.append({
            "index": i, 
            "title": n['title'], 
            "body": n.get('full_content', '')[:1000]
        })

    raw_result = ask_ai_master(system_prompt, json.dumps(input_data, ensure_ascii=False))
    
    parsed_list = parse_json_result(raw_result)
    
    if parsed_list and isinstance(parsed_list, list):
        print(f"      ✅ AI 분석 성공: {len(parsed_list)}개 생성")
        return parsed_list
    else:
        # print("      ❌ AI 응답 파싱 실패")
        return []
