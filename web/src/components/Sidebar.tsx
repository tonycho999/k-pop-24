'use client';
import HotKeywords from './HotKeywords';
import VibeCheck from './VibeCheck';
import { Trophy } from 'lucide-react';

export default function Sidebar({ news }: { news: any[] }) {
  const topLiked = [...news].sort((a, b) => b.likes - a.likes).slice(0, 3);

  return (
    <aside className="lg:col-span-4 space-y-6">
      <HotKeywords />
      <VibeCheck />
      
      <section className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-4 text-cyan-500">
          <Trophy size={18} />
          <h3 className="font-black text-slate-800 uppercase tracking-wider text-sm">Top Voted</h3>
        </div>
        <div className="space-y-4">
          {topLiked.map(m => (
            <div key={m.id} className="group cursor-pointer border-b border-slate-50 pb-2 last:border-0">
              <p className="text-xs font-bold text-slate-700 line-clamp-2 group-hover:text-cyan-500 transition-colors mb-1">{m.title}</p>
              <span className="text-[10px] font-black text-cyan-400">👍 {m.likes} Likes</span>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}
