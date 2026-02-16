'use client';

import { useEffect, useState, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { Lock, Zap } from 'lucide-react';
import { User } from '@supabase/supabase-js';

import Header from '@/components/Header';
import CategoryNav from '@/components/CategoryNav';
import InsightBanner from '@/components/InsightBanner';
import NewsFeed from '@/components/NewsFeed';
import Sidebar from '@/components/Sidebar';
import ArticleModal from '@/components/ArticleModal';
import MobileFloatingBtn from '@/components/MobileFloatingBtn';
import AdBanner from '@/components/AdBanner';
import { LiveNewsItem } from '@/types';

const WELCOME_MODAL_KEY = 'hasSeenWelcome_v1';

interface HomeClientProps {
  initialNews: LiveNewsItem[];
}

export default function HomeClient({ initialNews }: HomeClientProps) {
  
  // HTTP 이미지를 HTTPS로 변환하는 유틸리티
  const filterSecureNews = useCallback((items: LiveNewsItem[]) => {
    if (!items) return [];
    return items.map(item => ({
        ...item,
        image_url: item.image_url ? item.image_url.replace('http://', 'https://') : null
      }));
  }, []);

  const [news, setNews] = useState<LiveNewsItem[]>(filterSecureNews(initialNews));
  const [category, setCategory] = useState('All');
  const [selectedArticle, setSelectedArticle] = useState<LiveNewsItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [showWelcome, setShowWelcome] = useState(false);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  // 1. 유저 인증 및 웰컴 모달 체크
  useEffect(() => {
    const checkUser = async () => {
      const { data } = await supabase.auth.getUser();
      setUser(data.user);
    };
    checkUser();
    
    const hasSeenWelcome = localStorage.getItem(WELCOME_MODAL_KEY);
    if (!hasSeenWelcome) {
        const timer = setTimeout(() => setShowWelcome(true), 1000);
        return () => clearTimeout(timer);
    }

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  // 2. 카테고리 변경 핸들러 (핵심 수정 부분)
  const handleCategoryChange = useCallback(async (newCategory: string) => {
    setCategory(newCategory);
    setLoading(true);

    try {
      let query = supabase.from('live_news').select('*');

      if (newCategory === 'All') {
        // 전체보기: 점수(score) 높은 순
        query = query.order('score', { ascending: false });
      } else {
        // ✅ [핵심 수정] UI는 'K-Pop'이지만 DB는 'k-pop'이므로 소문자 변환 필수!
        const dbCategory = newCategory.toLowerCase();
        
        query = query
          .eq('category', dbCategory)
          .order('score', { ascending: false }); // 랭킹 대신 점수순 정렬
      }

      // 30개 제한
      query = query.limit(30);

      const { data, error } = await query;

      if (error) {
        console.error("Supabase Error:", error);
        throw error;
      }

      if (data) {
        setNews(filterSecureNews(data as LiveNewsItem[]));
      }
    } catch (error) {
      console.error("Fetch Error Details:", error);
    } finally {
      setLoading(false);
    }
  }, [filterSecureNews]);

  // 3. 투표 핸들러
  const handleVote = useCallback(async (id: string, type: 'likes' | 'dislikes') => {
    if (!user) {
      alert("Please sign in to vote!");
      return;
    }

    if (type === 'dislikes') {
       alert("Dislike feature is coming soon!");
       return;
    }

    setNews(prev => prev.map(item => item.id === id ? { ...item, likes: (item.likes || 0) + 1 } : item));
    
    setSelectedArticle((prev) => {
        if (prev && prev.id === id) {
            return { ...prev, likes: (prev.likes || 0) + 1 };
        }
        return prev;
    });

    await supabase.rpc('increment_vote', { row_id: id });
  }, [user]);

  // 4. 모달 이벤트 리스너
  useEffect(() => {
    const handleSearchModalOpen = (e: CustomEvent<LiveNewsItem>) => {
      if (e.detail) setSelectedArticle(e.detail);
    };
    window.addEventListener('open-news-modal', handleSearchModalOpen as EventListener);
    return () => window.removeEventListener('open-news-modal', handleSearchModalOpen as EventListener);
  }, []);

  const closeWelcome = () => {
    if (dontShowAgain) localStorage.setItem(WELCOME_MODAL_KEY, 'true');
    setShowWelcome(false);
  };

  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  };

  // 로그인 안 한 유저에게는 1개만 보여주기 (블러 처리용)
  // 이미 API에서 필터링해서 가져왔으므로 여기서는 추가 필터링 없이 그대로 사용하거나,
  // 'All' 상태에서 클라이언트 사이드 필터링이 필요하다면 아래 로직 유지.
  // 현재 로직: category state와 상관없이 news state는 이미 fetch된 데이터임.
  const displayedNews = user ? news : news.slice(0, 1);

  return (
    <main className="min-h-screen bg-[#f8fafc] text-slate-800 font-sans overflow-x-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-0 w-full">
        <Header />
        
        <div className="flex flex-col gap-0 w-full">
          <div className="mb-1 w-full overflow-hidden">
             <CategoryNav active={category} setCategory={handleCategoryChange} />
          </div>
          
          <div className="mt-0 w-full"> 
             <InsightBanner insight={news.length > 0 ? news[0].summary : undefined} />
          </div>
          
          <div className="mt-2 w-full">
             <AdBanner />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mt-6 w-full">
          <div className="col-span-1 md:col-span-3 relative w-full">
            <NewsFeed 
              news={displayedNews} 
              loading={loading || isTranslating} 
              onOpen={setSelectedArticle} 
            />
            
            {/* 로그인 안 했을 때 블러 처리 영역 */}
            {!user && !loading && news.length > 0 && (
              <div className="mt-4 sm:mt-6 relative w-full">
                 <div className="space-y-4 sm:space-y-6 opacity-40 blur-md select-none pointer-events-none grayscale">
                    <div className="h-32 sm:h-40 bg-white rounded-2xl sm:rounded-3xl border border-slate-200" />
                    <div className="h-32 sm:h-40 bg-white rounded-2xl sm:rounded-3xl border border-slate-200" />
                 </div>
                 
                 <div className="absolute inset-0 flex flex-col items-center justify-center px-4">
                    <div className="bg-white/95 backdrop-blur-2xl p-6 sm:p-8 rounded-[24px] sm:rounded-[32px] shadow-2xl border border-slate-100 text-center w-full max-w-[320px] mx-auto">
                        <div className="w-12 h-12 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-3 shadow-lg shadow-cyan-200">
                           <Lock className="text-white" size={20} />
                        </div>
                        <h3 className="text-lg font-black text-slate-900 mb-1 tracking-tight">Want to see more?</h3>
                        <p className="text-xs text-slate-500 mb-5 leading-relaxed">
                           Sign in to unlock <span className="font-bold text-cyan-600">Real-time K-Trends</span> & <span className="font-bold text-cyan-600">AI Analysis</span>.
                        </p>
                        <button onClick={handleLogin} className="w-full py-3 bg-slate-900 text-white text-sm font-bold rounded-xl active:scale-95 transition-transform shadow-xl">
                          Sign in with Google
                        </button>
                    </div>
                 </div>
              </div>
            )}
          </div>
          
          <div className="hidden md:block col-span-1">
            <Sidebar news={news} category={category} />
          </div>
        </div>
      </div>

      {selectedArticle && (
        <ArticleModal 
          article={selectedArticle} 
          onClose={() => setSelectedArticle(null)} 
          onVote={handleVote}
        />
      )}
      
      <MobileFloatingBtn />
      
      {showWelcome && !user && (
        <div className="fixed inset-0 z-[999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
           <div className="bg-white w-full max-w-md rounded-[32px] p-1 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
              <div className="bg-gradient-to-br from-cyan-500 via-blue-600 to-indigo-600 p-8 rounded-[28px] text-center relative overflow-hidden">
                 <div className="absolute top-0 left-0 w-full h-full opacity-20 bg-[url('https://grainy-gradients.vercel.app/noise.svg')]"></div>
                 <div className="relative z-10">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-white/20 backdrop-blur-md mb-4 border border-white/30 shadow-lg">
                       <Zap className="text-yellow-300 fill-yellow-300" size={24} />
                    </div>
                    <h2 className="text-2xl font-black text-white mb-3 tracking-tight leading-tight">⚡️ Real-time K-News Radar</h2>
                    <div className="text-white/95 font-medium text-sm mb-8 leading-relaxed space-y-2 opacity-90">
                       <p>Stop waiting for late translations.</p>
                       <p>Access breaking <span className="text-yellow-300 font-bold">K-Pop & Drama</span> articles the second they are published in Korea.</p>
                       <p>Experience the world's fastest K-Trend source.</p>
                    </div>
                    <button onClick={closeWelcome} className="w-full py-4 bg-white text-slate-900 font-black text-lg rounded-2xl hover:bg-slate-50 hover:scale-[1.02] transition-all shadow-xl">
                       Start Monitoring Now
                    </button>
                 </div>
              </div>
              <div className="p-4 bg-white text-center">
                 <label className="flex items-center justify-center gap-2 cursor-pointer group select-none">
                    <input type="checkbox" className="w-4 h-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500 transition-all" checked={dontShowAgain} onChange={(e) => setDontShowAgain(e.target.checked)} />
                    <span className="text-xs font-bold text-slate-400 group-hover:text-slate-600 transition-colors">Don't show this again</span>
                 </label>
              </div>
           </div>
        </div>
      )}
    </main>
  );
}
