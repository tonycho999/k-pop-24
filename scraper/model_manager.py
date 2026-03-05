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
        """
        Groq 실시간 리스트에서:
        1. 에러 유발 모델을 제외하고
        2. 성능이 좋은 모델을 우선 선택하여
        3. 단 하나의 모델 ID(String)를 반환합니다.
        """
        try:
            models = self.client.models.list()
            all_models = models.data
            
            if not all_models:
                return "llama-3.3-70b-versatile" # 안전장치

            valid_models = []
            for m in all_models:
                mid = m.id.lower()
                
                # 제외 조건
                if ('whisper' in mid or
                    'vision' in mid or
                    'llava' in mid or
                    'guard' in mid or
                    'compound' in mid or
                    'canopylabs' in mid or
                    'maverick' in mid):
                    continue
                
                valid_models.append(m.id)

            if not valid_models:
                print("⚠️ [GroqManager] No valid models found after filtering.")
                return "llama-3.3-70b-versatile"

            # 우선순위 1: 고성능 모델
            high_perf = [
                m for m in valid_models 
                if ("70b" in m.lower() or "90b" in m.lower()) 
                and "preview" not in m.lower()
            ]
            
            if high_perf:
                selected = high_perf[0] # [수정] 리스트가 아닌 문자열 반환
                print(f"🤖 [GroqManager] High-Performance Selected: {selected}")
                return selected

            # 우선순위 2: 일반 Llama 모델
            llama_models = [m for m in valid_models if "llama" in m.lower()]
            if llama_models:
                llama_models.sort(reverse=True)
                selected = llama_models[0] # [수정] 문자열 반환
                print(f"🤖 [GroqManager] Standard Llama Selected: {selected}")
                return selected

            # 최후의 수단
            fallback = valid_models[0] # [수정] 문자열 반환
            print(f"⚠️ [GroqManager] Fallback: {fallback}")
            return fallback
            
        except Exception as e:
            print(f"❌ [GroqManager] Error: {e}")
            return "llama-3.3-70b-versatile"

    def _get_best_gemini_model(self):
        """
        Gemini 실시간 리스트에서 동적으로 최신/최적 모델 1개 선택
        (1.5 등 특정 버전 하드코딩 제거)
        """
        try:
            import google.generativeai as genai
            
            # 생성 가능한 모델만 추출
            models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # 너무 무겁거나 이미지 전용인 모델 제외
            excluded_keywords = ["pro", "ultra", "advanced", "vision"] 
            
            candidates = []
            for m in models:
                name = m.name.lower()
                if not any(ex in name for ex in excluded_keywords):
                    candidates.append(m.name)

            # Flash(속도/가성비 최적화) 계열 모델 필터링
            flash_models = [m for m in candidates if "flash" in m]

            # [수정] 내림차순 정렬하면 gemini-2.5-flash 가 gemini-1.5-flash 보다 위에 옴
            if flash_models:
                flash_models.sort(reverse=True)
                selected = flash_models[0] # [수정] 가장 최신 버전 1개만 추출
                print(f"✨ [GeminiManager] Auto-selected: {selected}")
                return selected
            
            # Flash 모델이 아예 없으면 다른 후보 중 최신 모델 선택
            if candidates:
                candidates.sort(reverse=True)
                selected = candidates[0] # [수정] 문자열 반환
                print(f"⚠️ [GeminiManager] Fallback to candidate: {selected}")
                return selected

            # 진짜 아무것도 안 잡힐 때의 극단적 최후 수단 (가장 최신 기본값)
            return "models/gemini-2.5-flash"

        except Exception as e:
            print(f"❌ [GeminiManager] Error fetching models: {e}")
            return "models/gemini-2.5-flash"
