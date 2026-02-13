'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { 
  User, LogOut, ChevronDown, 
  Sun, Moon, Languages 
} from 'lucide-react';

export default function Header() {
  const [user, setUser] = useState<any>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [langCode, setLangCode] = useState('EN'); 
  
  // [수정] 전체 모니터링 개수 상태
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user));
    
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    }

    const browserLang = navigator.language.split('-')[0].toUpperCase();
    setLangCode(browserLang); 

    // [핵심 수정] Live(150개) + Archive(누적) 합산하기
    const fetchTotalCount = async () => {
      try {
        // 1. 현재 전시 중인 뉴스 개수
        const live = await supabase
          .from('live_news')
          .select('*', { count: 'exact', head: true });

        // 2. 아카이브된(누적된) 뉴스 개수 -> 여기가 계속 늘어남!
        const archive = await supabase
          .from('search_archive')
          .select('*', { count: 'exact', head: true });
        
        // 두 개 합치기 (기본값 0 처리)
        const total = (live.count || 0) + (archive.count || 0);
        
        // [옵션] 만약 숫자가 너무 적어 보이면 '기본값 1000'을 더해서 보여주는 꼼수도 가능
        // setTotalCount(total + 1000); 
        setTotalCount(total); 

      } catch (error) {
        console.error('Error fetching count:', error);
      }
    };
    fetchTotalCount();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  const toggleDarkMode = () => {
    const newDark = !isDark;
    setIsDark(newDark);
    if (newDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  const handleAiTranslate = () => {
    window.dispatchEvent(new CustomEvent('ai-translate', { detail: langCode }));
  };

  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${location.origin}/auth/callback` },
    });
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setMenuOpen(false);
  };

  return (
    <header className="flex justify-between items-center py-5 mb-1 border-b border-slate-100 dark:border-slate-800 transition-colors">
      <div className="flex items-center gap-2 sm:gap-4">
        <div className="w-[160px] sm:w-[200px] h-[80px] flex items-center justify-center overflow-hidden">
          <img src="/logo.png" alt="Logo" className="w-full h-full object-contain" />
        </div>
        
        <div className="flex flex-col ml-1 sm:ml-2 border-l border-slate-200 dark:border-slate-700 pl-2 sm:pl-3">
             <div className="flex items-center gap-1.5">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
                </span>
                <span className="text-[10px] sm:text-[11px] font-black text-cyan-500 uppercase tracking-tighter">Live</span>
             </div>
             <span className="text-[11px] sm:text-[12px] font-bold text-slate-400 dark:text-slate-500 leading-none mt-1 whitespace-nowrap uppercase">
               {/* 누적된 숫자 보여주기 */}
               {totalCount > 0 ? totalCount.toLocaleString() : 'Scanning...'} Monitoring
             </span>
        </div>
      </div>

      <div className="flex items-center gap-2 relative">
        <button 
          onClick={(e) => { e.preventDefault(); toggleDarkMode(); }} 
          className="p-2.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
        >
          {isDark ? <Sun size={22} className="text-yellow-500" /> : <Moon size={22} />}
        </button>

        <button 
          onClick={(e) => { e.preventDefault(); handleAiTranslate(); }}
          className="px-3 py-2 bg-cyan-50 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400 rounded-full flex items-center gap-2 border border-cyan-100 dark:border-cyan-800 transition-all hover:scale-105 active:scale-95"
        >
          <Languages size={20} />
          <span className="text-xs font-black uppercase">{langCode}</span>
        </button>

        <div className="h-5 w-[1px] bg-slate-200 dark:bg-slate-700 mx-1 hidden sm:block" />

        {user ? (
          <div className="relative">
            <button onClick={() => setMenuOpen(!menuOpen)} className="flex items-center gap-2 px-2 py-1.5 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-full shadow-sm">
              <div className="w-8 h-8 rounded-full bg-slate-100 overflow-hidden">
                {user.user_metadata?.avatar_url ? <img src={user.user_metadata.avatar_url} alt="profile" /> : <User size={18} />}
              </div>
              <ChevronDown size={16} className="text-slate-400" />
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-3 w-56 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-[24px] shadow-xl z-[100] p-2">
                <button onClick={handleLogout} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-bold text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl">
                  <LogOut size={18} /> Log Out
                </button>
              </div>
            )}
          </div>
        ) : (
          <button onClick={handleLogin} className="px-6 py-2.5 text-sm font-black text-white bg-slate-900 dark:bg-cyan-600 rounded-full hover:shadow-lg transition-all">
            Sign In
          </button>
        )}
      </div>
    </header>
  );
}
