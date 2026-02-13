'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { 
  User, LogOut, Settings, ChevronDown, 
  ShieldCheck, Sun, Moon, Languages 
} from 'lucide-react';

export default function Header() {
  const [user, setUser] = useState<any>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [langCode, setLangCode] = useState('EN'); 

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user));
    
    if (localStorage.getItem('theme') === 'dark' || 
        (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    }

    const browserLang = navigator.language.split('-')[0].toUpperCase();
    setLangCode(browserLang === 'KO' ? 'EN' : browserLang);

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  const toggleDarkMode = () => {
    if (isDark) {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    } else {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    }
    setIsDark(!isDark);
  };

  const handleAiTranslate = () => {
    if (langCode === 'EN') return; 
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
    <header className="flex justify-between items-center mb-6 py-2 border-b border-slate-100 dark:border-slate-800 transition-colors">
      {/* 좌측: 로고 & 실시간 상태 */}
      <div className="flex items-center gap-2 sm:gap-4">
        <div className="w-[150px] sm:w-[160px] h-[90px] sm:h-[100px] flex items-center justify-center overflow-hidden">
          <img src="/logo.png" alt="Logo" className="w-full h-full object-contain" />
        </div>
        
        {/* Live 상태 표시 (모바일에서도 보이도록 flex 조정) */}
        <div className="flex flex-col ml-1 sm:ml-2 border-l border-slate-200 dark:border-slate-700 pl-2 sm:pl-3">
             <div className="flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
                </span>
                <span className="text-[9px] sm:text-[10px] font-black text-cyan-500 uppercase tracking-tighter">Live</span>
             </div>
             <span className="text-[10px] sm:text-[11px] font-bold text-slate-400 dark:text-slate-500 leading-none mt-0.5 whitespace-nowrap">
               1,240 Articles Today
             </span>
        </div>
      </div>

      {/* 우측: 버튼 그룹 */}
      <div className="flex items-center gap-2 relative">
        <button onClick={toggleDarkMode} className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400">
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {/* 언어 설정 버튼 (항상 보임) */}
        <button 
          onClick={handleAiTranslate}
          className="px-2 sm:px-3 py-1.5 bg-cyan-50 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400 rounded-full flex items-center gap-1.5 border border-cyan-100 dark:border-cyan-800 transition-all active:scale-95"
          title={`Translate to ${langCode}`}
        >
          <Languages size={16} />
          <span className="text-[10px] sm:text-[11px] font-black uppercase">{langCode}</span>
        </button>

        <div className="h-4 w-[1px] bg-slate-200 dark:bg-slate-700 mx-1 hidden sm:block" />

        {user ? (
          <div className="relative">
            <button onClick={() => setMenuOpen(!menuOpen)} className="flex items-center gap-2 px-2 sm:px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-full">
              <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-slate-100 overflow-hidden">
                {user.user_metadata?.avatar_url ? <img src={user.user_metadata.avatar_url} alt="profile" /> : <User size={16} />}
              </div>
              <span className="hidden sm:inline text-xs font-bold text-slate-700 dark:text-slate-300 truncate max-w-[80px]">
                {user.email?.split('@')[0]}
              </span>
              <ChevronDown size={14} />
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-3 w-48 sm:w-56 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-[24px] shadow-xl z-[100] p-2">
                <button onClick={handleLogout} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-bold text-red-500 hover:bg-red-50 rounded-xl">
                  <LogOut size={18} /> Log Out
                </button>
              </div>
            )}
          </div>
        ) : (
          <button onClick={handleLogin} className="px-4 sm:px-6 py-2 text-xs sm:text-sm font-black text-white bg-slate-900 dark:bg-cyan-600 rounded-full hover:bg-cyan-500 transition-all shadow-lg shadow-cyan-900/20 whitespace-nowrap">
            Sign In
          </button>
        )}
      </div>
    </header>
  );
}
