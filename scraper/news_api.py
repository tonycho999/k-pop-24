import os
import time
import json
from openai import OpenAI
from groq import Groq

class NewsEngine:
    def __init__(self):
        self.pplx = OpenAI(
            api_key=os.environ.get("PERPLEXITY_API_KEY"), 
            base_url="https://api.perplexity.ai"
        )
        self.groq = Groq(
            api_key=os.environ.get("GROQ_API_KEY")
        )

    def get_trends_and_rankings(self, category):
        """
        [Step 1] Perplexity: 철저하게 24시간 이내의 한국 뉴스만 검색하여 '한국어'로 데이터 반환
        """
        
        # 카테고리별 특별 지시사항 (K-Culture 인물 제외 등)
        additional_rule = ""
        if category == "k-culture":
            additional_rule = """
            [특별 규칙: k-culture]
            1. 'people' 리스트에 절대 연예인(가수, 배우, 아이돌) 이름을 넣지 마시오.
            2. 대신 '핫플레이스(장소)', '유행하는 음식', '최신 유행어(밈)', '축제/행사', '패션 아이템'을 'name'에 넣으시오.
            3. 인물이 아닌 '문화 트렌드' 자체에 집중하시오.
            """
        elif category == "k-entertain":
            additional_rule = """
            [특별 규칙: k-entertain]
            1. 'top10' 리스트는 반드시 현재 방영 중이거나 화제인 **'한국 TV 예능 프로그램'의 제목**으로만 구성하시오.
            2. 뉴스 사건이나 연예인 개인의 이름은 'top10' 랭킹에 넣지 마시오.
            """
        else:
            additional_rule = "한국에서 활동하는 연예인/작품 위주로 분석하시오."

        # 시스템 프롬프트: 한국어 검색 강제
        system_prompt = "당신은 한국 엔터테인먼트 전문가입니다. 반드시 유효한 JSON만 출력하세요. 한국 국내 뉴스 소스만 검색하세요."
        
        user_prompt = f"""
        현재 시점(Real-time) 기준으로 '한국 국내'에서 발생한 '{category}' 분야 트렌드를 분석해 JSON으로 답하세요.
        
        {additional_rule}

        다음 두 가지 키를 가진 JSON 형식으로 작성하시오 (값은 모두 **한국어**로 작성):

        1. "people": 지난 24시간 동안 한국 언론과 SNS에서 언급량이 급증한 대상 30개.
           - "name": 이름 (한국어)
           - "facts": 기자가 기사를 작성할수 있도록 화제 이유 핵심 팩트를 상세하게 3줄 요약 (한국어)
        
        2. "top10": 현재 한국에서 가장 인기 있는 {category} 관련 콘텐츠 제목 TOP 10.
           - "rank": 1~10
           - "title": 제목 (한국어. 예: 눈물의 여왕, 런닝맨)
           - "info": 부가 정보 (한국어. 예: 시청률 15%, 가수: 아일릿)

        설명 없이 오직 JSON 문자열만 출력하시오.
        """

        try:
            response = self.pplx.chat.completions.create(
                model="sonar-pro",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content, user_prompt
            
        except Exception as e:
            print(f"Perplexity API Error: {e}")
            return "{}", user_prompt

    def translate_top10_to_english(self, top10_list):
        """
        [Step 2-A] Groq: 한국어 Top 10 리스트를 통째로 영어로 번역
        """
        if not top10_list:
            return []

        prompt = f"""
        Translate the values in the following JSON list from Korean to English for a global audience.
        Keep the 'rank' as is. Translate 'title' and 'info'.
        
        Input JSON:
        {json.dumps(top10_list, ensure_ascii=False)}
        
        Output ONLY the translated JSON string.
        """

        try:
            completion = self.groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            # JSON 파싱해서 반환
            translated_str = completion.choices[0].message.content
            # 마크다운 제거 등 간단한 정제
            if "```" in translated_str:
                import re
                match = re.search(r"```(?:json)?\s*(.*)\s*```", translated_str, re.DOTALL)
                if match: translated_str = match.group(1)
            
            return json.loads(translated_str)
        except Exception as e:
            print(f"Groq Translation Error: {e}")
            return top10_list # 에러나면 한국어 원본 반환

    def edit_with_groq(self, person_name, news_facts, category):
        """
        [Step 2-B] Groq: 한국어 팩트를 받아 '영어 기사' 작성 + 점수 부여
        """
        system_msg = "You are a professional journalist covering Korean entertainment news for global fans."
        
        user_msg = f"""
        Topic (Korean): {person_name}
        Facts (Korean): {news_facts}

        Based on the Korean facts above, write a news article **in English**.
        
        [Requirements]
        1. **Headline**: Catchy English headline on the first line.
        2. **Body**: English article body starting from the second line (3 paragraphs).
        3. **Language**: Strictly **English**.
        4. **Score**: At the very end, write "###SCORE: XX" (50-99) based on viral potential.
        5. Do not invent facts.
        """

        try:
            completion = self.groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.7
            )
            time.sleep(1.5)
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Groq API Error ({person_name}): {e}")
            return f"News about {person_name}\n{news_facts}\n###SCORE: 50"
