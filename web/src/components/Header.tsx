'use client';

import { useEffect, useState, useRef } from 'react';
import { supabase } from '@/lib/supabase';
import { 
  User, LogOut, ChevronDown, 
  Sun, Moon, Languages, Search, X, ExternalLink 
} from 'lucide-react';

export default function Header() {
  const [user, setUser] = useState<any>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [langCode, setLangCode] = useState('EN'); 
  const [totalCount, setTotalCount] = useState(0);

  // [검색 관련 상태]
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

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

    // 전체 카운트 가져오기
    const fetchTotalCount = async () => {
      try {
        const live = await supabase.from('live_news').select('*', { count: 'exact', head: true });
        const archive = await supabase.from('search_archive').select('*', { count: 'exact', head: true });
        const total = (live.count || 0) + (archive.count || 0);
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

  // [검색창 포커스]
  useEffect(() => {
    if (isSearchOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isSearchOpen]);

  // [핵심] 실시간 검색 로직 (디바운싱 적용)
  // 사용자가 타자를 칠 때는 기다리다가, 300ms(0.3초) 동안 입력이 없으면 검색 실행
  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (!searchQuery.trim()) {
        setSearchResults([]); // 검색어 없으면 결과 초기화
        return;
      }

      setIsSearching(true);
      try {
        // 1. Live News 검색
        const { data: liveData } = await supabase
          .from('live_news')
          .select('*')
          .ilike('title', `%${searchQuery}%`)
          .limit(5);

        // 2. Archive 검색
        const { data: archiveData } = await supabase
          .from('search_archive')
          .select('*')
          .ilike('title', `%${searchQuery}%`)
          .limit(5);

        // 결과 합치기
        const combined = [
          ...(liveData || []).map(item => ({ ...item, type: 'LIVE' })),
          ...(archiveData || []).map(item => ({ ...item, type: 'ARCHIVE' }))
        ];
        setSearchResults(combined);
      } catch (err) {
        console.error(err);
      } finally {
        setIsSearching(false);
      }
    }, 300); // 0.3초 지연

    // 타자를 계속 치면 이전 타이머를 취소해서 DB 호출을 막음
    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  // 엔터 키 눌렀을 때 새로고침 방지용
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
  };

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
    <>
      <header className="flex justify-between items-center py-5 mb-1 border-b border-slate-100 dark:border-slate-800 transition-colors relative z-50 bg-white dark:bg-slate-950">
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
                 {totalCount > 0 ? totalCount.toLocaleString() : 'Scanning...'} Monitoring
               </span>
          </div>
        </div>

        <div className="flex items-center gap-2 relative">
          <button 
            onClick={() => setIsSearchOpen(true)}
            className="p-2.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
          >
            <Search size={22} />
          </button>

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

      {/* 검색 모달 */}
      {isSearchOpen && (
        <div className="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-sm flex items-start justify-center pt-20 px-4">
          <div className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
            
            {/* 검색 입력창 (onSubmit 수정됨) */}
            <form onSubmit={handleSearchSubmit} className="flex items-center p-4 border-b border-slate-100 dark:border-slate-800">
              <Search className="text-slate-400 mr-3" size={24} />
              <input 
                ref={searchInputRef}
                type="text" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search K-Pop, Drama, Actors..." 
                className="flex-1 bg-transparent text-xl font-bold text-slate-900 dark:text-white outline-none placeholder:text-slate-300"
              />
              <button type="button" onClick={() => setIsSearchOpen(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full">
                <X size={24} className="text-slate-500" />
              </button>
            </form>

            {/* 검색 결과 영역 */}
            <div className="overflow-y-auto p-4">
              {isSearching ? (
                <div className="text-center py-10 text-slate-400">Searching...</div>
              ) : searchResults.length > 0 ? (
                <div className="space-y-4">
                  {searchResults.map((item) => (
                    <div 
                      key={item.id} 
                      onClick={() => {
                        setIsSearchOpen(false); // 검색창 닫기
                        // 메인 페이지에 모달 열라고 신호 보내기
                        window.dispatchEvent(new CustomEvent('open-news-modal', { detail: item }));
                      }}
                      className="block p-4 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group cursor-pointer"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <span className={`text-[10px] font-black px-2 py-0.5 rounded-full uppercase mb-2 inline-block ${
                            item.type === 'LIVE' ? 'bg-red-100 text-red-600' : 'bg-yellow-100 text-yellow-600'
                          }`}>
                            {item.type === 'LIVE' ? '🔥 Live' : '🏆 Archive'}
                          </span>
                          <h4 className="font-bold text-slate-800 dark:text-slate-200 group-hover:text-cyan-600 transition-colors">
                            {item.title}
                          </h4>
                          <p className="text-sm text-slate-400 mt-1 line-clamp-1">{item.summary}</p>
                        </div>
                        <ExternalLink size={16} className="text-slate-300 group-hover:text-cyan-500 opacity-0 group-hover:opacity-100 transition-all" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : searchQuery ? (
                <div className="text-center py-10 text-slate-400">
                  No results found for "{searchQuery}"
                </div>
              ) : (
                <div className="text-center py-10 text-slate-400">
                  Type to search...
                </div>
              )}
            </div>

            <div className="p-3 bg-slate-50 dark:bg-slate-950/50 text-center text-xs text-slate-400 border-t border-slate-100 dark:border-slate-800">
              Press Enter to search
            </div>
          </div>
        </div>
      )}
    </>
  );
}
