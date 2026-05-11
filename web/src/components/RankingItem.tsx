'use client';

import { RankingItemData } from '@/types';
import { TrendingUp, Minus, TrendingDown } from 'lucide-react';

interface RankingItemProps {
  rank: number;
  item: RankingItemData;
}

export default function RankingItem({ rank, item }: RankingItemProps) {
  const getTrendIcon = () => {
    if (rank <= 3) return <TrendingUp size={12} className="text-red-500" />;
    if (rank > 7) return <TrendingDown size={12} className="text-blue-500" />;
    return <Minus size={12} className="text-slate-300" />;
  };

  // 💡 [핵심] 랭킹 데이터를 뉴스 모달이 이해할 수 있는 규격으로 변환해서 던져줍니다.
  const handleOpenModal = () => {
    const modalData = {
      id: item.id,
      title: item.title,
      category: item.category || 'k-culture',
      // ✅ [수정 완료] TypeScript 에러를 일으키던 item.info 제거
      summary: `Current Rank: ${rank}위 | ${item.meta_info || ''}`, 
      // 쇼피(Shopee) 검색이 가능하도록 연예인/작품 이름 자체를 키워드로 넘깁니다.
      amazon_keyword: item.title, 
      score: item.score
    };
    
    // 뉴스 모달 열기 이벤트 호출!
    window.dispatchEvent(new CustomEvent('open-news-modal', { detail: modalData }));
  };

  return (
    // 💡 Link 대신 div를 사용하고 onClick 이벤트를 달아줍니다.
    <div 
      onClick={handleOpenModal}
      className="flex items-center justify-between py-3 border-b border-slate-50 dark:border-slate-800 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50 px-2 rounded-lg transition-colors group cursor-pointer"
    >
      <div className="flex items-center gap-3 overflow-hidden">
        {/* 순위 숫자 */}
        <div className={`
          flex flex-col items-center justify-center w-6 min-w-[24px]
          ${rank <= 3 ? 'text-cyan-600 dark:text-cyan-400 font-black text-lg' : 'text-slate-400 font-bold text-sm'}
        `}>
          {rank}
        </div>

        {/* 텍스트 정보 */}
        <div className="flex flex-col min-w-0">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5 truncate">
            {item.meta_info || item.category}
          </span>
          <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200 truncate group-hover:text-cyan-600 transition-colors">
            {item.title}
          </h4>
        </div>
      </div>

      {/* 우측 점수/아이콘 */}
      <div className="flex flex-col items-end gap-1 pl-2">
        {item.score && (
          <span className="text-[9px] font-mono text-slate-300">
            {item.score.toFixed(0)} pts
          </span>
        )}
        <div className="opacity-50">
          {getTrendIcon()}
        </div>
      </div>
    </div>
  );
}
