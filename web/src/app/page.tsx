'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import Header from '@/components/Header';
import CategoryNav from '@/components/CategoryNav';
import InsightBanner from '@/components/InsightBanner';
import NewsFeed from '@/components/NewsFeed';
import Sidebar from '@/components/Sidebar';
import ArticleModal from '@/components/ArticleModal';

export default function Home() {
  const [news, setNews] = useState<any[]>([]);
  const [category, setCategory] = useState('All');
  const [selectedArticle, setSelectedArticle] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchNews(); }, []);

  const fetchNews = async () => {
    setLoading(true);
    // DB에 200개가 있어도 우선 전체를 가져옵니다. (사이드바 통계 등을 위해)
    const { data } = await supabase
      .from('live_news')
      .select('*')
      .order('rank', { ascending: true });
    
    if (data) setNews(data);
    setLoading(false);
  };

  const handleVote = async (id: string, type: 'likes' | 'dislikes') => {
    // 실시간 투표 반영 (RPC)
    await supabase.rpc('increment_vote', { row_id: id, col_name: type });
    
    // 로컬 상태 업데이트
    setNews(prev => prev.map(item => 
      item.id === id ? { ...item, [type]: item[type] + 1 } : item
    ));

    // 선택된 상세 기사가 있을 경우 함께 업데이트
    if (selectedArticle?.id === id) {
      setSelectedArticle((prev: any) => ({ ...prev, [type]: prev[type] + 1 }));
    }
  };

  /**
   * [핵심 로직] 필터링 및 슬라이싱
   * 1. 카테고리가 'All'이면 전체 뉴스에서 Top 30
   * 2. 특정 카테고리면 해당 장르에서 Top 30
   */
  const filteredNews = (category === 'All' 
    ? news 
    : news.filter(n => n.category === category)
  ).slice(0, 30);

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 font-sans overflow-x-hidden">
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* 상단부: K-Enter 24 로고 및 사용자 영역 */}
        <Header />

        {/* 중단부: 카테고리 메뉴 & AI 인사이트 */}
        <CategoryNav active={category} setCategory={setCategory} />
        
        {/* 인사이트 배너는 전체 뉴스 중 1위의 인사이트를 보여줌 */}
        <InsightBanner insight={news[0]?.insight} />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* 메인 기사 영역: 필터링된 30개만 전달 */}
          <NewsFeed 
            news={filteredNews} 
            loading={loading} 
            onOpen={setSelectedArticle} 
          />

          {/* 사이드바 영역: 전체 뉴스를 기반으로 통계/랭킹 계산 */}
          <Sidebar news={news} />
        </div>
      </div>

      {/* 기사 상세 모달 */}
      <ArticleModal 
        article={selectedArticle} 
        onClose={() => setSelectedArticle(null)} 
        onVote={handleVote} 
      />
    </div>
  );
}
