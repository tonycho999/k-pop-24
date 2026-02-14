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
  const [loading, setLoading] = useState(true);

  // 1. 랭킹 데이터 가져오기
  useEffect(() => {
    const fetchRankings = async () => {
      setLoading(true);
      try {
        let data: RankingItemData[] | null = null;
        
        // ✅ [핵심 수정] DB 요청용 카테고리 이름 변환
        // 화면에서는 'K-Entertain'을 쓰지만, DB에는 'K-Variety'로 저장되어 있음
        let dbCategory = category;
        if (category === 'K-Entertain') {
            dbCategory = 'K-Variety';
        }

        // 테이블 이름: live_rankings
        if (category === 'All') {
          const { data: trendingData, error } = await supabase
            .from('live_rankings') 
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
          const { data: categoryData, error } = await supabase
            .from('live_rankings')
            .select('*')
            .eq('category', dbCategory) // ✅ 변환된 이름(K-Variety)으로 조회
            .order('rank', { ascending: true })
            .limit(10);
            
          if (error) throw error;
          data = categoryData as RankingItemData[];
        }

        setRankings(data || []);
      } catch (error) {
        console.error("Sidebar Ranking Fetch Error:", error);
        setRankings([]);
      } finally {
        setLoading(false);
      }
    };

    fetchRankings();
  }, [category]);

  // 2. 헤더 정보 설정
  const headerInfo = useMemo(() => {
    switch (category) {
      case 'K-Pop': return { title: 'Top 10 Music Chart', icon: <Music size={18} /> };
      case 'K-Drama': return { title: 'Drama Ranking', icon: <Tv size={18} /> }; 
      case 'K-Movie': return { title: 'Box Office Top 10', icon: <Film size={18} /> };
      // 화면 표시용 이름은 K-Entertain 유지
      case 'K-Entertain': return { title: 'Variety Show Trends', icon: <Flame size={18} /> };
      case 'K-Culture': return { title: "K-Culture Hot Picks", icon: <MapPin size={18} /> };
      default: return { title: 'Total Trend Ranking', icon: <TrendingUp size={18} /> };
    }
  }, [category]);

  // 3. 좋아요 Top 3
  const topLiked = useMemo(() => {
      if (!news || news.length === 0) return [];
      return [...news]
        .sort((a, b) => (b.likes || 0) - (a.likes || 0))
        .slice(0, 3);
  }, [news]);

  return (
    <aside className="lg:col-span-1 space-y-6 w-full">
      
      {/* 1. 실시간 랭킹 섹션 */}
      <section className="bg-white dark:bg-slate-900 rounded-[32px] p-6 border border-slate-100 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-2 mb-4 text-cyan-600 dark:text-cyan-400 border-b border-slate-50 dark:border-slate-800 pb-3">
          {headerInfo.icon}
          <h3 className="font-black uppercase tracking-wider text-sm">
            {headerInfo.title}
          </h3>
        </div>
        
        <div className="space-y-1">
          {loading ? (
              <div className="text-center py-8 text-xs text-slate-400 animate-pulse">
                Updating Charts...
              </div>
          ) : rankings.length > 0 ? (
              rankings.map((item, index) => (
                <RankingItem 
                    key={item.id || `rank-${index}-${item.title}`} 
                    rank={item.rank} 
                    item={item} 
                />
              ))
          ) : (
              <div className="text-center py-8">
                <p className="text-xs text-slate-400 italic mb-2">Ranking data preparing...</p>
                <p className="text-[10px] text-slate-300">Run scraper to fetch data</p>
              </div>
          )}
        </div>
      </section>

      {/* 2. 부가 기능 */}
      <KeywordTicker />
      <VibeCheck />
      
      {/* 3. 유저 초이스 */}
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
              <div key={m.id || idx} className="group cursor-pointer border-b border-slate-50 dark:border-slate-800 pb-3 last:border-0 last:pb-0 hover:pl-2 transition-all duration-300">
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
