'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Star, ThumbsUp, ThumbsDown, X, TrendingUp, Activity, Trophy } from 'lucide-react';

export default function Home() {
  const [news, setNews] = useState<any[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNews();
  }, []);

  const fetchNews = async () => {
    const { data } = await supabase
      .from('live_news')
      .select('*')
      .order('rank', { ascending: true });
    if (data) setNews(data);
    setLoading(false);
  };

  // 좋아요/싫어요 클릭 처리
  const handleVote = async (id: string, type: 'likes' | 'dislikes', e: React.MouseEvent) => {
    e.stopPropagation(); // 카드 클릭 이벤트 전파 방지
    await supabase.rpc('increment_vote', { row_id: id, col_name: type });
    fetchNews(); // 수치 업데이트를 위해 재호출
  };

  // 사이드바용 데이터 가공
  const mostLikedNews = [...news].sort((a, b) => b.likes - a.likes).slice(0, 3);
  const mostDislikedNews = [...news].sort((a, b) => b.dislikes - a.dislikes).slice(0, 3);

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-white font-sans selection:bg-cyan-500/30">
      <div className="max-w-7xl mx-auto px-4 py-8">
        
        {/* 헤더 */}
        <header className="mb-12 flex flex-col md:flex-row justify-between items-end gap-4">
          <h1 className="text-6xl font-black tracking-tighter drop-shadow-[0_0_20px_rgba(6,182,212,0.5)]">K-ENTER 24</h1>
          <p className="text-cyan-400 font-bold text-sm tracking-[0.2em]">AI-DRIVEN REALTIME CURATION</p>
        </header>

        {/* [진짜 인사이트 배너] 가짜 문구 삭제 및 DB 데이터 연동 */}
        <div className="mb-12 p-[2px] rounded-2xl bg-gradient-to-r from-cyan-500 via-purple-500 to-pink-500 shadow-[0_0_30px_rgba(192,38,211,0.2)]">
          <div className="bg-[#0f0f25] rounded-[14px] p-6 flex items-center gap-4">
            <Zap className="text-yellow-400 w-10 h-10 flex-shrink-0 animate-pulse" />
            <p className="text-xl md:text-2xl font-bold italic text-white/90">
              "{news[0]?.insight || "Analyzing the latest K-Enter trends via AI Editor..."}"
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          {/* 메인 뉴스 피드 (왼쪽 8칸) */}
          <div className="lg:col-span-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {news.map((item) => {
                // [요구사항] 랭킹별 차등 레이아웃
                const isTop3 = item.rank <= 3;
                const isMid = item.rank > 3 && item.rank <= 10;
                const cardClass = isTop3 
                  ? "md:col-span-2 bg-gradient-to-br from-white/10 to-white/5 p-8" 
                  : isMid 
                    ? "md:col-span-1 bg-white/5 p-6" 
                    : "md:col-span-1 bg-white/[0.03] p-5 grayscale-[0.5] hover:grayscale-0";

                return (
                  <motion.div
                    key={item.id}
                    layoutId={item.id}
                    onClick={() => setSelectedArticle(item)}
                    className={`${cardClass} rounded-3xl border border-white/10 cursor-pointer hover:border-cyan-500/50 hover:shadow-[0_0_20px_rgba(6,182,212,0.1)] transition-all group`}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <span className={`font-black ${isTop3 ? 'text-4xl text-cyan-400' : 'text-xl text-gray-500'}`}>#{item.rank}</span>
                      <span className="text-[10px] font-bold px-2 py-1 bg-white/10 rounded uppercase tracking-widest">{item.category}</span>
                    </div>
                    <h2 className={`${isTop3 ? 'text-2xl' : 'text-lg'} font-bold mb-3 group-hover:text-cyan-300 transition-colors`}>{item.title}</h2>
                    <p className="text-sm text-gray-400 line-clamp-3 mb-6">{item.summary}</p>
                    
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
          </div>

          {/* 사이드바 (오른쪽 4칸) */}
          <aside className="lg:col-span-4 space-y-8">
            {/* 1. Trending Keywords */}
            <section className="bg-white/5 rounded-3xl p-6 border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp size={20} className="text-purple-400" />
                <h3 className="font-bold">Trending Keywords</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {['#Debut', '#Comeback', '#Casting', '#WorldTour', '#K-Food', '#Webtoon'].map(tag => (
                  <span key={tag} className="px-3 py-1 bg-white/5 rounded-full text-xs text-gray-400 border border-white/5 hover:border-purple-500/50 cursor-default">{tag}</span>
                ))}
              </div>
            </section>

            {/* 2. Most Liked News */}
            <section className="bg-white/5 rounded-3xl p-6 border border-white/10">
              <div className="flex items-center gap-2 mb-4 text-cyan-400">
                <Trophy size={20} />
                <h3 className="font-bold text-white">Most Liked</h3>
              </div>
              <div className="space-y-4">
                {mostLikedNews.map(m => (
                  <div key={m.id} className="text-sm border-b border-white/5 pb-2 last:border-0">
                    <p className="font-medium line-clamp-1 mb-1">{m.title}</p>
                    <span className="text-cyan-500 font-bold text-xs">👍 {m.likes} Likes</span>
                  </div>
                ))}
              </div>
            </section>

            {/* 3. Most Disliked News */}
            <section className="bg-white/5 rounded-3xl p-6 border border-white/10">
              <div className="flex items-center gap-2 mb-4 text-red-400">
                <ThumbsDown size={20} />
                <h3 className="font-bold text-white">Controversial</h3>
              </div>
              <div className="space-y-4">
                {mostDislikedNews.map(m => (
                  <div key={m.id} className="text-sm border-b border-white/5 pb-2 last:border-0">
                    <p className="font-medium line-clamp-1 mb-1">{m.title}</p>
                    <span className="text-red-500 font-bold text-xs">👎 {m.dislikes} Dislikes</span>
                  </div>
                ))}
              </div>
            </section>

            {/* 4. Live Vibe Check */}
            <section className="bg-white/5 rounded-3xl p-6 border border-white/10">
              <div className="flex items-center gap-2 mb-4 text-pink-500">
                <Activity size={20} />
                <h3 className="font-bold text-white">Live Vibe Check</h3>
              </div>
              <div className="space-y-3">
                {[{l:'Excitement', v:78, c:'bg-cyan-500'}, {l:'Shock', v:15, c:'bg-yellow-500'}, {l:'Sadness', v:7, c:'bg-red-500'}].map(s => (
                  <div key={s.l}>
                    <div className="flex justify-between text-[10px] mb-1 uppercase font-bold text-gray-400"><span>{s.l}</span><span>{s.v}%</span></div>
                    <div className="h-1 bg-white/10 rounded-full overflow-hidden"><div className={`h-full ${s.c}`} style={{width:`${s.v}%`}} /></div>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </div>
      </div>

      {/* [상세 팝업 모달] */}
      <AnimatePresence>
        {selectedArticle && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-xl">
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="bg-[#13132b] border border-white/20 p-8 rounded-[40px] max-w-2xl w-full relative shadow-[0_0_50px_rgba(0,0,0,0.5)]">
              <button onClick={() => setSelectedArticle(null)} className="absolute top-6 right-6 text-gray-500 hover:text-white transition-colors"><X/></button>
              
              <div className="mb-6">
                <span className="text-cyan-400 font-bold text-sm tracking-widest uppercase">#{selectedArticle.rank} {selectedArticle.category}</span>
                <h2 className="text-3xl font-bold mt-2 leading-tight">{selectedArticle.title}</h2>
              </div>

              <div className="text-gray-300 text-lg leading-relaxed mb-8 max-h-[40vh] overflow-y-auto pr-2 custom-scrollbar">
                {selectedArticle.summary}
              </div>

              <div className="flex flex-col gap-6 p-6 bg-white/5 rounded-3xl border border-white/10">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2"><Star className="text-yellow-500 fill-current" /> <span className="text-2xl font-black">AI SCORE: {selectedArticle.score}</span></div>
                  <div className="flex gap-6">
                    <button onClick={(e) => handleVote(selectedArticle.id, 'likes', e)} className="flex flex-col items-center gap-1 text-cyan-400"><ThumbsUp size={24}/><span className="text-xs">{selectedArticle.likes}</span></button>
                    <button onClick={(e) => handleVote(selectedArticle.id, 'dislikes', e)} className="flex flex-col items-center gap-1 text-red-400"><ThumbsDown size={24}/><span className="text-xs">{selectedArticle.dislikes}</span></button>
                  </div>
                </div>
                <a href={selectedArticle.link} target="_blank" rel="noopener noreferrer" className="block text-center py-4 bg-cyan-600 rounded-2xl font-bold text-white hover:bg-cyan-500 transition-colors shadow-lg shadow-cyan-900/20">기사 원문 읽기 (Original Link)</a>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
