'use client';
import { motion } from 'framer-motion';
import { Zap } from 'lucide-react';

interface InsightBannerProps {
  insight?: string;
}

export default function InsightBanner({ insight }: InsightBannerProps) {
  // 기본 문구 설정
  const content = insight || "Analyzing global K-Entertainment trends in real-time... ⚡️ Breaking News & Viral Rankings";

  return (
    // ✅ [수정 1] 배경색을 투명도(opacity) 대신 고정 색상으로 변경하여 라벨과의 이질감 제거
    <div className="mt-1 mb-2 px-1 py-1 bg-cyan-50 dark:bg-slate-900 border border-cyan-100 dark:border-slate-800 rounded-2xl flex items-center gap-0 overflow-hidden shadow-sm relative">
      
      {/* ✅ [수정 2] 고정 라벨 디자인 강화 (그림자 추가로 텍스트 위로 떠있는 느낌) */}
      <div className="flex items-center gap-2 bg-cyan-100 dark:bg-slate-800 px-3 py-1.5 rounded-xl z-20 shadow-md mr-2 shrink-0">
        <Zap className="text-yellow-500 w-4 h-4 animate-pulse fill-yellow-500" />
        <span className="text-cyan-700 dark:text-cyan-400 uppercase font-black text-[11px] tracking-widest whitespace-nowrap">
          Insight
        </span>
      </div>

      {/* 흐르는 텍스트 영역 */}
      <div className="flex-1 overflow-hidden relative flex items-center h-full mask-linear-fade">
        <motion.div
          // ✅ [수정 3] 시작 위치와 끝 위치를 조정하여 더 자연스러운 흐름
          initial={{ x: "100%" }}
          animate={{ x: "-100%" }}
          transition={{
            repeat: Infinity,
            duration: 20, // 속도를 조금 더 천천히 (가독성 확보)
            ease: "linear",
          }}
          className="whitespace-nowrap text-sm font-bold text-slate-600 dark:text-slate-400 flex items-center"
        >
          {content}
          {/* 반복되는 느낌을 주기 위해 뒤에 동일 문구 희미하게 추가 (선택사항) */}
          <span className="opacity-50 mx-8"> | </span> 
          <span className="opacity-50">{content}</span>
        </motion.div>
        
        {/* 오른쪽 끝 페이드 아웃 효과 (텍스트가 자연스럽게 사라짐) */}
        <div className="absolute right-0 top-0 w-8 h-full bg-gradient-to-l from-cyan-50 dark:from-slate-900 to-transparent z-10"></div>
      </div>
    </div>
  );
}
