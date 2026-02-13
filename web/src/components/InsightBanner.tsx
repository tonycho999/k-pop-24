'use client';
import { Zap } from 'lucide-react';

export default function InsightBanner({ insight }: { insight?: string }) {
  return (
    // [수정] 
    // 1. mb-8 -> mb-2 (아래 여백 대폭 감소)
    // 2. mt-1 (위 여백 최소화)
    // 3. py-3 -> py-2 (박스 높이 축소)
    <div className="mt-1 mb-2 px-6 py-2 bg-cyan-50 border border-cyan-100 rounded-2xl flex items-center gap-3">
      <Zap className="text-yellow-500 w-5 h-5 flex-shrink-0" />
      <p className="text-sm font-bold text-slate-700 italic leading-none">
        <span className="text-cyan-600 uppercase mr-2 font-black tracking-wider">AI Insight:</span>
        {insight || "Analyzing global K-Entertainment trends in real-time..."}
      </p>
    </div>
  );
}
