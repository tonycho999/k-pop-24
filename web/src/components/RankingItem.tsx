'use client';

import { RankingItemData } from '@/types';
import { TrendingUp, Minus, TrendingDown } from 'lucide-react';
import Link from 'next/link'; // ✅ Link 컴포넌트 추가

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

  return (
    // ✅ div 대신 Link를 사용하여 고유 URL(/ranking/아이디)을 부여합니다.
    <Link 
      href={`/ranking/${item.id}`} 
      className="flex items-center justify-between py-3 border-b border-slate-50 dark:border-slate-800 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50 px-2 rounded-lg transition-colors group cursor-pointer"
    >
      <div className="flex items-center gap-3 overflow-hidden">
        <div className={`
          flex flex-col items-center justify-center w-6 min-w-[24px]
          ${rank <= 3 ? 'text-cyan-600 dark:text-cyan-400 font-black text-lg' : 'text-slate-400 font-bold text-sm'}
        `}>
          {rank}
        </div>

        <div className="flex flex-col min-w-0">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5 truncate">
            {item.meta_info || item.category}
          </span>
          <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200 truncate group-hover:text-cyan-600 transition-colors">
            {item.title}
          </h4>
        </div>
      </div>

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
    </Link>
  );
}
