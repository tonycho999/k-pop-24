'use client';

import { useEffect, useState, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { Lock, Zap, X } from 'lucide-react';
import { User } from '@supabase/supabase-js';
import { useRouter } from 'next/navigation'; // ✅ 페이지 이동을 위한 라우터 추가

import Header from '@/components/Header';
import CategoryNav from '@/components/CategoryNav';
import InsightBanner from '@/components/InsightBanner';
import NewsFeed from '@/components/NewsFeed';
import Sidebar from '@/components/Sidebar';
import MobileFloatingBtn from '@/components/MobileFloatingBtn';
import AdBanner from '@/components/AdBanner';
import { LiveNewsItem } from '@/types';

// 🗑️ 모달 컴포넌트(ArticleModal) 임포트 삭제 완료

const WELCOME_MODAL_KEY = 'hasSeenWelcome_v1';

interface HomeClientProps {
  initialNews: LiveNewsItem[];
}

export default function HomeClient({ initialNews }: HomeClientProps) {
  const router = useRouter(); // ✅ 라우터 초기화
  
  const filterSecureNews = useCallback((items: LiveNewsItem[]) => {
    if (!items) return [];
    return items.map(item => ({
        ...item,
        image_url: item.image_url ? item.image_url.replace('http://', 'https://') : null
      }));
  }, []);

  const [news, setNews] = useState<LiveNewsItem[]>(filterSecureNews(initialNews));
  const [category, setCategory] = useState('All');
  const [loading, setLoading] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [showWelcome, setShowWelcome] = useState(false);
  const [dontShowAgain, setDontShowAgain] = useState(false);
  
  // 🗑️ 모달, 로그인 팝업 관련 상태 전부 삭제 완료

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

  const handleCategoryChange = useCallback(async (newCategory: string) => {
    setCategory(newCategory);
    setLoading(true);

    try {
      let query = supabase.from('live_news').select('*');

      if (newCategory === 'All') {
        query = query.order('score', { ascending: false }).limit(30);
      } else if (newCategory === 'K-Culture') {
        query = query
          .in('category', ['k-food', 'k-beauty', 'k-fashion', 'k-lifestyle'])
          .order('score', { ascending: false })
          .limit(40);
      } else {
        const dbCategory = newCategory.toLowerCase();
        query = query
          .eq('category', dbCategory)
          .order('score', { ascending: false })
          .limit(30);
      }

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

  // ✅ [수정] 기사 클릭 시 무조건 기사 전용 페이지(URL)로 이동시킵니다.
  // (로그인 체크는 이동한 /article 페이지 내에서 처리하는 것이 SEO 정석입니다)
  const handleArticleClick = useCallback((item: LiveNewsItem) => {
    router.push(`/article/${item.id}`);
  }, [router]);

  const closeWelcome = () => {
    if (dontShowAgain) localStorage.setItem(WELCOME_MODAL_KEY, 'true');
    setShowWelcome(false);
  };

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
          <div className={`relative w-full ${category === 'K-Culture' ? 'col-span-1 md:col-span-4' : 'col-span-1 md:col-span-3'}`}>
            
            <NewsFeed 
              news={news} 
              loading={loading || isTranslating} 
              onOpen={handleArticleClick} // ✅ 클릭 시 router.push 발동
              category={category}
            />
          </div>
          
          {category !== 'K-Culture' && (
            <div className="hidden md:block col-span-1">
              <Sidebar news={news} category={category} />
            </div>
          )}
        </div>
      </div>

      {/* 🗑️ ArticleModal 렌더링 부분 삭제 완료 */}
      {/* 🗑️ 로그인 팝업 모달 렌더링 부분 삭제 완료 */}
      
      <MobileFloatingBtn news={news} category={category} />

      {/* 기존 웰컴 팝업 유지 */}
      {showWelcome && !user && (
        <div className="fixed inset-0 z-[998] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
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
