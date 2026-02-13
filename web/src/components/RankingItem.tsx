'use client';

import { RankingItemData } from '@/types';
import { Minus, ArrowUp, ArrowDown } from 'lucide-react';

interface Props {
  rank: number;
  item: RankingItemData;
}

export default function RankingItem({ rank, item }: Props) {
  
  // 순위 변동 아이콘 로직
  const getDeltaIcon = (delta: string) => {
    if (delta === 'NEW') return <span className="text-[8px] font-black text-red-500 bg-red-50 px-1 rounded">NEW</span>;
    if (delta.includes('▲')) return <span className="text-[9px] text-red-500 flex items-center"><ArrowUp size={8}/>{delta.replace('▲', '')}</span>;
    if (delta.includes('▼')) return <span className="text-[9px] text-blue-500 flex items-center"><ArrowDown size={8}/>{delta.replace('▼', '')}</span>;
    return <Minus size={10} className="text-slate-300" />;
  };

  return (
    <div className="flex items-center gap-3 py-2 px-2 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer group">
      {/* 순위 */}
      <div className="w-6 text-center font-black text-slate-300 group-hover:text-cyan-500 italic">
        {rank}
      </div>

      {/* 썸네일 (작은 원형) */}
      <div className="w-8 h-8 rounded-full bg-slate-100 overflow-hidden flex-shrink-0 border border-slate-100 dark:border-slate-700">
        <img 
          src={item.image_url || `https://placehold.co/50x50?text=${rank}`} 
          className="w-full h-full object-cover" 
          alt="" 
        />
      </div>

      {/* 텍스트 정보 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <p className="text-sm font-bold text-slate-700 dark:text-slate-300 line-clamp-1">
            {item.keyword}
          </p>
          <div className="pl-2">
            {getDeltaIcon(item.delta)}
          </div>
        </div>
      </div>
    </div>
  );
}
