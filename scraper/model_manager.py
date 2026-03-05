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
        """Groq 실시간 리스트에서 에러 유발 모델을 제외하고 고성능 모델 1개 반환"""
        try:
            models = self.client.models.list()
            all_models = models.data
            
            if not all_models:
                return "llama-3.3-70b-versatile"

            valid_models = []
            for m in all_models:
                mid = m.id.lower()
                if ('whisper' in mid or 'vision' in mid or 'llava' in mid or 
                    'guard' in mid or 'compound' in mid or 'canopylabs' in mid or 
                    'maverick' in mid):
                    continue
                valid_models.append(m.id)

            if not valid_models:
                print("⚠️ [GroqManager] No valid models found after filtering.")
                return "llama-3.3-70b-versatile"

            high_perf = [m for m in valid_models if ("70b" in m.lower() or "90b" in m.lower()) and "preview" not in m.lower()]
            if high_perf:
                selected = high_perf[0]
                print(f"🤖 [GroqManager] High-Performance Selected: {selected}")
                return selected

            llama_models = [m for m in valid_models if "llama" in m.lower()]
            if llama_models:
                llama_models.sort(reverse=True)
                selected = llama_models[0]
                print(f"🤖 [GroqManager] Standard Llama Selected: {selected}")
                return selected

            fallback = valid_models[0]
            print(f"⚠️ [GroqManager] Fallback: {fallback}")
            return fallback
            
        except Exception as e:
            print(f"❌ [GroqManager] Error: {e}")
            return "llama-3.3-70b-versatile"

    def _get_best_gemini_model(self):
        """Gemini 실시간 리스트에서 동적으로 최신/최적 모델 1개 선택 (하드코딩 배제)"""
        try:
            import google.generativeai as genai
            
            models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            excluded_keywords = ["pro", "ultra", "advanced", "vision"] 
            
            candidates = []
            for m in models:
                name = m.name.lower()
                if not any(ex in name for ex in excluded_keywords):
                    candidates.append(m.name)

            flash_models = [m for m in candidates if "flash" in m]

            if flash_models:
                flash_models.sort(reverse=True)
                selected = flash_models[0] 
                print(f"✨ [GeminiManager] Auto-selected from list: {selected}")
                return selected
            
            if candidates:
                candidates.sort(reverse=True)
                selected = candidates[0]
                print(f"⚠️ [GeminiManager] Fallback to candidate from list: {selected}")
                return selected

            # API 응답 자체가 비어있을 경우의 최후 보루
            return "models/gemini-2.5-flash"

        except Exception as e:
            print(f"❌ [GeminiManager] Error fetching models: {e}")
            return "models/gemini-2.5-flash"
