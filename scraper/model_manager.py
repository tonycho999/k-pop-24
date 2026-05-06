import os

class ModelManager:
    def __init__(self):
        # GitHub Actions에 등록된 GROQ_API_KEY1 ~ GROQ_API_KEY20 등을 모두 찾아 리스트에 담습니다.
        self.groq_keys = []
        for i in range(1, 8):  
            key = os.environ.get(f"GROQ_API_KEY{i}")
            if key:
                self.groq_keys.append(key)
        
        # 제미나이 백업 키
        self.gemini_key = os.environ.get("GEMINI_API_KEY")

    def _select_groq_model(self, client):
        """API를 통해 사용 가능한 모델 리스트를 불러와 최적의 텍스트 모델을 동적 선택합니다."""
        try:
            models = client.models.list()
            all_models = models.data
            
            if not all_models:
                return "llama-3.3-70b-versatile"

            valid_models = []
            for m in all_models:
                mid = m.id.lower()
                # 텍스트(JSON) 생성에 부적합하거나 에러를 유발하는 모델 제외
                if any(x in mid for x in ['whisper', 'vision', 'llava', 'guard', 'compound', 'canopylabs', 'maverick']):
                    continue
                valid_models.append(m.id)

            if not valid_models:
                return "llama-3.3-70b-versatile"

            # 1순위: 가장 파라미터가 높고 고성능인 70b 또는 90b 모델
            high_perf = [m for m in valid_models if ("70b" in m.lower() or "90b" in m.lower()) and "preview" not in m.lower()]
            if high_perf:
                return high_perf[0]

            # 2순위: 그 외 일반 Llama 모델 중 최신 버전
            llama_models = [m for m in valid_models if "llama" in m.lower()]
            if llama_models:
                llama_models.sort(reverse=True)
                return llama_models[0]

            # 3순위: 그냥 리스트에 있는 사용 가능한 첫 번째 모델
            return valid_models[0]
            
        except Exception as e:
            print(f"⚠️ [Groq Model Fetch Error] {e}")
            return "llama-3.3-70b-versatile"

    def _select_gemini_model(self, client):
        """Gemini 실시간 리스트에서 동적으로 최신/최적 모델 1개 선택"""
        try:
            models = client.models.list()
            excluded_keywords = ["pro", "ultra", "advanced", "vision"] 
            
            candidates = []
            for m in models:
                name = m.name.lower().replace("models/", "")
                if not any(ex in name for ex in excluded_keywords):
                    candidates.append(name)

            # 1순위: flash 모델 중 최신 버전
            flash_models = [m for m in candidates if "flash" in m]
            if flash_models:
                flash_models.sort(reverse=True)
                return flash_models[0]
            
            # 2순위: 그 외 가능한 모델 중 가장 최신 버전
            if candidates:
                candidates.sort(reverse=True)
                return candidates[0]

            return "gemini-2.5-flash"
        except Exception as e:
            print(f"⚠️ [Gemini Model Fetch Error] {e}")
            return "gemini-2.5-flash"


    def generate_json(self, prompt):
        """
        Groq API 키를 순환하며 '동적으로 불러온 최적의 모델'로 생성을 시도합니다.
        모두 에러가 나면 Gemini의 '동적 최적 모델'로 백업 전환합니다.
        """
        
        # 🚀 1. Groq 메인 파이프라인 (키 로테이션 + 동적 모델 선택)
        if self.groq_keys:
            try:
                from groq import Groq
            except ImportError:
                print("⚠️ 'groq' 라이브러리가 필요합니다. (서버에 pip install groq 확인)")
                Groq = None

            if Groq:
                for i, api_key in enumerate(self.groq_keys):
                    try:
                        print(f"🔄 [ModelManager] Attempting Groq with Key {i + 1}...")
                        client = Groq(api_key=api_key)
                        
                        # 💡 해당 키로 사용 가능한 모델 목록을 불러와서 최적 모델 자동 선택!
                        model_name = self._select_groq_model(client)
                        print(f"🤖 [ModelManager] Auto-selected Groq Model: {model_name}")
                        
                        response = client.chat.completions.create(
                            model=model_name,
                            messages=[{"role": "user", "content": prompt}],
                            response_format={"type": "json_object"},
                            max_tokens=4000
                        )
                        print(f"✅ [ModelManager] Success with Groq Key {i + 1}!")
                        return response.choices[0].message.content
                        
                    except Exception as e:
                        print(f"⚠️ [ModelManager] Groq Key {i + 1} failed: {e}")
                        continue # 에러 발생 시 다음 키(i+2)로 이동

        # 🛡️ 2. Gemini 백업 파이프라인 (Groq 키가 전부 막혔을 때)
        if self.gemini_key:
            print("🔄 [ModelManager] All Groq keys failed! Falling back to Gemini Backup...")
            try:
                from google import genai
                gemini_client = genai.Client(api_key=self.gemini_key)
                
                # 💡 제미나이도 사용 가능한 최적 모델 자동 선택!
                model_name = self._select_gemini_model(gemini_client)
                print(f"✨ [ModelManager] Auto-selected Gemini Model: {model_name}")
                
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                print("✅ [ModelManager] Success with Gemini Backup!")
                return response.text
            except Exception as e:
                print(f"❌ [ModelManager] Gemini Fallback also failed: {e}")
        
        print("❌ [ModelManager] FATAL ERROR: All LLM APIs are currently down.")
        return None
