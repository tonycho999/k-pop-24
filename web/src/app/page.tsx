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
    // [수정] 초기 로딩 시 모든 데이터를 가져오되, 기본적으로 '점수(score)' 순으로 가져옵니다.
    // 이렇게 하면 'All' 탭에서 가장 핫한 뉴스가 먼저 보입니다.
    const { data, error } = await supabase
      .from('live_news')
      .select('*')
      .order('score', { ascending: false }); // 전체 점수 내림차순
      
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

  // 3. [핵심 수정] 필터링 및 정렬 로직 분리
  const getFilteredNews = () => {
    if (category === 'All') {
      // [All Trends]: 카테고리 상관없이 전체 기사를 '점수(Score)' 높은 순으로 정렬
      // 원본 배열을 복사([...news])하여 정렬해야 원본이 훼손되지 않음
      return [...news]
        .sort((a, b) => (b.score || 0) - (a.score || 0))
        .slice(0, 30);
    } else {
      // [Specific Category]: 해당 카테고리만 남기고 '랭크(Rank)' 오름차순(1위->30위) 정렬
      return news
        .filter(n => n.category === category)
        .sort((a, b) => (a.rank || 99) - (b.rank || 99))
        .slice(0, 30);
    }
  };

  const filteredNews = getFilteredNews();

  return (
    <main className="min-h-screen bg-[#f8fafc] text-slate-800 font-sans overflow-x-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        
        {/* 헤더 & 네비게이션 */}
        <Header />
        <CategoryNav active={category} setCategory={setCategory} />
        
        {/* AI 배너: 현재 보고 있는 리스트의 1위 기사 Insight를 보여줌 */}
        <InsightBanner insight={filteredNews[0]?.insight} />

        {/* 메인 레이아웃 (Grid) */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mt-8">
          
          {/* [1] 뉴스 피드 영역 */}
          <div className="col-span-1 md:col-span-3">
            <NewsFeed 
              news={filteredNews} 
              loading={loading} 
              onOpen={setSelectedArticle} 
            />
          </div>

          {/* [2] 사이드바 영역 */}
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

      {/* [4] 모바일용 플로팅 버튼 */}
      <MobileFloatingBtn />

    </main>
  );
}
