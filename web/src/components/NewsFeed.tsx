'use client';

import { motion } from 'framer-motion';
import { Star, ThumbsUp, ThumbsDown, Share2 } from 'lucide-react';

interface NewsFeedProps {
  news: any[];
  loading: boolean;
  onOpen: (article: any) => void;
}

export default function NewsFeed({ news, loading, onOpen }: NewsFeedProps) {
  // 1. 공유 핸들러 함수 정의
  const handleShare = async (e: React.MouseEvent, title: string, url: string) => {
    e.stopPropagation(); // 카드가 클릭되어 모달이 뜨는 것을 방지
    try {
      if (navigator.share) {
        // 모바일 등 네이티브 공유 지원 시
        await navigator.share({
          title: title,
          text: `Check out this news: ${title}`,
          url: url,
        });
      } else {
        // PC 등 미지원 시 클립보드 복사
        await navigator.clipboard.writeText(url);
        alert('Link copied to clipboard!');
      }
    } catch (err) {
      console.error('Error sharing:', err);
    }
  };

  if (loading) {
    return (
      <div className="lg:col-span-8 h-96 flex items-center justify-center text-slate-300 font-black tracking-[1em]">
        LOADING...
      </div>
    );
  }

  return (
    <div className="lg:col-span-8">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {news.map((item, index) => {
          // 카테고리 내 독립 순위 계산
          const displayRank = index + 1;
          const isHero = displayRank <= 2;
          const isGrid = displayRank > 2 && displayRank <= 6;
          
          // 디자인 클래스 설정 (다크모드 지원 클래스 dark: 추가)
          const cardClass = isHero 
            ? "md:col-span-2 aspect-[4/3] relative overflow-hidden group shadow-xl hover:shadow-2xl" 
            : isGrid 
              ? "md:col-span-1 aspect-square relative overflow-hidden group shadow-md hover:shadow-xl"
              : "md:col-span-4 bg-white dark:bg-slate-900 p-4 flex items-center gap-4 rounded-3xl border border-slate-100 dark:border-slate-800 hover:border-cyan-300 transition-all shadow-sm";

          // 1. Hero & Grid Style (Rank 1~6)
          if (isHero || isGrid) {
            return (
              <motion.div
                key={item.id}
                layoutId={item.id}
                onClick={() => onOpen(item)}
                className={`${cardClass} rounded-[32px] cursor-pointer bg-slate-900 transition-all duration-500`}
              >
                <img 
                  src={item.image_url || `https://placehold.co/800x600/111/cyan?text=${item.category}`} 
                  className="absolute inset-0 w-full h-full object-cover opacity-60 group-hover:opacity-80 group-hover:scale-105 transition-all duration-700" 
                  alt={item.title} 
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent p-6 flex flex-col justify-end">
                  <div className="flex justify-between items-start mb-2">
                    <span className="px-3 py-1 bg-white/20 backdrop-blur-md rounded-lg text-[10px] font-black text-white uppercase border border-white/20">
                      #{displayRank} {item.category}
                    </span>
                    <span className="px-2 py-1 bg-cyan-400 rounded-lg text-[10px] font-black text-white uppercase shadow-lg">
                      Score {item.score}
                    </span>
                  </div>
                  <h2 className={`${isHero ? 'text-2xl' : 'text-lg'} font-bold text-white leading-tight mb-2 line-clamp-2`}>
                    {item.title}
                  </h2>
                  {isHero && <p className="text-sm text-slate-300 line-clamp-2 mb-4 opacity-80">{item.summary}</p>}
                  <div className="flex justify-between items-end mt-2">
                     <div className="flex gap-4">
                        <span className="flex items-center gap-1 text-xs font-bold text-cyan-400"><ThumbsUp size={14}/> {item.likes}</span>
                        <span className="text-xs font-bold text-pink-400 flex items-center gap-1"><ThumbsDown size={14}/> {item.dislikes}</span>
                     </div>
                     {/* Hero/Grid에도 공유 버튼 추가 (선택 사항, 필요 없으면 삭제 가능) */}
                     <button 
                        onClick={(e) => handleShare(e, item.title, item.link)}
                        className="p-2 bg-white/10 hover:bg-white/30 rounded-full text-white transition-colors backdrop-blur-sm"
                     >
                        <Share2 size={16} />
                     </button>
                  </div>
                </div>
              </motion.div>
            );
          }

          // 2. List Style (Rank 7+)
          return (
            <motion.div
              key={item.id}
              onClick={() => onOpen(item)}
              className={`${cardClass} cursor-pointer group`}
            >
              <div className="w-20 h-20 rounded-2xl bg-slate-100 overflow-hidden flex-shrink-0 relative text-center">
                <img 
                  src={item.image_url || `https://placehold.co/100x100?text=${item.category}`} 
                  className="w-full h-full object-cover" 
                  alt="" 
                />
                <div className="absolute top-0 left-0 bg-black/50 text-white text-[8px] font-bold px-1.5 py-0.5 rounded-br-lg">
                  #{displayRank}
                </div>
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-black text-cyan-500 uppercase">{item.category}</span>
                  {/* 시간 표시 안전하게 수정 (Date 객체 변환) */}
                  <span className="text-[10px] text-slate-400">
                    • {new Date(item.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </span>
                </div>
                <h3 className="font-bold text-slate-800 dark:text-slate-200 line-clamp-1 group-hover:text-cyan-500 transition-colors">
                  {item.title}
                </h3>
                <p className="text-xs text-slate-500 line-clamp-1">{item.summary}</p>
              </div>

              <div className="flex flex-col items-end gap-2 pr-2">
                <span className="text-xs font-black text-yellow-500">★ {item.score}</span>
                
                <div className="flex gap-3 text-[10px] font-bold text-slate-400 items-center">
                  <span className="flex items-center gap-0.5"><ThumbsUp size={10}/> {item.likes}</span>
                  <span className="flex items-center gap-0.5"><ThumbsDown size={10}/> {item.dislikes}</span>
                  
                  {/* [추가] 공유 버튼 */}
                  <button 
                    onClick={(e) => handleShare(e, item.title, item.link)}
                    className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full text-slate-400 hover:text-cyan-500 transition-colors"
                    title="Share"
                  >
                    <Share2 size={14} />
                  </button>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
