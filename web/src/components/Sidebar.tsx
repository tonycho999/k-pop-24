'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase'; // 경로 확인 필요
import KeywordTicker from './KeywordTicker';
import VibeCheck from './VibeCheck';
import RankingItem from './RankingItem';
import { Trophy, Flame, Music, Film, Tv, MapPin } from 'lucide-react';
import { LiveNewsItem, RankingItemData } from '@/types';
'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import KeywordTicker from './KeywordTicker';
import VibeCheck from './VibeCheck';
import RankingItem from './RankingItem';
// 👇 [수정] ThumbsUp 아이콘 추가
import { Trophy, Flame, Music, Film, Tv, MapPin, ThumbsUp } from 'lucide-react';
import { LiveNewsItem, RankingItemData } from '@/types';

interface SidebarProps {
  news: LiveNewsItem[];
  category: string;
}

export default function Sidebar({ news, category }: SidebarProps) {
  const [rankings, setRankings] = useState<RankingItemData[]>([]);
  const [loading, setLoading] = useState(false);

  // 카테고리 변경 시 랭킹 데이터 새로고침
  useEffect(() => {
    const fetchRankings = async () => {
      const targetCategory = category === 'All' ? 'K-Pop' : category;
      
      if (!['K-Pop', 'K-Drama', 'K-Movie', 'K-Entertain', 'K-Culture'].includes(targetCategory)) {
          setRankings([]); 
          return;
      }

      setLoading(true);
      
      const { data, error } = await supabase
        .from('trending_rankings')
        .select('*')
        .eq('category', targetCategory)
        .order('rank', { ascending: true })
        .limit(10);

      if (!error && data) {
        setRankings(data as RankingItemData[]);
      } else {
        setRankings([]);
      }
      setLoading(false);
    };

    fetchRankings();
  }, [category]);

  const getHeaderInfo = () => {
    switch (category) {
      case 'K-Pop': return { title: 'Top 10 Music Chart', icon: <Music size={18} /> };
      case 'K-Drama': return { title: 'Drama & Actors Ranking', icon: <Tv size={18} /> };
      case 'K-Movie': return { title: 'Box Office Top 10', icon: <Film size={18} /> };
      case 'K-Entertain': return { title: 'Variety Show Trends', icon: <Flame size={18} /> };
      case 'K-Culture': return { title: "K-Culture Hot Picks", icon: <MapPin size={18} /> };
      default: return { title: 'Top Voted News', icon: <Trophy size={18} /> };
    }
  };

  const headerInfo = getHeaderInfo();
  
  // 좋아요 순 정렬 (Top 3)
  const topLiked = [...news].sort((a, b) => (b.likes || 0) - (a.likes || 0)).slice(0, 3);

  return (
    <aside className="lg:col-span-4 space-y-6">
      
      {/* 1. 카테고리별 실시간 랭킹 (All 아닐 때만) */}
      {category !== 'All' && (
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
               rankings.map((item) => (
                 <RankingItem key={item.id} rank={item.rank} item={item} />
               ))
            ) : (
               <div className="text-center py-6 text-xs text-slate-400 italic">
                 Ranking data preparing...
               </div>
            )}
          </div>
        </section>
      )}

      {/* 2. Hot Keywords */}
      <KeywordTicker />

      {/* 3. AI Vibe Check */}
      <VibeCheck />
      
      {/* 4. Users' Choice (Top Voted) */}
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
                      <ThumbsUp size={10} /> {m.likes}
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
interface SidebarProps {
  news: LiveNewsItem[];
  category: string;
}

export default function Sidebar({ news, category }: SidebarProps) {
  const [rankings, setRankings] = useState<RankingItemData[]>([]);
  const [loading, setLoading] = useState(false);

  // [중요] 카테고리가 바뀔 때마다 사이드바 랭킹 데이터 새로고침
  useEffect(() => {
    const fetchRankings = async () => {
      // 'All'일 때는 기본적으로 K-Pop을 보여주거나, 비워둘 수 있음
      const targetCategory = category === 'All' ? 'K-Pop' : category;
      
      // 유효한 카테고리인지 검사
      if (!['K-Pop', 'K-Drama', 'K-Movie', 'K-Entertain', 'K-Culture'].includes(targetCategory)) {
          setRankings([]); 
          return;
      }

      setLoading(true);
      
      // trending_rankings 테이블 조회 (새 DB 구조)
      const { data, error } = await supabase
        .from('trending_rankings')
        .select('*')
        .eq('category', targetCategory)
        .order('rank', { ascending: true })
        .limit(10); // Top 10

      if (!error && data) {
        setRankings(data as RankingItemData[]);
      } else {
        console.error("Sidebar Error:", error);
        setRankings([]);
      }
      setLoading(false);
    };

    fetchRankings();
  }, [category]);

  // 카테고리별 아이콘 및 제목 매핑
  const getHeaderInfo = () => {
    switch (category) {
      case 'K-Pop': return { title: 'Top 10 Music Chart', icon: <Music size={18} /> };
      case 'K-Drama': return { title: 'Drama & Actors Ranking', icon: <Tv size={18} /> };
      case 'K-Movie': return { title: 'Box Office Top 10', icon: <Film size={18} /> };
      case 'K-Entertain': return { title: 'Variety Show Trends', icon: <Flame size={18} /> };
      case 'K-Culture': return { title: "K-Culture Hot Picks", icon: <MapPin size={18} /> };
      default: return { title: 'Top Voted News', icon: <Trophy size={18} /> };
    }
  };

  const headerInfo = getHeaderInfo();
  
  // 좋아요 순으로 정렬하여 상위 3개 보여주기 (기존 news 데이터 재활용)
  const topLiked = [...news].sort((a, b) => (b.likes || 0) - (a.likes || 0)).slice(0, 3);

  return (
    <aside className="lg:col-span-4 space-y-6">
      
      {/* 1. 카테고리별 실시간 랭킹 (All이 아닐 때만 표시) */}
      {category !== 'All' && (
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
               rankings.map((item) => (
                 <RankingItem key={item.id} rank={item.rank} item={item} />
               ))
            ) : (
               <div className="text-center py-6 text-xs text-slate-400 italic">
                 Ranking data preparing...
               </div>
            )}
          </div>
        </section>
      )}

      {/* 2. Hot Keywords */}
      <KeywordTicker />

      {/* 3. AI Vibe Check (감성 분석) */}
      <VibeCheck />
      
      {/* 4. Top Voted News (전체 뉴스 중 좋아요 Top 3) */}
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
                      <ThumbsUp size={10} /> {m.likes}
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
