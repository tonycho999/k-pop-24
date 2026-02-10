'use client';
import { useState, useEffect } from 'react';

export default function KeywordTicker({ keywords }: { keywords: string[] }) {
  const [index, setIndex] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  // 2초마다 순위 바뀌는 효과
  useEffect(() => {
    if (isOpen) return;
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % keywords.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [keywords.length, isOpen]);

  return (
    <div className="relative max-w-2xl mx-auto mb-12 z-20">
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="cursor-pointer bg-gray-900/80 border border-gray-700 rounded-lg px-4 py-2 flex items-center justify-between hover:border-pink-500 transition-all shadow-[0_0_10px_rgba(0,0,0,0.5)]"
      >
        <div className="flex items-center gap-3">
          <span className="text-pink-500 font-bold italic">HOT 🔥</span>
          <span className="text-white text-sm animate-fade-in-up">
            <span className="text-gray-500 mr-2">{index + 1}.</span>
            {keywords[index]}
          </span>
        </div>
        <span className="text-xs text-gray-500">▼</span>
      </div>

      {/* 클릭하면 10위까지 펼쳐지는 메뉴 */}
      {isOpen && (
        <div className="absolute top-full left-0 w-full mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
          {keywords.map((k, i) => (
            <div key={i} className="px-4 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-white flex justify-between border-b border-gray-800 last:border-0">
              <span><span className="text-pink-600 font-bold mr-2">{i + 1}</span> {k}</span>
              {i < 3 && <span className="text-xs text-red-400 font-bold">UP ▲</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
