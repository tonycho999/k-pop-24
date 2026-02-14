# scraper/main.py
import os
import sys
from datetime import datetime
import config
import processor

def get_category_by_time():
    """
    현재 시간을 기준으로 카테고리를 수학적으로 계산해서 선택
    (DB에 상태를 저장하지 않아도 순서대로 돌아가게 함)
    """
    # 현재 시간 (UTC 기준)
    now = datetime.utcnow()
    
    # 로직: (시간 * 2) + (30분 이상이면 1, 아니면 0)
    # 예: 1시 12분 -> 인덱스 2 / 1시 42분 -> 인덱스 3
    # 이렇게 하면 매 실행마다 인덱스가 1씩 증가함
    time_slot_index = (now.hour * 2) + (1 if now.minute >= 30 else 0)
    
    # 전체 카테고리 개수로 나눈 나머지 (0 ~ 4 순환)
    category_idx = time_slot_index % len(config.CATEGORY_ORDER)
    
    return config.CATEGORY_ORDER[category_idx]

def main():
    print(f"🤖 GitHub Action Scraper Started at {datetime.now()} (UTC)")
    
    # 1. 시간 기반으로 카테고리 자동 선택
    target_category = get_category_by_time()
    
    # 2. 로직 실행 (1회만 실행하고 바로 종료됨 -> 이게 깃허브 액션 방식)
    try:
        processor.run_category_process(target_category)
        print("✅ Job finished successfully.")
    except Exception as e:
        print(f"🚨 Job Failed: {e}")
        sys.exit(1) # 에러 나면 깃허브에 빨간불 띄우기

if __name__ == "__main__":
    main()
