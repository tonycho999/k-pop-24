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
        """Groq 실시간 리스트에서 가장 성능 좋은 모델 1개 선택"""
        try:
            # 1. 모델 리스트 조회
            models = self.client.models.list()
            available_models = models.data
            
            if not available_models:
                return "llama-3.3-70b-versatile" # 안전장치

            # 2. 모델 ID 문자열만 추출
            model_ids = [m.id for m in available_models]

            # 3. 우선순위 1: Llama 3.3 또는 3.1의 70B급 (가장 똑똑함)
            # 'preview'가 아닌 정식 버전을 선호
            high_perf = [
                m for m in model_ids 
                if ("70b" in m.lower() or "90b" in m.lower()) 
                and "preview" not in m.lower()
            ]
            
            # 리스트가 비어있지 않으면 가장 첫번째(보통 최신) 선택
            if high_perf:
                # Groq는 보통 llama-3.3-70b-versatile이 리스트 상단에 옴
                selected = high_perf
                print(f"🤖 [GroqManager] Selected High-Performance: {selected}")
                return selected

            # 4. 우선순위 2: 70B가 없으면 Llama 계열 아무거나 (8b 등)
            llama_models = [m for m in model_ids if "llama" in m.lower()]
            if llama_models:
                selected = llama_models
                print(f"🤖 [GroqManager] Selected Standard Llama: {selected}")
                return selected

            # 5. 최후의 수단: 리스트의 맨 첫 번째 모델
            fallback = model_ids
            print(f"⚠️ [GroqManager] Fallback: {fallback}")
            return fallback
            
        except Exception as e:
            print(f"❌ [GroqManager] Error: {e}")
            return "llama-3.3-70b-versatile"

    def _get_best_gemini_model(self):
        """
        Gemini 실시간 리스트에서 무료/고속(Flash) 모델 1개 선택
        """
        try:
            import google.generativeai as genai
            
            # 1. 'generateContent' 지원 모델 조회
            models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # 2. 제외 키워드 (유료/무거운 모델)
            excluded_keywords = ["pro", "ultra", "advanced", "vision"] 
            
            # 3. 1차 필터링: 제외 키워드 없는 것들
            candidates = []
            for m in models:
                name = m.name.lower()
                if not any(ex in name for ex in excluded_keywords):
                    candidates.append(m.name)

            # 4. 2차 필터링: 그 중에서 'flash'가 들어간 것 우선 (속도/최신성)
            flash_models = [m for m in candidates if "flash" in m]

            # 5. 정렬 및 선택 (역순 정렬하면 최신 버전이 위로 옴: 1.5 > 1.0)
            if flash_models:
                flash_models.sort(reverse=True)
                selected = flash_models # [중요] 리스트가 아니라 요소 1개 선택
                print(f"✨ [GeminiManager] Auto-selected: {selected}")
                return selected
            
            # Flash가 없으면 candidates 중 최신 선택
            if candidates:
                candidates.sort(reverse=True)
                selected = candidates
                print(f"⚠️ [GeminiManager] Fallback to candidate: {selected}")
                return selected

            # 정말 아무것도 없으면 하드코딩
            print("⚠️ [GeminiManager] No optimal model found. Using default.")
            return "models/gemini-1.5-flash"

        except Exception as e:
            print(f"❌ [GeminiManager] Error fetching models: {e}")
            return "models/gemini-1.5-flash"
