'use client';

import { Trophy, TrendingUp, MapPin, Music, Film, Tv } from 'lucide-react';

interface RankingItemProps {
  rank: number;
  item: any;
}

export default function RankingItem({ rank, item }: RankingItemProps) {
  // 순위에 따른 아이콘 및 색상 설정
  const getRankIcon = (r: number) => {
    if (r === 1) return <Trophy size={14} className="text-yellow-500 fill-yellow-500" />;
    if (r === 2) return <span className="text-slate-400 font-black">2</span>;
    if (r === 3) return <span className="text-orange-400 font-black">3</span>;
    return <span className="text-slate-300 font-bold">{r}</span>;
  };

  return (
    <a 
      href={item.link_url || '#'} 
      target="_blank" 
      rel="noopener noreferrer"
      className="flex items-center gap-4 py-3 border-b border-slate-50 last:border-0 hover:bg-slate-50/50 rounded-xl px-2 transition-colors group"
    >
      {/* 순위 표시 */}
      <div className={`
        flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg
        ${rank === 1 ? 'bg-yellow-50 shadow-sm' : 'bg-transparent'}
      `}>
        {getRankIcon(rank)}
      </div>

      {/* 썸네일 (있으면 표시) */}
      {item.image_url && (
        <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 border border-slate-100">
          <img src={item.image_url} alt={item.title} className="w-full h-full object-cover" />
        </div>
      )}

      {/* 내용 */}
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-bold text-slate-700 truncate group-hover:text-cyan-600 transition-colors">
          {item.title}
        </h4>
        {item.sub_title && (
          <p className="text-xs text-slate-400 truncate flex items-center gap-1">
             {item.category === 'K-Culture' && <MapPin size={10} />}
             {item.sub_title}
          </p>
        )}
      </div>

      {/* 화살표 아이콘 (호버 시 등장) */}
      <div className="opacity-0 group-hover:opacity-100 transition-opacity">
        <TrendingUp size={14} className="text-cyan-400" />
      </div>
    </a>
  );
}
