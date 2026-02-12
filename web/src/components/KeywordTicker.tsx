'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase'; // 공용 인스턴스 사용
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, TrendingUp } from 'lucide-react';

export default function KeywordTicker() {
  const [keywords, setKeywords] = useState<string[]>([]);
  const [index, setIndex] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTrendingTitles = async () => {
      // live_news 테이블에서 상위 10개 기사 제목만 가져옴
      const { data, error } = await supabase
        .from('live_news')
        .select('title')
        .order('rank', { ascending: true })
        .limit(10);

      if (data && !error) {
        // 제목 앞에 순위를 붙여서 저장
        const formatted = data.map((item, i) => `${i + 1}. ${item.title}`);
        setKeywords(formatted);
      }
      setLoading(false);
    };

    fetchTrendingTitles();
  }, []);

  // 3초마다 순위 롤링
  useEffect(() => {
    if (isOpen || keywords.length === 0) return; 
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % keywords.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [isOpen, keywords]);

  if (loading) return <div className="h-10 animate-pulse bg-slate-100 rounded-2xl mb-6" />;

  return (
    <div className="w-full max-w-md mx-auto mb-6 relative z-[60]">
      {/* 티커 메인 영역 */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="cursor-pointer bg-white border border-slate-100 shadow-sm rounded-2xl px-5 py-3 flex items-center justify-between transition-all hover:border-cyan-200 active:scale-[0.98]"
      >
        <div className="flex items-center gap-3 flex-1 overflow-hidden">
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-cyan-50 rounded-lg">
            <TrendingUp size={14} className="text-cyan-500" />
            <span className="text-[10px] text-cyan-600 font-black uppercase tracking-tighter">Live</span>
          </div>
          
          <div className="flex-1 h-5 overflow-hidden relative">
            <AnimatePresence mode="wait">
              <motion.div 
                key={index}
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -20, opacity: 0 }}
                transition={{ duration: 0.5, ease: "circOut" }}
                className="text-slate-700 font-bold text-sm absolute w-full truncate"
              >
                {keywords[index] || "Gathering news..."}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
        
        <ChevronDown 
          size={16} 
          className={`text-slate-300 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} 
        />
      </div>

      {/* 펼쳐졌을 때 보이는 리스트 (Dropdown) */}
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-14 left-0 w-full bg-white/95 backdrop-blur-xl border border-slate-100 rounded-3xl p-5 shadow-xl shadow-slate-200/50 flex flex-col gap-1"
          >
            <div className="text-[10px] font-black text-slate-400 mb-3 px-1 flex justify-between uppercase tracking-widest">
              <span>Current Hot Topics</span>
              <span className="text-cyan-500 font-bold">LIVE</span>
            </div>
            
            <div className="grid grid-cols-1 gap-1">
              {keywords.map((keyword, idx) => (
                <div 
                  key={idx} 
                  className="group flex items-center justify-between p-2 rounded-xl hover:bg-cyan-50 transition-all cursor-pointer"
                >
                  <span className={`text-sm font-bold ${idx < 3 ? 'text-slate-800' : 'text-slate-500'} group-hover:text-cyan-600 truncate mr-2`}>
                    {keyword}
                  </span>
                  {idx < 3 && (
                    <span className="text-[10px] font-black text-orange-400 bg-orange-50 px-1.5 py-0.5 rounded-md flex-shrink-0">HOT</span>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
