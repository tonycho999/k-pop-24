'use client';

import { useState, useEffect } from 'react';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';

// 분리된 컴포넌트 불러오기
import NewsFeed from '@/components/NewsFeed';
import HotKeywords from '@/components/HotKeywords';
import VibeCheck from '@/components/VibeCheck';

export default function Home() {
  const [articles, setArticles] = useState<any[]>([]); 
  const [user, setUser] = useState<any>(null);
  const [topVibe, setTopVibe] = useState<any>(null); // 최신 기사의 AI 감정 데이터
  
  const supabase = createClientComponentClient();

  useEffect(() => {
    const init = async () => {
      // 1. 유저 세션 확인 (로그인 상태 관리)
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user ?? null);

      // 2. 실시간 뉴스 데이터 가져오기 (is_published가 true인 것만)
      const { data, error } = await supabase
        .from('live_news')
        .select('*')
        .eq('is_published', true)
        .order('created_at', { ascending: false });
      
      if (error) {
        console.error("Error fetching news:", error);
        return;
      }

      if (data && data.length > 0) {
        setArticles(data);
        // 가장 최신 기사의 vibe(감정 수치)를 분석 섹션에 전달
        // 백엔드에서 생성한 vibe 필드를 사용합니다.
        setTopVibe(data[0].vibe); 
      }
    };
    init();

    // 실시간 데이터 구독 (선택 사항: 새로운 뉴스가 올라오면 자동 갱신)
    const channel = supabase
      .channel('schema-db-changes')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'live_news' }, (payload) => {
        if (payload.new.is_published) {
          setArticles((prev) => [payload.new, ...prev]);
          setTopVibe(payload.new.vibe);
        }
      })
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [supabase]);

  // 구글 로그인 핸들러
  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { 
        redirectTo: `${window.location.origin}/auth/callback`,
        queryParams: { prompt: 'select_account' }
      },
    });
  };

  // 로그아웃 핸들러
  const handleLogout = async () => {
    await supabase.auth.signOut();
    window.location.reload(); // 세션 초기화를 위해 새로고침
  };

  return (
    <main className="min-h-screen bg-black text-white p-4 md:p-8 font-sans selection:bg-cyan-500 selection:text-black">
      
      {/* --- 헤더 섹션 --- */}
      <header className="flex justify-between items-center mb-12 max-w-7xl mx-auto border-b border-gray-800 pb-6">
        <div className="flex items-center gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img 
            src="/logo.png" 
            alt="K-POP 24" 
            className="h-20 md:h-28 w-auto object-contain drop-shadow-[0_0_20px_rgba(34,211,238,0.8)]" 
          />
        </div>

        <nav>
          {user ? (
            <div className="flex items-center gap-4">
              <div className="hidden md:flex flex-col items-end">
                <span className="text-cyan-400 text-xs font-mono tracking-widest uppercase">Authorized Agent</span>
                <span className="text-white text-sm font-bold">{user.email?.split('@')[0]}</span>
              </div>
              <button 
                onClick={handleLogout} 
                className="text-xs text-gray-400 border border-gray-700 px-4 py-2 rounded-full hover:bg-red-900/20 hover:border-red-500 transition-all"
              >
                DISCONNECT
              </button>
            </div>
          ) : (
            <button 
              onClick={handleLogin}
              className="group relative bg-cyan-500 text-black px-8 py-3 rounded-full text-sm font-black hover:bg-white transition-all shadow-[0_0_20px_rgba(34,211,238,0.5)] active:scale-95"
            >
              <span className="relative z-10">ACCESS DATABASE (FREE)</span>
              <div className="absolute inset-0 bg-cyan-400 rounded-full animate-ping opacity-20 group-hover:hidden"></div>
            </button>
          )}
        </nav>
      </header>

      {/* --- 메인 콘텐츠: 뉴스 피드 --- */}
      {/* user 객체를 넘겨주어 NewsFeed 내부에서 로그인 안 할 시 블러(Blur) 처리를 하도록 합니다. */}
      <section className="max-w-7xl mx-auto mb-16">
        <NewsFeed 
          articles={articles} 
          user={user} 
          onLogin={handleLogin} 
        />
      </section>

      {/* --- 하단 분석 섹션: 키워드 + AI Vibe Check --- */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-7xl mx-auto pb-20">
        <div className="h-full">
          <HotKeywords />
        </div>
        <div className="h-full">
          <VibeCheck data={topVibe} />
        </div>
      </section>

      {/* 푸터: 사이버펑크 디테일 */}
      <footer className="max-w-7xl mx-auto border-t border-gray-900 pt-8 flex justify-between text-[10px] text-gray-600 font-mono uppercase tracking-[0.2em]">
        <span>System Status: Online</span>
        <span>© 2026 K-POP 24 / Global News Network</span>
        <span>Secure Connection: AES-256</span>
      </footer>

    </main>
  );
}
