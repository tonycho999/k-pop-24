'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@/utils/supabase/client';
import NewsFeed from '@/components/NewsFeed';
import HotKeywords from '@/components/HotKeywords';
import VibeCheck from '@/components/VibeCheck';

export default function Home() {
  const [articles, setArticles] = useState<any[]>([]); 
  const [user, setUser] = useState<any>(null);
  const [topVibe, setTopVibe] = useState<any>(null);
  
  const supabase = createClient();

  useEffect(() => {
    const init = async () => {
      // 1. 유저 세션 확인
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user ?? null);

      // 2. 실시간 뉴스 데이터 가져오기 (is_published가 true인 것만)
      const { data, error } = await supabase
        .from('live_news')
        .select('*')
        .eq('is_published', true)
        .order('created_at', { ascending: false });
      
      if (data && data.length > 0) {
        setArticles(data);
        // DB의 'reactions' 컬럼(vibe JSON)을 VibeCheck에 전달
        setTopVibe(data[0].reactions); 
      }
    };
    init();

    const channel = supabase
      .channel('schema-db-changes')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'live_news' }, (payload) => {
        if (payload.new.is_published) {
          setArticles((prev) => [payload.new, ...prev]);
          setTopVibe(payload.new.reactions);
        }
      })
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [supabase]);

  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    window.location.reload();
  };

  return (
    <main className="min-h-screen bg-black text-white p-4 md:p-8 font-sans selection:bg-cyan-500 selection:text-black">
      <header className="flex justify-between items-center mb-12 max-w-7xl mx-auto border-b border-gray-800 pb-6">
        <img src="/logo.png" alt="K-ENTER 24" className="h-20 md:h-28 w-auto object-contain drop-shadow-[0_0_20px_rgba(34,211,238,0.8)]" />
        <nav>
          {user ? (
            <div className="flex items-center gap-4">
              <span className="text-cyan-400 text-xs font-mono hidden md:inline uppercase">Agent {user.email?.split('@')[0]}</span>
              <button onClick={handleLogout} className="text-xs text-gray-400 border border-gray-700 px-4 py-2 rounded-full hover:border-red-500 transition-all">DISCONNECT</button>
            </div>
          ) : (
            <button onClick={handleLogin} className="bg-cyan-500 text-black px-8 py-3 rounded-full text-sm font-black shadow-[0_0_20px_rgba(34,211,238,0.5)]">ACCESS DATABASE</button>
          )}
        </nav>
      </header>

      <section className="max-w-7xl mx-auto mb-16">
        <NewsFeed articles={articles} user={user} onLogin={handleLogin} />
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-7xl mx-auto pb-20">
        <HotKeywords />
        <VibeCheck data={topVibe} />
      </section>
    </main>
  );
}
