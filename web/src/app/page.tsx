'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

// 기존 컴포넌트들
import Header from '@/components/Header';
import CategoryNav from '@/components/CategoryNav';
import InsightBanner from '@/components/InsightBanner';
import NewsFeed from '@/components/NewsFeed';
import Sidebar from '@/components/Sidebar';
import ArticleModal from '@/components/ArticleModal';

// [추가] 모바일용 플로팅 버튼
import MobileFloatingBtn from '@/components/MobileFloatingBtn';

export default function Home() {
  const [news, setNews] = useState<any[]>([]);
  const [category, setCategory] = useState('All');
  const [selectedArticle, setSelectedArticle] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // 1. 데이터 로드
  useEffect(() => { fetchNews(); }, []);

  const fetchNews = async () => {
    setLoading(true);
    // 사이드바의 통계와 전체 랭킹 분석을 위해 모든 기사를 가져옵니다.
    const { data, error } = await supabase
      .from('live_news')
      .select('*')
      .order('rank', { ascending: true });
    
    if (data && !error) {
      setNews(data);
    }
    setLoading(false);
  };

  // 2. 투표 로직
  const handleVote = async (id: string, type: 'likes' | 'dislikes') => {
    await supabase.rpc('increment_vote', { row_id: id, col_name: type });
    
    // 리스트 상태 즉시 반영
    setNews(prev => prev.map(item => 
      item.id === id ? { ...item, [type]: item[type] + 1 } : item
    ));

    // 상세 팝업 상태 즉시 반영
    if (selectedArticle?.id === id) {
      setSelectedArticle((prev: any) => ({ ...prev, [type]: prev[type] + 1 }));
    }
  };

  // 3. 필터링 로직 (상위 30개)
  const filteredNews = (category === 'All' 
    ? news 
    : news.filter(n => n.category === category)
  ).slice(0, 30);

  return (
    <main className="min-h-screen bg-[#f8fafc] text-slate-800 font-sans overflow-x-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        
        {/* 헤더 & 네비게이션 */}
        <Header />
        <CategoryNav active={category} setCategory={setCategory} />
        
        {/* AI 배너 */}
        <InsightBanner insight={news[0]?.insight} />

        {/* 메인 레이아웃 (Grid) */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mt-8">
          
          {/* [1] 뉴스 피드 영역 (PC: 왼쪽 3칸 / 모바일: 전체) */}
          <div className="col-span-1 md:col-span-3">
            <NewsFeed 
              news={filteredNews} 
              loading={loading} 
              onOpen={setSelectedArticle} 
            />
          </div>

          {/* [2] 사이드바 영역 (PC: 오른쪽 1칸 / 모바일: 숨김) */}
          {/* 'hidden md:block' 클래스가 모바일에서 이 부분을 숨겨줍니다 */}
          <div className="hidden md:block col-span-1">
            <Sidebar news={news} />
          </div>
          
        </div>
      </div>

      {/* [3] 기사 상세 모달 */}
      <ArticleModal 
        article={selectedArticle} 
        onClose={() => setSelectedArticle(null)} 
        onVote={handleVote} 
      />

      {/* [4] 모바일용 플로팅 버튼 (화면 우측 하단 고정) */}
      <MobileFloatingBtn />

    </main>
  );
}
