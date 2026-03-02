import os
from groq import Groq

def inspect_structure():
    print("🔍 Starting Groq Response Inspection...")
    
    api_key = os.environ.get("GROQ_API_KEY1")
    if not api_key:
        print("❌ GROQ_API_KEY1 is missing")
        return

    client = Groq(api_key=api_key)

    try:
        # 가장 단순한 요청
        print("📡 Sending simple request to Groq...")
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": "hi"}],
            model="llama-3.3-70b-versatile",
        )

        print("\n" + "="*50)
        print("✅ [Inspection Result]")
        print("="*50)

        # 1. 최상위 객체 타입 확인
        print(f"1. Type of 'completion': {type(completion)}")
        
        # 2. dir()로 사용 가능한 속성(Attribute) 확인
        print(f"2. Attributes (dir): {dir(completion)}")

        # 3. 'choices' 속성 확인
        if hasattr(completion, 'choices'):
            choices = completion.choices
            print(f"3. Type of 'choices': {type(choices)}")
            print(f"4. Content of 'choices': {choices}")
            
            if isinstance(choices, list) and len(choices) > 0:
                first = choices
                print(f"5. Type of 'choices': {type(first)}")
                print(f"6. Attributes of 'choices': {dir(first)}")
                
                # message 속성 확인
                if hasattr(first, 'message'):
                    msg = first.message
                    print(f"7. Type of 'choices.message': {type(msg)}")
                    print(f"8. Content of 'choices.message': {msg}")
                else:
                    print("⚠️ 'choices' has no 'message' attribute!")
        else:
            print("⚠️ 'completion' has no 'choices' attribute!")
            # 혹시 딕셔너리인지 확인
            if isinstance(completion, dict):
                print("💡 It is a Dictionary! Keys:", completion.keys())

        print("="*50 + "\n")

    except Exception as e:
        print(f"❌ Error during inspection: {e}")

if __name__ == "__main__":
    inspect_structure()
