import os
import time
from openai import OpenAI
from groq import Groq

class NewsEngine:
    def __init__(self):
        self.pplx = OpenAI(api_key=os.environ.get("PERPLEXITY_API_KEY"), base_url="https://api.perplexity.ai")
        self.groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def fetch_trending_people(self, category):
        """Perplexity: 1시간 내 화제 인물 30명 및 기사 스니펫 수집"""
        prompt = f"지난 24시간 동안 한국 {category} 분야에서 가장 화제인 인물 30명을 리스트업하고, 각 인물별 핵심 뉴스 팩트 3개를 JSON으로 줘."
        
        response = self.pplx.chat.completions.create(
            model="sonar-pro",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def summarize_with_groq(self, raw_news, category):
        """Groq: 수집된 정보를 바탕으로 인물 기사 최종 요약 (무료 티어 RPM 고려)"""
        system_prompts = {
            "k-pop": "너는 트렌디한 아이돌 전문 기자야. 팬들이 좋아할 이모지를 섞어서 써줘.",
            "k-movie": "너는 냉철한 영화 평론가야. 전문적인 용어를 섞어서 분석해줘."
        }
        
        completion = self.groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompts.get(category, "너는 전문 에디터야.")},
                {"role": "user", "content": f"다음 정보를 기사 제목과 본문으로 요약해: {raw_news}"}
            ]
        )
        time.sleep(2) # Groq 무료 버전 Rate Limit 방지
        return completion.choices[0].message.content
