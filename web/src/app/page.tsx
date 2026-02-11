'use client';

import { useState, useEffect } from 'react';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';

// 분리한 컴포넌트 불러오기
import NewsFeed from '@/components/NewsFeed';
import HotKeywords from '@/components/HotKeywords';
import VibeCheck from '@/components/VibeCheck';

export default function Home() {
  const [articles, setArticles] = useState<any[]>([]); 
  const [user, setUser] = useState<any>(null);
  const [topVibe, setTopVibe] = useState<any>(null); // 최신 기사의 감정 데이터
  
  const supabase = createClientComponentClient();

  useEffect(() => {
    const init = async () => {
      // 1. 유저 세션 확인
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user ?? null);

      // 2. 뉴스 데이터 가져오기
      const { data } = await supabase
        .from('live_news')
        .select('*')
        .eq('is_published', true)
        .order('id', { ascending: false });
      
      if (data && data.length > 0) {
        setArticles(data);
        // 가장 최신 기사의 분위기를 VibeCheck에 전달 (예시)
        setTopVibe(data[0].reactions); 
      }
    };
    init();
  }, []);

  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  };

  return (
    <main className="min-h-screen bg-black text-white p-4 md:p-8 font-sans">
      
      {/* 헤더 */}
      <header className="flex justify-between items-center mb-8 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="K-POP 24" className="h-24 md:h-32 w-auto object-contain drop-shadow-[0_0_15px_rgba(34,211,238,0.6)]" />
        </div>

        {user ? (
          <div className="flex items-center gap-3">
             <span className="text-cyan-400 text-sm font-bold hidden md:inline">
               Agent {user.email?.split('@')[0]}
             </span>
             <button onClick={() => supabase.auth.signOut()} className="text-xs text-gray-500 border border-gray-700 px-3 py-1 rounded hover:bg-gray-800">
               Log Out
             </button>
          </div>
        ) : (
          <button 
            onClick={handleLogin}
            className="bg-cyan-500 text-black px-5 py-2 rounded-full text-sm font-bold hover:bg-cyan-400 transition-all shadow-[0_0_15px_rgba(34,211,238,0.4)] animate-pulse"
          >
            LOG IN (FREE)
          </button>
        )}
      </header>

      {/* 1. 뉴스 피드 컴포넌트 */}
      <NewsFeed 
        articles={articles} 
        user={user} 
        onLogin={handleLogin} 
      />

      {/* 2 & 3. 하단 분석 섹션 (키워드 + AI 분석) */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-7xl mx-auto pb-10">
        <HotKeywords />
        <VibeCheck data={topVibe} />
      </section>

    </main>
  );
}
