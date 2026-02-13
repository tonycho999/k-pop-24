'use client';
import { motion } from 'framer-motion';
import { Zap } from 'lucide-react';

export default function InsightBanner({ insight }: { insight?: string }) {
  const content = insight || "Analyzing global K-Entertainment trends in real-time...";

  return (
    <div className="mt-1 mb-2 px-4 py-2 bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-100 dark:border-cyan-800 rounded-2xl flex items-center gap-3 overflow-hidden shadow-sm">
      {/* 고정된 레이블 */}
      <div className="flex items-center gap-2 bg-cyan-50 dark:bg-slate-900 z-10 pr-2">
        <Zap className="text-yellow-500 w-5 h-5 animate-pulse" fill="currentColor" />
        <span className="text-cyan-600 dark:text-cyan-400 uppercase font-black text-xs tracking-wider whitespace-nowrap">
          AI Insight:
        </span>
      </div>

      {/* 흐르는 텍스트 영역 */}
      <div className="flex-1 overflow-hidden relative">
        <motion.div
          initial={{ x: "100%" }}
          animate={{ x: "-100%" }}
          transition={{
            repeat: Infinity,
            duration: 15, // 속도 조절 (숫자가 높을수록 느림)
            ease: "linear",
          }}
          className="whitespace-nowrap text-sm font-bold text-slate-600 dark:text-slate-400"
        >
          {content}
        </motion.div>
      </div>
    </div>
  );
}
