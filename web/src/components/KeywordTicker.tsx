// web/src/components/KeywordTicker.tsx
'use client';

import { useState, useEffect } from 'react';

// 임시 데이터 (나중에 API와 연동 가능)
const TRENDING_KEYWORDS = [
  "1. BTS Jin", "2. NewJeans", "3. SEVENTEEN", "4. BLACKPINK Lisa", "5. Stray Kids",
  "6. IVE", "7. LE SSERAFIM", "8. TWICE", "9. EXO", "10. SHINee"
];

export default function KeywordTicker() {
  const [index, setIndex] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  // 2초마다 순위 변경 (티커 효과)
  useEffect(() => {
    if (isOpen) return; // 펼쳐져 있으면 롤링 멈춤
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % TRENDING_KEYWORDS.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [isOpen]);

  return (
    <div className="w-full max-w-md mx-auto mb-6 relative z-50">
      {/* 티커 메인 영역 */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="cursor-pointer bg-black/80 border border-green-400/50 shadow-[0_0_10px_#4ade80] rounded-full px-4 py-2 flex items-center justify-between transition-all hover:bg-black"
      >
        <span className="text-xs text-green-400 font-bold mr-2">LIVE TRENDING</span>
        <div className="flex-1 h-6 overflow-hidden relative">
            <div 
                key={index}
                className="animate-slideUp text-white font-medium text-sm absolute w-full"
            >
                {TRENDING_KEYWORDS[index]}
            </div>
        </div>
        <span className="text-gray-400 text-xs">▼</span>
      </div>

      {/* 펼쳐졌을 때 보이는 리스트 (Dropdown) */}
      {isOpen && (
        <div className="absolute top-12 left-0 w-full bg-black/95 border border-green-500 rounded-xl p-4 shadow-[0_0_20px_#4ade80] flex flex-col gap-2">
          <div className="text-xs text-gray-400 mb-2 pb-2 border-b border-gray-800">
            Real-time K-POP Issues
          </div>
          {TRENDING_KEYWORDS.map((keyword, idx) => (
            <div key={idx} className="text-white text-sm hover:text-green-400 cursor-pointer transition-colors">
              {keyword}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
