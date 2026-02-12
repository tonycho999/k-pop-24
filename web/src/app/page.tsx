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
    const { data } = await supabase.from('live_news').select('*').order('rank', { ascending: true });
    if (data) setNews(data);
    setLoading(false);
  };

  const handleVote = async (id: string, type: 'likes' | 'dislikes') => {
    await supabase.rpc('increment_vote', { row_id: id, col_name: type });
    setNews(prev => prev.map(item => item.id === id ? { ...item, [type]: item[type] + 1 } : item));
  };

  const filteredNews = category === 'All' ? news : news.filter(n => n.category === category);

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 font-sans overflow-x-hidden">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Header />
        <CategoryNav active={category} setCategory={setCategory} />
        <InsightBanner insight={news[0]?.insight} />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <NewsFeed 
            news={filteredNews} 
            loading={loading} 
            onOpen={setSelectedArticle} 
          />
          <Sidebar news={news} />
        </div>
      </div>

      <ArticleModal 
        article={selectedArticle} 
        onClose={() => setSelectedArticle(null)} 
        onVote={handleVote} 
      />
    </div>
  );
}
