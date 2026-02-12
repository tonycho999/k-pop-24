'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { Lock, X, Zap } from 'lucide-react'; // 아이콘 추가

import Header from '@/components/Header';
import CategoryNav from '@/components/CategoryNav';
import InsightBanner from '@/components/InsightBanner';
import NewsFeed from '@/components/NewsFeed';
import Sidebar from '@/components/Sidebar';
import ArticleModal from '@/components/ArticleModal';
import MobileFloatingBtn from '@/components/MobileFloatingBtn';

export default function Home() {
  const [news, setNews] = useState<any[]>([]);
  const [category, setCategory] = useState('All');
  const [selectedArticle, setSelectedArticle] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isTranslating, setIsTranslating] = useState(false);
  const [user, setUser] = useState<any>(null); // 유저 상태
  
  // 웰컴 팝업 상태
  const [showWelcome, setShowWelcome] = useState(false);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  useEffect(() => {
    // 1. 유저 체크
    supabase.auth.getUser().then(({ data }) => setUser(data.user));
    
    // 2. 웰컴 팝업 체크 (localStorage)
    const hasSeenWelcome = localStorage.getItem('hasSeenWelcome_v1');
    if (!hasSeenWelcome) {
      // 1초 뒤에 팝업 띄움 (자연스럽게)
      setTimeout(() => setShowWelcome(true), 1000);
    }

    fetchNews();
    
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  const fetchNews = async () => {
    setLoading(true);
    const { data, error } = await supabase
      .from('live_news')
      .select('*')
      .order('score', { ascending: false });
    if (data && !error) { setNews(data); }
    setLoading(false);
  };

  // 웰컴 팝업 닫기
  const closeWelcome = () => {
    if (dontShowAgain) {
      localStorage.setItem('hasSeenWelcome_v1', 'true');
    }
    setShowWelcome(false);
  };

  // AI 번역 리스너
  useEffect(() => {
    const handleTranslate = async (e: any) => {
      const targetLang = e.detail;
      if (isTranslating || news.length === 0) return;
      setIsTranslating(true);
      
      try {
        const translatedNews = await Promise.all(news.map(async (item) => {
          const res = await fetch('/api/translate', {
            method: 'POST',
            body: JSON.stringify({ text: item.summary, targetLang }),
          });
          const data = await res.json();
          return { ...item, summary: data.translatedText || item.summary };
        }));
        setNews(translatedNews);
      } catch (err) { console.error(err); } 
      finally { setIsTranslating(false); }
    };
    window.addEventListener('ai-translate', handleTranslate);
    return () => window.removeEventListener('ai-translate', handleTranslate);
  }, [news, isTranslating]);

  const handleVote = async (id: string, type: 'likes' | 'dislikes') => {
    if (!user) return; // 비로그인 투표 방지
    await supabase.rpc('increment_vote', { row_id: id, col_name: type });
    setNews(prev => prev.map(item => item.id === id ? { ...item, [type]: item[type] + 1 } : item));
    if (selectedArticle?.id === id) {
      setSelectedArticle((prev: any) => ({ ...prev, [type]: prev[type] + 1 }));
    }
  };

  // [핵심] 로그인 여부에 따른 데이터 필터링
  const getFilteredNews = () => {
    let baseNews = category === 'All' 
      ? [...news].sort((a, b) => (b.score || 0) - (a.score || 0))
      : news.filter(n => n.category === category).sort((a, b) => (a.rank || 99) - (b.rank || 99));

    // 로그인 안 했으면 1개만 보여줌, 했으면 30개
    return user ? baseNews.slice(0, 30) : baseNews.slice(0, 1);
  };

  const filteredNews = getFilteredNews();

  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${location.origin}/auth/callback` },
    });
  };

  return (
    <main className="min-h-screen bg-[#f8fafc] text-slate-800 font-sans dark:bg-slate-950 dark:text-slate-200 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
        <Header />
        <CategoryNav active={category} setCategory={setCategory} />
        <InsightBanner insight={filteredNews[0]?.insight} />

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mt-8">
          <div className="col-span-1 md:col-span-3 relative">
            <NewsFeed news={filteredNews} loading={loading || isTranslating} onOpen={setSelectedArticle} />
            
            {/* [Paywall] 비로그인 유저용 잠금 화면 */}
            {!user && !loading && (
              <div className="mt-6 relative">
                 {/* 가짜 블러 카드들 */}
                 <div className="space-y-6 opacity-40 blur-sm select-none pointer-events-none grayscale">
                    <div className="h-40 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200" />
                    <div className="h-40 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200" />
                 </div>
                 
                 {/* 중앙 로그인 유도 */}
                 <div className="absolute inset-0 flex flex-col items-center justify-start pt-4">
                    <div className="bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl p-8 rounded-[32px] shadow-2xl border border-slate-100 dark:border-slate-800 text-center max-w-sm mx-auto">
                        <div className="w-14 h-14 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg shadow-cyan-200">
                           <Lock className="text-white" size={24} />
                        </div>
                        <h3 className="text-xl font-black text-slate-900 dark:text-white mb-2">
                           Want to see more?
                        </h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6 leading-relaxed">
                           Sign in to unlock <span className="font-bold text-cyan-600">Real-time K-Trends</span> & <span className="font-bold text-cyan-600">AI Analysis</span>.
                        </p>
                        <button 
                          onClick={handleLogin}
                          className="w-full py-3.5 bg-slate-900 dark:bg-cyan-600 text-white font-bold rounded-xl hover:scale-105 transition-transform shadow-xl"
                        >
                          Sign in with Google
                        </button>
                    </div>
                 </div>
              </div>
            )}
          </div>
          
          <div className="hidden md:block col-span-1">
            <Sidebar news={news} />
          </div>
        </div>
      </div>

      <ArticleModal article={selectedArticle} onClose={() => setSelectedArticle(null)} onVote={handleVote} />
      <MobileFloatingBtn />

 {/* [Welcome Popup] 신규 방문자용 팝업 (문구 수정됨) */}
      {showWelcome && !user && (
        <div className="fixed inset-0 z-[999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
           <div className="bg-white dark:bg-slate-900 w-full max-w-md rounded-[32px] p-1 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
              <div className="bg-gradient-to-br from-cyan-500 via-blue-600 to-indigo-600 p-8 rounded-[28px] text-center relative overflow-hidden">
                 {/* 배경 장식 */}
                 <div className="absolute top-0 left-0 w-full h-full opacity-20 bg-[url('https://grainy-gradients.vercel.app/noise.svg')]"></div>
                 
                 <div className="relative z-10">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-white/20 backdrop-blur-md mb-4 border border-white/30 shadow-lg">
                       <Zap className="text-yellow-300 fill-yellow-300" size={24} />
                    </div>
                    
                    {/* [수정] 헤드라인: 실시간성 강조 */}
                    <h2 className="text-2xl font-black text-white mb-3 tracking-tight leading-tight">
                       ⚡️ Real-time K-News Radar
                    </h2>
                    
                    {/* [수정] 본문: 3줄 가량의 핵심 메시지 */}
                    <div className="text-white/95 font-medium text-sm mb-8 leading-relaxed space-y-2 opacity-90">
                       <p>Stop waiting for late translations.</p>
                       <p>Access breaking <span className="text-yellow-300 font-bold">K-Pop & Drama</span> articles the second they are published in Korea.</p>
                       <p>Experience the world's fastest K-Trend source.</p>
                    </div>
                    
                    <button 
                       onClick={closeWelcome}
                       className="w-full py-4 bg-white text-slate-900 font-black text-lg rounded-2xl hover:bg-slate-50 hover:scale-[1.02] transition-all shadow-xl"
                    >
                       Start Monitoring Now
                    </button>
                 </div>
              </div>
              
              {/* 다시 보지 않기 체크박스 */}
              <div className="p-4 bg-white dark:bg-slate-900 text-center">
                 <label className="flex items-center justify-center gap-2 cursor-pointer group select-none">
                    <input 
                       type="checkbox" 
                       className="w-4 h-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500 transition-all"
                       checked={dontShowAgain}
                       onChange={(e) => setDontShowAgain(e.target.checked)}
                    />
                    <span className="text-xs font-bold text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300 transition-colors">
                       Don't show this again
                    </span>
                 </label>
              </div>
           </div>
        </div>
      )}
    </main>
  );
}
