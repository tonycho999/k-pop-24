'use client';

import { useEffect, useState, useMemo } from 'react';
import { supabase } from '@/lib/supabase';
import KeywordTicker from './KeywordTicker';
import VibeCheck from './VibeCheck';
import RankingItem from './RankingItem';
import { Trophy, Flame, Music, Film, Tv, MapPin, ThumbsUp, TrendingUp } from 'lucide-react';
import { LiveNewsItem, RankingItemData } from '@/types';

interface SidebarProps {
  news: LiveNewsItem[];
  category: string;
}

export default function Sidebar({ news, category }: SidebarProps) {
  const [rankings, setRankings] = useState<RankingItemData[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchRankings = async () => {
      setLoading(true);
      try {
        let data: RankingItemData[] | null = null;

        // ✅ [수정] 테이블 이름을 'live_rankings'로 통일
        if (category === 'All') {
          const { data: trendingData, error } = await supabase
            .from('live_rankings')  // <-- 여기 수정됨
            .select('*')
            .order('score', { ascending: false })
            .limit(10);
          
          if (error) throw error;
          if (trendingData) {
            data = trendingData.map((item, index) => ({
              ...item,
              rank: index + 1
            })) as RankingItemData[];
          }
        } else {
          const targetCategory = category.toLowerCase();
          const { data: categoryData, error } = await supabase
            .from('live_rankings')  // <-- 여기 수정됨
            .select('*')
            .eq('category', targetCategory)
            .order('rank', { ascending: true })
            .limit(10);
            
          if (error) throw error;
          data = categoryData as RankingItemData[];
        }

        setRankings(data || []);
      } catch (error) {
        console.error("Sidebar Error:", error);
        setRankings([]);
      } finally {
        setLoading(false);
      }
    };

    fetchRankings();
  }, [category]);

  const headerInfo = useMemo(() => {
    switch (category) {
      case 'K-Pop': return { title: 'Top 10 Music Chart', icon: <Music size={18} /> };
      case 'K-Drama': return { title: 'Drama Ranking', icon: <Tv size={18} /> }; 
      case 'K-Movie': return { title: 'Box Office Top 10', icon: <Film size={18} /> };
      case 'K-Entertain': return { title: 'Variety Show Trends', icon: <Flame size={18} /> };
      case 'K-Culture': return { title: "K-Culture Hot Picks", icon: <MapPin size={18} /> };
      default: return { title: 'Total Trend Ranking', icon: <TrendingUp size={18} /> };
    }
  }, [category]);

  const topLiked = useMemo(() => {
      if (!news) return [];
      return [...news]
        .sort((a, b) => (b.likes || 0) - (a.likes || 0))
        .slice(0, 3);
  }, [news]);

  return (
    <aside className="lg:col-span-1 space-y-6">
      <section className="bg-white dark:bg-slate-900 rounded-[32px] p-6 border border-slate-100 dark:border-slate-800 shadow-sm animate-in fade-in slide-in-from-right-4 duration-500">
        <div className="flex items-center gap-2 mb-4 text-cyan-600 dark:text-cyan-400 border-b border-slate-50 dark:border-slate-800 pb-3">
          {headerInfo.icon}
          <h3 className="font-black uppercase tracking-wider text-sm">
            {headerInfo.title}
          </h3>
        </div>
        
        <div className="space-y-1">
          {loading ? (
              <div className="text-center py-8 text-xs text-slate-400 animate-pulse">Update Charts...</div>
          ) : rankings.length > 0 ? (
              rankings.map((item, index) => (
                <RankingItem 
                    key={item.id || `${item.category}-${item.rank}-${index}`} 
                    rank={item.rank} 
                    item={item} 
                />
              ))
          ) : (
              <div className="text-center py-6 text-xs text-slate-400 italic">
                Ranking data preparing...
              </div>
          )}
        </div>
      </section>

      <KeywordTicker />
      <VibeCheck />
      
      <section className="bg-white dark:bg-slate-900 rounded-[32px] p-6 border border-slate-100 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-2 mb-6 text-cyan-500">
          <Trophy size={18} className="fill-current" />
          <h3 className="font-black text-slate-800 dark:text-slate-200 uppercase tracking-wider text-sm">
            Users' Choice
          </h3>
        </div>
        
        <div className="space-y-4">
          {topLiked.length > 0 ? (
            topLiked.map((m, idx) => (
              <div key={m.id} className="group cursor-pointer border-b border-slate-50 dark:border-slate-800 pb-3 last:border-0 last:pb-0 hover:pl-2 transition-all duration-300">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-black text-slate-300 uppercase">#{idx + 1}</span>
                  <span className="text-[10px] font-bold text-cyan-500 uppercase">{m.category}</span>
                </div>
                <p className="text-sm font-bold text-slate-700 dark:text-slate-300 line-clamp-2 group-hover:text-cyan-500 transition-colors mb-2">
                  {m.title}
                </p>
                <div className="flex items-center gap-3">
                    <span className="text-[10px] font-black text-cyan-600 bg-cyan-50 dark:bg-cyan-900/30 px-2 py-0.5 rounded-md flex items-center gap-1">
                      <ThumbsUp size={10} /> {m.likes || 0}
                    </span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-400 text-center py-4 italic">No votes yet.</p>
          )}
        </div>
      </section>
    </aside>
  );
}
