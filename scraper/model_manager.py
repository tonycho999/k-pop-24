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
        1. 에러 유발 모델(Vision, Audio, Guard, 약관필요 등)을 제외하고
        2. 성능이 좋은(70b/90b) 모델을 우선 선택하여
        3. 단 하나의 모델 ID(String)를 반환합니다.
        """
        try:
            # 1. 모델 리스트 조회
            models = self.client.models.list()
            all_models = models.data
            
            if not all_models:
                return "llama-3.3-70b-versatile" # 안전장치

            # 2. [필터링] 채팅용으로 부적합한 모델 제외 (참고 코드 로직 적용)
            valid_models = []
            for m in all_models:
                mid = m.id.lower()
                
                # 제외 조건 확인
                if ('whisper' in mid or       # 음성용
                    'vision' in mid or        # 이미지용
                    'llava' in mid or         # 이미지용
                    'guard' in mid or         # 보안용
                    'compound' in mid or      # 비표준 응답
                    'canopylabs' in mid or    # 약관 동의 필요 [NEW]
                    'maverick' in mid):       # 중단 예정
                    continue
                
                valid_models.append(m.id)

            if not valid_models:
                print("⚠️ [GroqManager] No valid models found after filtering.")
                return "llama-3.3-70b-versatile"

            # 3. [우선순위 1] 70b 또는 90b 고성능 모델 (Preview 제외 선호)
            high_perf = [
                m for m in valid_models 
                if ("70b" in m.lower() or "90b" in m.lower()) 
                and "preview" not in m.lower()
            ]
            
            if high_perf:
                # 리스트의 0번째 요소를 문자열로 반환
                selected = high_perf 
                print(f"🤖 [GroqManager] High-Performance Selected: {selected}")
                return selected

            # 4. [우선순위 2] Llama 3.x 계열 (가장 무난함)
            # 최신 버전(숫자가 높은 것)이 위로 오도록 정렬 시도
            llama_models = [m for m in valid_models if "llama" in m.lower()]
            if llama_models:
                # 예: llama-3.3, llama-3.1 순으로 정렬하기 위해 역순 정렬
                llama_models.sort(reverse=True)
                selected = llama_models
                print(f"🤖 [GroqManager] Standard Llama Selected: {selected}")
                return selected

            # 5. [최후의 수단] 필터링 통과한 것 중 아무거나 첫 번째
            fallback = valid_models
            print(f"⚠️ [GroqManager] Fallback: {fallback}")
            return fallback
            
        except Exception as e:
            print(f"❌ [GroqManager] Error: {e}")
            # 에러 발생 시 가장 안정적인 하드코딩 모델 반환
            return "llama-3.3-70b-versatile"

    def _get_best_gemini_model(self):
        # ... (기존 Gemini 코드는 그대로 유지) ...
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
                selected = flash_models 
                print(f"✨ [GeminiManager] Auto-selected: {selected}")
                return selected
            
            if candidates:
                candidates.sort(reverse=True)
                selected = candidates
                print(f"⚠️ [GeminiManager] Fallback to candidate: {selected}")
                return selected

            return "models/gemini-1.5-flash"

        except Exception as e:
            print(f"❌ [GeminiManager] Error fetching models: {e}")
            return "models/gemini-1.5-flash"
