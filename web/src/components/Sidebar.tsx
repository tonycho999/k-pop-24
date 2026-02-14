'use client';

import { useEffect, useState, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { Lock, Zap, Globe, Menu, X } from 'lucide-react';
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

// localStorage 키 상수화
const WELCOME_MODAL_KEY = 'hasSeenWelcome_v1';

interface HomeClientProps {
  initialNews: LiveNewsItem[];
}

export default function HomeClient({ initialNews }: HomeClientProps) {
  
  // ✅ [보안 필터] 이미지 주소만 업그레이드 (http -> https)
  const filterSecureNews = useCallback((items: LiveNewsItem[]) => {
    if (!items) return [];
    return items.map(item => ({
        ...item,
        image_url: item.image_url ? item.image_url.replace('http://', 'https://') : null
      }));
  }, []);

  // 1. 상태 관리
  const [news, setNews] = useState<LiveNewsItem[]>(filterSecureNews(initialNews));
  const [category, setCategory] = useState('All');
  const [selectedArticle, setSelectedArticle] = useState<LiveNewsItem | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  
  const [showWelcome, setShowWelcome] = useState(false);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  // 2. 초기화 및 인증 체크
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

  // 3. [핵심 로직] 카테고리 변경 시 데이터 조회
  const handleCategoryChange = useCallback(async (newCategory: string) => {
    setCategory(newCategory);
    setLoading(true);

    try {
      let query = supabase.from('live_news').select('*');

      if (newCategory === 'All') {
        // All: 평점(score) 높은 순 (트렌드)
        query = query.order('score', { ascending: false });
      } else {
        // 개별 카테고리: DB에 저장된 대소문자 그대로 비교 (K-Entertain 등) + 랭킹순
        query = query
          .eq('category', newCategory)
          .order('rank', { ascending: true });
      }

      // 30개 제한
      query = query.limit(30);

      const { data, error } = await query;

      if (!error && data) {
        setNews(filterSecureNews(data as LiveNewsItem[]));
      }
    } catch (error) {
      console.error("Fetch Error:", error);
    } finally {
      setLoading(false);
    }
  }, [filterSecureNews]);

  // 4. 좋아요 핸들러
  const handleVote = useCallback(async (id: string, type: 'likes' | 'dislikes') => {
    if (!user) {
      alert("Please sign in to vote!");
      return;
    }

    if (type === 'dislikes') {
       alert("Dislike feature is coming soon!");
       return;
    }

    // UI 즉시 반영 (Optimistic Update)
    setNews(prev => prev.map(item => item.id === id ? { ...item, likes: item.likes + 1 } : item));
    
    // 모달이 열려있다면 모달 내부 상태도 업데이트
    setSelectedArticle((prev) => {
        if (prev && prev.id === id) {
            return { ...prev, likes: prev.likes + 1 };
        }
        return prev;
    });

    // DB 업데이트
    await supabase.rpc('increment_vote', { row_id: id });
  }, [user]);

  // 5. 이벤트 리스너 (모달 열기 등)
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

  // 렌더링용: 카테고리 필터링 (이미 DB에서 필터링해왔지만, 클라이언트 상태 동기화를 위해 한 번 더 확인)
  const filteredDisplayNews = category === 'All' 
    ? news 
    : news.filter(item => item.category === category);
  
  // 비로그인 유저: 1개만 보여줌
  const displayedNews = user ? filteredDisplayNews : filteredDisplayNews.slice(0, 1);

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
          {/* 뉴스 피드 영역 (모바일: 전체, PC: 왼쪽 3칸) */}
          <div className="col-span-1 md:col-span-3 relative w-full">
            <NewsFeed 
              news={displayedNews} 
              loading={loading || isTranslating} 
              onOpen={setSelectedArticle} 
            />
            
            {/* 로그인 유도 블러 처리 (비로그인 시) */}
            {!user && !loading && news.length > 0 && (
              <div className="mt-4 sm:mt-6 relative w-full">
                 <div className="space-y-4 sm:space-y-6 opacity-40 blur-md select-none pointer-events-none grayscale">
                    <div className="h-32 sm:h-40 bg-white rounded-2xl sm:rounded-3
