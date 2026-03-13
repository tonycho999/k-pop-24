'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { Flame, X, Trophy, ChevronRight, LogIn, LogOut, User as UserIcon, PlayCircle } from 'lucide-react';
import { User } from '@supabase/supabase-js';

interface MobileFloatingBtnProps {
  news: any[];
  category: string;
}

export default function MobileFloatingBtn({ news, category }: MobileFloatingBtnProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [rankings, setRankings] = useState<any[]>([]); // ✅ [추가] 랭킹 데이터를 담을 상태

  // 1. 유저 정보 가져오기
  useEffect(() => {
    const fetchUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user);
    };
    fetchUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  // 2. ✅ [핵심 수정] 카테고리가 바뀔 때마다 해당 카테고리의 '진짜 Top 10 차트'를 불러옵니다.
  useEffect(() => {
    const fetchRankings = async () => {
      let targetCategory = category.toLowerCase();
      
      // 'All'이나 'K-Culture'는 고유 차트가 없으므로 가장 인기 있는 'k-pop' 차트를 기본으로 보여줍니다.
      if (targetCategory === 'all' || targetCategory === 'k-culture') {
        targetCategory = 'k-pop';
      }

      const { data, error } = await supabase
        .from('live_rankings')
        .select('*')
        .eq('category', targetCategory)
        .order('rank', { ascending: true })
        .limit(10);

      if (data && !error) {
        setRankings(data);
      }
    };

    fetchRankings();
  }, [category]); // category가 변경될 때마다 재실행

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

  // 현재 보여주는 차트의 제목을 예쁘게 포맷팅
  const getChartTitle = () => {
    if (category === 'K-Movie') return 'Box Office Top 10';
    if (category === 'K-Drama') return 'Trending Dramas Top 10';
    if (category === 'K-Entertain') return 'TV Shows Top 10';
    return 'Music Chart Top 10'; // 기본값 (K-Pop)
  };

  return (
    <>
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

      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-[90] md:hidden backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setIsOpen(false)}
        />
      )}

      <div
        className={`fixed bottom-0 left-0 right-0 z-[100] bg-white/95 backdrop-blur-xl rounded-t-[32px] shadow-[0_-10px_40px_rgba(0,0,0,0.2)] transform transition-transform duration-300 cubic-bezier(0.16, 1, 0.3, 1) md:hidden flex flex-col max-h-[85vh]
          ${isOpen ? 'translate-y-0' : 'translate-y-full'}
        `}
      >
        <div className="pt-4 pb-2 px-6 flex-shrink-0" onClick={() => setIsOpen(false)}>
            <div className="w-12 h-1.5 bg-slate-200 rounded-full mx-auto mb-4" />
        </div>

        <div className="overflow-y-auto px-6 pb-12 overflow-x-hidden">
            
            {/* 로그인/유저 섹션 */}
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

            {/* ✅ [수정] 진짜 랭킹 차트 (live_rankings 테이블 데이터) */}
            <div className="pb-8">
                <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2">
                    <Trophy className="w-5 h-5 text-amber-500" />
                    {getChartTitle()}
                </h3>
                <div className="space-y-3">
                    {rankings.length > 0 ? (
                        rankings.map((item, idx) => (
                        <a 
                            key={item.id || idx} 
                            // 클릭하면 유튜브 검색으로 바로 넘어가도록 편의성 추가
                            href={`https://www.youtube.com/results?search_query=${encodeURIComponent(item.title)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-4 group p-3 rounded-2xl bg-white border border-slate-100 shadow-sm active:bg-slate-50 transition-all"
                        >
                            <span className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-sm font-black
                                ${idx === 0 ? 'bg-amber-100 text-amber-600' : 
                                  idx === 1 ? 'bg-slate-200 text-slate-600' :
                                  idx === 2 ? 'bg-orange-100 text-orange-700' : 'bg-slate-50 text-slate-400'}
                            `}>
                                {item.rank}
                            </span>
                            <div className="flex-1 min-w-0">
                                <h4 className="text-sm font-bold text-slate-700 leading-snug truncate">
                                    {item.title}
                                </h4>
                                {/* 영화 관객수, 유튜브 조회수 등 부가 정보 출력 */}
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-0.5 block truncate">
                                    {item.info}
                                </span>
                            </div>
                            <PlayCircle className="w-5 h-5 text-slate-200 group-hover:text-red-500 transition-colors" />
                        </a>
                        ))
                    ) : (
                        <div className="text-center py-6 text-slate-400 text-sm">
                            Loading charts...
                        </div>
                    )}
                </div>
            </div>
            
            <div className="h-8 md:h-0" />
        </div>
      </div>
    </>
  );
}
