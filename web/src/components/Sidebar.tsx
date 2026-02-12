'use client';

import HotKeywords from './HotKeywords';
import VibeCheck from './VibeCheck';
import { Trophy } from 'lucide-react';

interface SidebarProps {
  news: any[];
}

export default function Sidebar({ news }: SidebarProps) {
  // 전체 뉴스 중 좋아요 순위 TOP 3 추출
  const topLiked = [...news]
    .sort((a, b) => (b.likes || 0) - (a.likes || 0))
    .slice(0, 3);

  return (
    <aside className="lg:col-span-4 space-y-6">
      {/* 1. 실시간 급상승 키워드 */}
      <HotKeywords />

      {/* 2. AI 감성 분석 (Vibe Check) */}
      <VibeCheck />
      
      {/* 3. 명예의 전당 (Top Voted) */}
      <section className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-6 text-cyan-500">
          <Trophy size={20} className="fill-current" />
          <h3 className="font-black text-slate-800 uppercase tracking-wider text-sm">
            Top Voted News
          </h3>
        </div>
        
        <div className="space-y-5">
          {topLiked.length > 0 ? (
            topLiked.map((m, idx) => (
              <div key={m.id} className="group cursor-pointer border-b border-slate-50 pb-4 last:border-0 last:pb-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-black text-slate-300 uppercase">Top 0{idx + 1}</span>
                  <span className="text-[10px] font-bold text-cyan-500 uppercase">{m.category}</span>
                </div>
                <p className="text-sm font-bold text-slate-700 line-clamp-2 group-hover:text-cyan-500 transition-colors mb-2">
                  {m.title}
                </p>
                <div className="flex items-center gap-3">
                   <span className="text-[11px] font-black text-cyan-400 bg-cyan-50 px-2 py-0.5 rounded-md">
                     👍 {m.likes} Likes
                   </span>
                   <span className="text-[11px] font-bold text-slate-400">
                     Score {m.score}
                   </span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-400 text-center py-4 italic">No votes yet...</p>
          )}
        </div>
      </section>
    </aside>
  );
}
