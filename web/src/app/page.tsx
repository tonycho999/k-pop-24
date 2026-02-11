'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { motion } from 'framer-motion';
import { Newspaper, TrendingUp, Zap, Activity, Star } from 'lucide-react';

export default function Home() {
  // 여기서 에러 났던 부분을 any[]로 확실하게 고쳤습니다
  const [news, setNews] = useState<any[]>([]);
  const [category, setCategory] = useState('All');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNews = async () => {
      const { data } = await supabase
        .from('live_news')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(50);
      
      if (data) setNews(data);
      setLoading(false);
    };

    fetchNews();
  }, []);

  const filteredNews = category === 'All' 
    ? news 
    : news.filter((item: any) => item.category === category);

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-white font-sans overflow-x-hidden">
      {/* 배경 효과 */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-purple-900/30 blur-[120px] rounded-full" />
        <div className="absolute bottom-[10%] right-[-10%] w-[400px] h-[400px] bg-cyan-900/20 blur-[100px] rounded-full" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-4 py-8">
        
        {/* 헤더: 제목이 잘 보이도록 그라데이션 대신 흰색+네온 효과로 변경 */}
        <header className="flex flex-col md:flex-row justify-between items-center mb-10 gap-4">
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tighter text-white drop-shadow-[0_0_15px_rgba(6,182,212,0.8)]">
            K-ENTER 24
          </h1>
          <div className="flex items-center gap-2 px-4 py-2 bg-white/5 rounded-full border border-white/10 backdrop-blur-md shadow-[0_0_15px_rgba(0,255,255,0.2)]">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs font-bold text-cyan-300 tracking-wider">LIVE SYSTEM ACTIVE</span>
          </div>
        </header>

        {/* AI Insight 배너 */}
        <div className="mb-10 p-1 rounded-xl bg-gradient-to-r from-cyan-500 via-purple-500 to-pink-500">
          <div className="bg-[#0f0f25] rounded-lg p-4 flex items-center gap-4">
            <Zap className="text-yellow-400 w-8 h-8 flex-shrink-0 animate-pulse" />
            <div>
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">AI Chief Editor's Insight</h3>
              <p className="text-sm md:text-lg font-medium text-white">
                "Global fans are currently hyped about <span className="text-cyan-400 font-bold">NewJeans</span> comeback rumors and <span className="text-purple-400 font-bold">Squid Game 2</span> teasers!"
              </p>
            </div>
          </div>
        </div>

        {/* 메인 레이아웃 */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* 왼쪽: 뉴스 피드 */}
          <div className="lg:col-span-8 space-y-6">
            <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide mb-4">
              {['All', 'K-POP', 'K-Drama', 'K-Movie', 'Variety'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setCategory(tab)}
                  className={`px-5 py-2 rounded-full text-sm font-bold transition-all whitespace-nowrap border ${
                    category === tab 
                    ? 'bg-white text-black border-white shadow-[0_0_15px_rgba(255,255,255,0.4)]' 
                    : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {loading ? (
              <div className="text-center py-20 text-gray-500 animate-pulse">Loading Data Stream...</div>
            ) : (
              filteredNews.map((item: any, idx: number) => (
                <motion.div 
                  key={item.id || idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="group flex flex-col md:flex-row gap-4 bg-[#13132b]/80 border border-white/5 p-4 rounded-2xl hover:border-cyan-500/50 hover:bg-[#1a1a35] transition-all duration-300"
                >
                  {/* 썸네일 */}
                  <div className="md:w-40 md:h-28 flex-shrink-0 rounded-xl overflow-hidden bg-black relative">
                    <img 
                      src={item.image_url || 'https://placehold.co/600x400/111/cyan?text=No+Image'} 
                      alt={item.title} 
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                    />
                    <div className="absolute top-0 left-0 bg-black/60 px-2 py-1 text-[10px] font-bold text-white uppercase backdrop-blur-sm">
                      {item.category}
                    </div>
                  </div>
                  
                  {/* 내용 */}
                  <div className="flex-1 flex flex-col justify-between">
                    <div>
                      <h3 className="text-lg font-bold leading-snug group-hover:text-cyan-300 transition-colors mb-2">
                        {item.title}
                      </h3>
                      <p className="text-sm text-gray-400 line-clamp-2">
                        {item.summary}
                      </p>
                    </div>
                    <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1 text-yellow-500 font-bold">
                          <Star className="w-3 h-3 fill-current" /> {item.score}
                        </span>
                        <span>{new Date(item.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                      </div>
                      <a href={item.link} target="_blank" className="text-cyan-500 hover:text-white font-bold">READ MORE →</a>
                    </div>
                  </div>
                </motion.div>
              ))
            )}
          </div>

          {/* 오른쪽: 사이드바 */}
          <div className="lg:col-span-4 space-y-6">
            <div className="rounded-2xl bg-[#0f0f25] p-6 border border-white/10 shadow-lg">
              <div className="flex items-center gap-2 mb-6">
                <Activity className="text-pink-500 w-5 h-5 animate-bounce" />
                <h3 className="font-bold text-lg text-white">Live Vibe Check</h3>
              </div>
              <div className="space-y-5">
                {[
                  { label: '😍 Excitement', val: 78, color: 'bg-cyan-500', text: 'text-cyan-400' },
                  { label: '😲 Shock', val: 15, color: 'bg-yellow-500', text: 'text-yellow-400' },
                  { label: '😢 Sadness', val: 7, color: 'bg-red-500', text: 'text-red-400' }
                ].map((stat) => (
                  <div key={stat.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-300">{stat.label}</span>
                      <span className={`font-bold ${stat.text}`}>{stat.val}%</span>
                    </div>
                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                      <div className={`h-full ${stat.color} rounded-full`} style={{ width: `${stat.val}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl bg-[#0f0f25] p-6 border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="text-purple-400 w-5 h-5" />
                <h3 className="font-bold text-lg text-white">Trending Keywords</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {['#NewJeans', '#SquidGame2', '#BTS', '#Blackpink', '#K-Food', '#HanSohee'].map((tag) => (
                  <span key={tag} className="px-3 py-1.5 rounded-lg bg-white/5 text-xs font-medium text-gray-300 border border-white/5 hover:bg-purple-500/20 hover:text-purple-300 hover:border-purple-500/50 cursor-pointer transition-all">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
