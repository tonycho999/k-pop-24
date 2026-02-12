'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Star, ThumbsUp, ThumbsDown, X, TrendingUp, Activity, Trophy } from 'lucide-react';

// 1. 카테고리 정의
const CATEGORIES = [
  { label: 'All', value: 'All' },
  { label: 'K-POP', value: 'k-pop' },
  { label: 'K-Drama', value: 'k-drama' },
  { label: 'K-Movie', value: 'k-movie' },
  { label: 'k-Entertain', value: 'k-entertain' },
  { label: 'K-Culture', value: 'k-culture' }
];

export default function Home() {
  const [news, setNews] = useState<any[]>([]);
  const [category, setCategory] = useState('All');
  const [selectedArticle, setSelectedArticle] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNews();
  }, []);

  // 뉴스 데이터 가져오기 (AI 랭킹순)
  const fetchNews = async () => {
    setLoading(true);
    const { data } = await supabase
      .from('live_news')
      .select('*')
      .order('rank', { ascending: true });
    if (data) setNews(data);
    setLoading(false);
  };

  // 좋아요/싫어요 투표 (RPC 호출)
  const handleVote = async (id: string, type: 'likes' | 'dislikes', e?: React.MouseEvent) => {
    if (e) e.stopPropagation(); 
    await supabase.rpc('increment_vote', { row_id: id, col_name: type });
    
    // 로컬 상태 즉시 업데이트 (사용자 경험 향상)
    setNews(prev => prev.map(item => 
      item.id === id ? { ...item, [type]: item[type] + 1 } : item
    ));
    if (selectedArticle?.id === id) {
      setSelectedArticle((prev: any) => ({ ...prev, [type]: prev[type] + 1 }));
    }
  };

  // 필터링 및 사이드바 데이터 가공
  const filteredNews = category === 'All' 
    ? news 
    : news.filter((item) => item.category === category);

  const mostLikedNews = [...news].sort((a, b) => b.likes - a.likes).slice(0, 3);
  const mostDislikedNews = [...news].sort((a, b) => b.dislikes - a.dislikes).slice(0, 3);

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-white font-sans selection:bg-cyan-500/30 overflow-x-hidden">
      {/* 배경 효과 */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-purple-900/20 blur-[120px] rounded-full" />
        <div className="absolute bottom-[10%] right-[-10%] w-[400px] h-[400px] bg-cyan-900/10 blur-[100px] rounded-full" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-8">
        
        {/* 헤더 */}
        <header className="mb-12 flex flex-col md:flex-row justify-between items-end gap-4">
          <h1 className="text-6xl font-black tracking-tighter drop-shadow-[0_0_20px_rgba(6,182,212,0.5)] uppercase">
            K-Enter 24
          </h1>
          <div className="flex items-center gap-2 px-4 py-2 bg-white/5 rounded-full border border-white/10 backdrop-blur-md">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-[10px] font-bold text-cyan-400 tracking-widest uppercase">AI-Driven Curation Active</span>
          </div>
        </header>

        {/* [실제 데이터] AI Insight 배너 */}
        <div className="mb-8 p-[2px] rounded-2xl bg-gradient-to-r from-cyan-500 via-purple-500 to-pink-500 shadow-[0_0_30px_rgba(192,38,211,0.2)]">
          <div className="bg-[#0f0f25] rounded-[14px] p-6 flex items-center gap-4">
            <Zap className="text-yellow-400 w-10 h-10 flex-shrink-0 animate-pulse" />
            <p className="text-xl md:text-2xl font-bold italic text-white/90">
              "{news[0]?.insight || "Analyzing the latest global K-Entertainment trends via AI Editor..."}"
            </p>
          </div>
        </div>

        {/* 카테고리 탭 */}
        <div className="flex gap-2 overflow-x-auto pb-4 mb-8 scrollbar-hide">
          {CATEGORIES.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setCategory(tab.value)}
              className={`px-6 py-2 rounded-full text-sm font-bold transition-all whitespace-nowrap border ${
                category === tab.value 
                ? 'bg-white text-black border-white shadow-[0_0_15px_rgba(255,255,255,0.4)]' 
                : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          
          {/* 메인 피드: 랭킹별 차등 디자인 */}
          <div className="lg:col-span-8">
            {loading ? (
              <div className="text-center py-20 text-gray-500 animate-pulse font-bold tracking-widest">LOADING DATA STREAM...</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {filteredNews.map((item) => {
                  const isTop3 = item.rank <= 3;
                  const isMid = item.rank > 3 && item.rank <= 10;
                  const cardClass = isTop3 
                    ? "md:col-span-2 bg-gradient-to-br from-white/10 to-white/5 p-8" 
                    : isMid 
                      ? "md:col-span-1 bg-white/5 p-6" 
                      : "md:col-span-1 bg-white/[0.02] p-5 grayscale-[0.3] hover:grayscale-0";

                  return (
                    <motion.div
                      key={item.id}
                      layoutId={item.id}
                      onClick={() => setSelectedArticle(item)}
                      className={`${cardClass} rounded-3xl border border-white/10 cursor-pointer hover:border-cyan-500/50 hover:shadow-[0_0_20px_rgba(6,182,212,0.1)] transition-all group`}
                    >
                      <div className="flex justify-between items-start mb-4">
                        <span className={`font-black ${isTop3 ? 'text-5xl text-cyan-400' : 'text-2xl text-gray-600'}`}>#{item.rank}</span>
                        <span className="text-[10px] font-bold px-2 py-1 bg-cyan-500/10 text-cyan-400 rounded uppercase tracking-widest border border-cyan-500/20">{item.category}</span>
                      </div>
                      <h2 className={`${isTop3 ? 'text-2xl' : 'text-lg'} font-bold mb-3 group-hover:text-cyan-300 transition-colors leading-tight`}>{item.title}</h2>
                      <p className="text-sm text-gray-400 line-clamp-3 mb-6 leading-relaxed">{item.summary}</p>
                      
                      <div className="flex items-center justify-between mt-auto">
                        <div className="flex items-center gap-1 text-yellow-500 font-bold">
                          <Star size={16} className="fill-current" /> {item.score}
                        </div>
                        <div className="flex gap-4 text-xs font-bold">
                          <button onClick={(e) => handleVote(item.id, 'likes', e)} className="flex items-center gap-1 text-cyan-400 hover:scale-110 transition-transform"><ThumbsUp size={14}/> {item.likes}</button>
                          <button onClick={(e) => handleVote(item.id, 'dislikes', e)} className="flex items-center gap-1 text-red-400 hover:scale-110 transition-transform"><ThumbsDown size={14}/> {item.dislikes}</button>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 사이드바: 요청하신 순서대로 배치 */}
          <aside className="lg:col-span-4 space-y-8">
            
            {/* 1. Trending Keywords */}
            <section className="bg-white/5 rounded-3xl p-6 border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp size={20} className="text-purple-400" />
                <h3 className="font-bold uppercase tracking-wider text-sm">Trending Keywords</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {['#Debut', '#Comeback', '#Casting', '#WorldTour', '#K-Food', '#Webtoon'].map(tag => (
                  <span key={tag} className="px-3 py-1 bg-white/5 rounded-lg text-[10px] font-bold text-gray-400 border border-white/5 hover:border-purple-500/50 cursor-pointer transition-all">{tag}</span>
                ))}
              </div>
            </section>

            {/* 2. Most Liked News */}
            <section className="bg-white/5 rounded-3xl p-6 border border-white/10">
              <div className="flex items-center gap-2 mb-4 text-cyan-400">
                <Trophy size={20} />
                <h3 className="font-bold text-white uppercase tracking-wider text-sm">Most Liked</h3>
              </div>
              <div className="space-y-4">
                {mostLikedNews.map(m => (
                  <div key={m.id} className="text-sm border-b border-white/5 pb-3 last:border-0 last:pb-0">
                    <p className="font-medium line-clamp-1 mb-1 group-hover:text-cyan-400 transition-colors">{m.title}</p>
                    <span className="text-cyan-500 font-bold text-[10px] uppercase tracking-tighter">👍 {m.likes} Fans Hyped</span>
                  </div>
                ))}
              </div>
            </section>

            {/* 3. Controversial (Most Disliked) */}
            <section className="bg-white/5 rounded-3xl p-6 border border-white/10">
              <div className="flex items-center gap-2 mb-4 text-red-400">
                <ThumbsDown size={20} />
                <h3 className="font-bold text-white uppercase tracking-wider text-sm">Controversial</h3>
              </div>
              <div className="space-y-4">
                {mostDislikedNews.map(m => (
                  <div key={m.id} className="text-sm border-b border-white/5 pb-3 last:border-0 last:pb-0">
                    <p className="font-medium line-clamp-1 mb-1">{m.title}</p>
                    <span className="text-red-500 font-bold text-[10px] uppercase tracking-tighter">👎 {m.dislikes} Unfavorable</span>
                  </div>
                ))}
              </div>
            </section>

            {/* 4. Live Vibe Check */}
            <section className="bg-white/5 rounded-3xl p-6 border border-white/10">
              <div className="flex items-center gap-2 mb-4 text-pink-500">
                <Activity size={20} />
                <h3 className="font-bold text-white uppercase tracking-wider text-sm">Live Vibe Check</h3>
              </div>
              <div className="space-y-4">
                {[{l:'Excitement', v:78, c:'bg-cyan-500'}, {l:'Shock', v:15, c:'bg-yellow-500'}, {l:'Sadness', v:7, c:'bg-red-500'}].map(s => (
                  <div key={s.l}>
                    <div className="flex justify-between text-[10px] mb-1.5 uppercase font-black text-gray-500 tracking-widest"><span>{s.l}</span><span>{s.v}%</span></div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden"><div className={`h-full ${s.c} shadow-[0_0_10px_rgba(0,255,255,0.5)]`} style={{width:`${s.v}%`}} /></div>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </div>
      </div>

      {/* 상세 팝업 모달 */}
      <AnimatePresence>
        {selectedArticle && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-xl">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 20 }} 
              animate={{ scale: 1, opacity: 1, y: 0 }} 
              exit={{ scale: 0.9, opacity: 0, y: 20 }} 
              className="bg-[#13132b] border border-white/20 p-8 md:p-10 rounded-[40px] max-w-2xl w-full relative shadow-[0_0_80px_rgba(0,0,0,0.8)]"
            >
              <button onClick={() => setSelectedArticle(null)} className="absolute top-8 right-8 text-gray-500 hover:text-white transition-colors"><X size={32}/></button>
              
              <div className="mb-8">
                <span className="text-cyan-400 font-black text-xs tracking-[0.3em] uppercase">#{selectedArticle.rank} // {selectedArticle.category}</span>
                <h2 className="text-3xl md:text-4xl font-bold mt-4 leading-tight tracking-tight">{selectedArticle.title}</h2>
              </div>

              <div className="text-gray-300 text-lg leading-relaxed mb-10 max-h-[35vh] overflow-y-auto pr-4 custom-scrollbar">
                {selectedArticle.summary}
              </div>

              <div className="flex flex-col gap-6 p-8 bg-white/5 rounded-[32px] border border-white/10 backdrop-blur-md">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <Star className="text-yellow-500 fill-current w-8 h-8" /> 
                    <div className="flex flex-col">
                      <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">AI Performance Score</span>
                      <span className="text-3xl font-black text-white">{selectedArticle.score}</span>
                    </div>
                  </div>
                  <div className="flex gap-8">
                    <button onClick={() => handleVote(selectedArticle.id, 'likes')} className="flex flex-col items-center gap-2 group">
                      <div className="p-3 rounded-2xl bg-cyan-500/10 group-hover:bg-cyan-500/20 transition-all text-cyan-400"><ThumbsUp size={28}/></div>
                      <span className="text-xs font-bold text-gray-400">{selectedArticle.likes}</span>
                    </button>
                    <button onClick={() => handleVote(selectedArticle.id, 'dislikes')} className="flex flex-col items-center gap-2 group">
                      <div className="p-3 rounded-2xl bg-red-500/10 group-hover:bg-red-500/20 transition-all text-red-400"><ThumbsDown size={28}/></div>
                      <span className="text-xs font-bold text-gray-400">{selectedArticle.dislikes}</span>
                    </button>
                  </div>
                </div>
                <a 
                  href={selectedArticle.link} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="block text-center py-5 bg-gradient-to-r from-cyan-600 to-blue-600 rounded-2xl font-black text-sm uppercase tracking-[0.2em] text-white hover:from-cyan-500 hover:to-blue-500 transition-all shadow-lg shadow-cyan-900/40"
                >
                  Read Original Article
                </a>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
