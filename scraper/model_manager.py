import os

class GroqModelManager:
    def __init__(self, client):
        self.client = client

    def get_best_model(self):
        """
        하드코딩된 모델명 없이, 실시간 리스트에서 가장 고성능 모델을 자동으로 선택합니다.
        """
        try:
            models = self.client.models.list()
            available_models = models.data # Groq 가용 모델 객체 리스트
            
            if not available_models:
                return "llama-3.1-8b-instant" # 최후의 수단

            # 1. 모델 ID에 '70b' 또는 '90b'가 포함된 고성능 모델을 우선 탐색
            high_performance_models = [
                m.id for m in available_models 
                if ("70b" in m.id.lower() or "90b" in m.id.lower()) 
                and "preview" not in m.id.lower() # 안정성을 위해 프리뷰 제외
            ]
            
            if high_performance_models:
                # 고성능 모델 중 가장 최신(보통 리스트 상단) 모델 반환
                selected = high_performance_models[0]
                print(f"🤖 [ModelManager] High-performance model auto-selected: {selected}")
                return selected

            # 2. 고성능 모델이 없다면, 'llama' 계열 중 아무거나 선택
            llama_models = [m.id for m in available_models if "llama" in m.id.lower()]
            if llama_models:
                selected = llama_models[0]
                print(f"🤖 [ModelManager] Llama model auto-selected: {selected}")
                return selected

            # 3. 그 외 가용 리스트의 첫 번째 모델 선택
            fallback = available_models[0].id
            print(f"⚠️ [ModelManager] Fallback to first available model: {fallback}")
            return fallback
            
        except Exception as e:
            print(f"❌ [ModelManager] Error: {e}")
            return "llama-3.1-8b-instant"
