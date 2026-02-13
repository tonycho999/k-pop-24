'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { Lock, Zap } from 'lucide-react';

import Header from '@/components/Header';
import CategoryNav from '@/components/CategoryNav';
import InsightBanner from '@/components/InsightBanner';
import NewsFeed from '@/components/NewsFeed';
import Sidebar from '@/components/Sidebar';
import ArticleModal from '@/components/ArticleModal';
import MobileFloatingBtn from '@/components/MobileFloatingBtn';
import AdBanner from '@/components/AdBanner';
import { LiveNewsItem } from '@/types';

interface HomeClientProps {
  initialNews: LiveNewsItem[];
}

export default function HomeClient({ initialNews }: HomeClientProps) {
  
  // ✅ [보안 필터] 이미지 주소만 업그레이드 (링크 검사 제거)
  const filterSecureNews = (items: LiveNewsItem[]) => {
    if (!items) return [];
    return items.map(item => ({
        ...item,
        // 이미지 주소가 http면 https로 변환
        image_url: item.image_url ? item.image_url.replace('http://', 'https://') : null
      }));
  };

  // 1. 상태 관리
  const [news, setNews] = useState<LiveNewsItem[]>(filterSecureNews(initialNews));
  const [category, setCategory] = useState('All');
  const [selectedArticle, setSelectedArticle] = useState<LiveNewsItem | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [user, setUser] = useState<any>(null);
  
  const [showWelcome, setShowWelcome] = useState(false);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  // 2. 초기화 및 인증 체크
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user));
    
    const hasSeenWelcome = localStorage.getItem('hasSeenWelcome_v1');
    if (!hasSeenWelcome) setTimeout(() => setShowWelcome(true), 1000);

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  // 3. [핵심 수정] 카테고리 변경 시 소문자로 변환하여 DB 조회
  const handleCategoryChange = async (newCategory: string) => {
    setCategory(newCategory);
    setLoading(true);

    try {
      let query = supabase
        .from('live_news')
        .select('*')
        .order('rank', { ascending: true }) 
        .limit(30);

      // 'All'이 아닐 경우, 소문자로 변환해서 DB와 비교 (DB에는 k-pop으로 저장됨)
      if (newCategory !== 'All') {
        query = query.eq('category', newCategory.toLowerCase());
      }

      const { data, error } = await query;

      if (!error && data) {
        setNews(filterSecureNews(data as LiveNewsItem[]));
      }
    } catch (error) {
      console.error("Fetch Error:", error);
    } finally {
      setLoading(false);
    }
  };

  // 4. 좋아요 핸들러
  const handleVote = async (id: string, type: 'likes' | 'dislikes') => {
    if (!user) {
      alert("Please sign in to vote!");
      return;
    }

    if (type === 'dislikes') {
       alert("Dislike feature is coming soon!");
       return;
    }

    setNews(prev => prev.map(item => item.id === id ? { ...item, likes: item.likes + 1 } : item));
    if (selectedArticle?.id === id) {
      setSelectedArticle((prev: any) => ({ ...prev, likes: prev.likes + 1 }));
    }

    await supabase.rpc('increment_vote', { row_id: id });
  };

  // 5. [핵심 수정] 클라이언트 사이드 필터링도 소문자로 비교
  // (All일 때는 전체 표시, 아니면 카테고리 소문자로 비교)
  const displayNewsRaw = user ? news : news.slice(0, 1);
  const filteredDisplayNews = category === 'All' 
    ? displayNewsRaw 
    : displayNewsRaw.filter(item => item.category === category.toLowerCase());

  // 6. 이벤트 리스너
  useEffect(() => {
    const handleSearchModalOpen = (e: any) => {
      if (e.detail) setSelectedArticle(e.detail);
    };
    window.addEventListener('open-news-modal', handleSearchModalOpen);
    return () => window.removeEventListener('open-news-modal', handleSearchModalOpen);
  }, []);

  const closeWelcome = () => {
    if (dontShowAgain) localStorage.setItem('hasSeenWelcome_v1', 'true');
    setShowWelcome(false);
  };

  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  };

  return (
    <main className="min-h-screen bg-[#f8fafc] text-slate-800 font-sans dark:bg-slate-950 dark:text-slate-200 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-0">
        <Header />
        
        <div className="flex flex-col gap-0">
          <div className="mb-1">
             <CategoryNav active={category} setCategory={handleCategoryChange} />
          </div>
          
          <div className="mt-0"> 
             <InsightBanner insight={news.length > 0 ? news[0].summary : undefined} />
          </div>
          
          <div className="mt-2">
             <AdBanner />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mt-6">
          <div className="col-span-1 md:col-span-3 relative">
            {/* 필터링된 뉴스를 전달 */}
            <NewsFeed 
              news={filteredDisplayNews} 
              loading={loading || isTranslating} 
              onOpen={setSelectedArticle} 
            />
            
            {!user && !loading && news.length > 0 && (
              <div className="mt-6 relative">
                 <div className="space-y-6 opacity-40 blur-sm select-none pointer-events-none grayscale">
                    <div className="h-40 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200" />
                    <div className="h-40 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200" />
                 </div>
                 
                 <div className="absolute inset-0 flex flex-col items-center justify-start pt-4">
                    <div className="bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl p-8 rounded-[32px] shadow-2xl border border-slate-100 dark:border-slate-800 text-center max-w-sm mx-auto">
                        <div className="w-14 h-14 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg shadow-cyan-200">
                           <Lock className="text-white" size={24} />
                        </div>
                        <h3 className="text-xl font-black text-slate-900 dark:text-white mb-2">Want to see more?</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6 leading-relaxed">
                           Sign in to unlock <span className="font-bold text-cyan-600">Real-time K-Trends</span> & <span className="font-bold text-cyan-600">AI Analysis</span>.
                        </p>
                        <button onClick={handleLogin} className="w-full py-3.5 bg-slate-900 dark:bg-cyan-600 text-white font-bold rounded-xl hover:scale-105 transition-transform shadow-xl">
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
          // @ts-ignore
          onVote={handleVote} 
        />
      )}
      
      <MobileFloatingBtn />
      
      {showWelcome && !user && (
        <div className="fixed inset-0 z-[999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
           <div className="bg-white dark:bg-slate-900 w-full max-w-md rounded-[32px] p-1 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
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
              <div className="p-4 bg-white dark:bg-slate-900 text-center">
                 <label className="flex items-center justify-center gap-2 cursor-pointer group select-none">
                    <input type="checkbox" className="w-4 h-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500 transition-all" checked={dontShowAgain} onChange={(e) => setDontShowAgain(e.target.checked)} />
                    <span className="text-xs font-bold text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300 transition-colors">Don't show this again</span>
                 </label>
              </div>
           </div>
        </div>
      )}
    </main>
  );
}
