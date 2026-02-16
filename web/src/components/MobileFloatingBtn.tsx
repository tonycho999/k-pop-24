'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { Flame, X, Trophy, TrendingUp, ChevronRight, LogIn, LogOut, User as UserIcon } from 'lucide-react';
import { User } from '@supabase/supabase-js';

export default function MobileFloatingBtn() {
  const [isOpen, setIsOpen] = useState(false);
  const [keywords, setKeywords] = useState<any[]>([]);
  const [topNews, setTopNews] = useState<any[]>([]);
  const [user, setUser] = useState<User | null>(null);

  // 데이터 및 유저 정보 가져오기
  useEffect(() => {
    const fetchData = async () => {
      // 1. 유저 세션 확인
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user);

      // 2. 트렌드 키워드 (Top 8로 제한하여 공간 확보)
      const { data: kwData } = await supabase
        .from('live_rankings')
        .select('*')
        .order('rank', { ascending: true })
        .limit(8);
      if (kwData) setKeywords(kwData);

      // 3. 인기 뉴스 Top 5
      const { data: newsData } = await supabase
        .from('live_news')
        .select('title, category, score, link')
        .order('score', { ascending: false })
        .limit(5);
      if (newsData) setTopNews(newsData);
    };

    fetchData();

    // 유저 상태 변화 감지
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setIsOpen(false);
  };

  return (
    <>
      {/* 1. 플로팅 버튼 (화면 우측 하단 고정) */}
      <button
        onClick={() => setIsOpen(true)}
        className={`md:hidden fixed bottom-6 right-6 z-[100] p-4 rounded-full shadow-2xl transition-all duration-300 flex items-center justify-center
          ${isOpen 
            ? 'bg-slate-800 rotate-90 scale-100' 
            : 'bg-gradient-to-r from-orange-500 to-red-600 hover:scale-110 active:scale-95'
          }
        `}
      >
        {isOpen ? (
          <X className="w-6 h-6 text-white" />
        ) : (
          <Flame className="w-7 h-7 text-white fill-white animate-pulse" />
        )}
      </button>

      {/* 2. 어두운 배경 (Overlay) */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-[90] md:hidden backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* 3. 바텀 시트 (패널) */}
      <div
        className={`fixed bottom-0 left-0 right-0 z-[100] bg-white/95 backdrop-blur-xl rounded-t-[32px] shadow-[0_-10px_40px_rgba(0,0,0,0.2)] transform transition-transform duration-300 cubic-bezier(0.16, 1, 0.3, 1) md:hidden flex flex-col max-h-[85vh]
          ${isOpen ? 'translate-y-0' : 'translate-y-full'}
        `}
      >
        {/* 핸들바 & 헤더 영역 */}
        <div className="pt-4 pb-2 px-6 flex-shrink-0" onClick={() => setIsOpen(false)}>
            <div className="w-12 h-1.5 bg-slate-200 rounded-full mx-auto mb-4" />
        </div>

        {/* 스크롤 가능한 콘텐츠 영역 */}
        <div className="overflow-y-auto px-6 pb-12 overflow-x-hidden">
            
            {/* [New] 로그인/유저 섹션 (최상단 배치) */}
            <div className="mb-8 p-4 bg-slate-50 border border-slate-100 rounded-2xl">
                {user ? (
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-cyan-100 rounded-full flex items-center justify-center text-cyan-600">
                                <UserIcon size={20} />
                            </div>
                            <div>
                                <p className="text-xs text-slate-400 font-bold uppercase">Welcome Back</p>
                                <p className="text-sm font-bold text-slate-800">{user.email?.split('@')[0]}</p>
                            </div>
                        </div>
                        <button 
                            onClick={handleLogout}
                            className="p-2 bg-white border border-slate-200 rounded-xl text-slate-500 hover:text-red-500 transition-colors"
                        >
                            <LogOut size={18} />
                        </button>
                    </div>
                ) : (
                    <div className="text-center">
                         <h4 className="text-sm font-bold text-slate-800 mb-1">Unlock Full Access</h4>
                         <p className="text-xs text-slate-400 mb-3">Vote & Read unlimited AI news</p>
                         <button 
                            onClick={handleLogin}
                            className="w-full py-3 bg-slate-900 text-white rounded-xl text-sm font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform"
                         >
                            <LogIn size={16} />
                            Sign in with Google
                         </button>
                    </div>
                )}
            </div>

            {/* 섹션 1: 실시간 트렌드 키워드 */}
            <div className="mb-8">
                <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-red-500" />
                    Real-time Trends
                </h3>
                <div className="flex flex-wrap gap-2">
                    {keywords.map((item, idx) => (
                    <span 
                        key={item.id} 
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold border flex items-center gap-1.5
                        ${idx < 3 
                            ? 'bg-red-50 border-red-100 text-red-600' 
                            : 'bg-white border-slate-100 text-slate-500'
                        }`}
                    >
                        <span className="opacity-60 text-[10px]">#{item.rank}</span>
                        {item.keyword}
                    </span>
                    ))}
                </div>
            </div>

            <div className="h-px bg-slate-100 mb-8" />

            {/* 섹션 2: 지금 가장 핫한 뉴스 */}
            <div className="pb-8">
                <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2">
                    <Trophy className="w-5 h-5 text-amber-500" />
                    Top Voted News
                </h3>
                <div className="space-y-3">
                    {topNews.map((news, idx) => (
                    <a 
                        key={idx} 
                        href={news.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-4 group p-3 rounded-2xl bg-white border border-slate-100 shadow-sm active:bg-slate-50 transition-all"
                    >
                        <span className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-sm font-black
                            ${idx === 0 ? 'bg-amber-100 text-amber-600' : 'bg-slate-100 text-slate-500'}
                        `}>
                            {idx + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                            <span className="text-[10px] font-bold text-cyan-600 uppercase tracking-wider mb-0.5 block">
                                {news.category}
                            </span>
                            <h4 className="text-sm font-bold text-slate-700 leading-snug truncate">
                                {news.title}
                            </h4>
                        </div>
                        <ChevronRight className="w-4 h-4 text-slate-300" />
                    </a>
                    ))}
                </div>
            </div>
            
            {/* 하단 여백 (아이폰 홈 바 대응) */}
            <div className="h-8 md:h-0" />
        </div>
      </div>
    </>
  );
}
