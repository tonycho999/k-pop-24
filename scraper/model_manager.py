import os

class ModelManager:
    def __init__(self, client=None, provider="groq"):
        self.client = client
        self.provider = provider

    def get_best_model(self):
        """공급자(Groq/Gemini)에 따라 최적의 모델을 동적으로 선택합니다."""
        if self.provider == "groq":
            return self._get_best_groq_model()
        elif self.provider == "gemini":
            return self._get_best_gemini_model()
        else:
            return None

    def _get_best_groq_model(self):
        """(기존 로직 유지) Groq 실시간 고성능 모델 선택"""
        try:
            models = self.client.models.list()
            available_models = models.data
            
            if not available_models:
                return "llama-3.1-8b-instant"

            # 1. 70b/90b 고성능 모델 우선
            high_performance_models = [
                m.id for m in available_models 
                if ("70b" in m.id.lower() or "90b" in m.id.lower()) 
                and "preview" not in m.id.lower()
            ]
            
            if high_performance_models:
                selected = high_performance_models
                print(f"🤖 [GroqManager] High-performance model auto-selected: {selected}")
                return selected

            # 2. Llama 계열 차선
            llama_models = [m.id for m in available_models if "llama" in m.id.lower()]
            if llama_models:
                selected = llama_models
                print(f"🤖 [GroqManager] Llama model auto-selected: {selected}")
                return selected

            # 3. 최후의 수단
            fallback = available_models.id
            print(f"⚠️ [GroqManager] Fallback: {fallback}")
            return fallback
            
        except Exception as e:
            print(f"❌ [GroqManager] Error: {e}")
            return "llama-3.1-8b-instant"

    def _get_best_gemini_model(self):
        """
        [신규 추가] Gemini 실시간 가용 모델 리스트 조회 및 자동 선택
        - 'Pro', 'Ultra' 등 무거운 유료 모델 제외
        - 'Flash' 등 빠르고 가벼운 모델 우선 선택
        """
        try:
            # self.client는 여기서 google.generativeai 모듈 자체입니다.
            import google.generativeai as genai
            
            # 1. 'generateContent' 기능을 지원하는 모델만 리스트업
            models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # 2. 제외 키워드 설정 (유료/고비용 모델 방지)
            # 'pro', 'ultra', 'advanced' 등이 포함된 모델은 리스트에서 배제
            excluded_keywords = ["pro", "ultra", "advanced", "vision"] 
            
            filtered_models = []
            for m in models:
                name = m.name.lower() # 예: models/gemini-1.5-flash
                # 제외 키워드가 없고, 'latest'나 'flash' 같은 최신/경량 키워드가 있는지 확인
                if not any(ex in name for ex in excluded_keywords):
                    filtered_models.append(m.name)

            if not filtered_models:
                # 필터링을 너무 빡빡하게 해서 남은게 없다면, 'flash'가 들어간 모델이라도 찾음
                filtered_models = [m.name for m in models if "flash" in m.name.lower()]

            # 3. 우선순위 정렬 (최신 버전인 1.5가 1.0보다 먼저 오도록)
            # 보통 리스트는 알파벳 순이므로 역순 정렬하면 1.5가 위로 뜰 확률 높음
            filtered_models.sort(reverse=True)

            if filtered_models:
                selected = filtered_models
                print(f"✨ [GeminiManager] Auto-selected model: {selected}")
                return selected
            
            # 4. 정말 아무것도 못 찾았을 때의 안전장치
            print("⚠️ [GeminiManager] No optimal model found. Using hardcoded fallback.")
            return "models/gemini-1.5-flash"

        except Exception as e:
            print(f"❌ [GeminiManager] Error fetching models: {e}")
            return "models/gemini-1.5-flash"
