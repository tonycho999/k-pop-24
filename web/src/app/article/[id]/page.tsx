import { supabase } from '@/lib/supabase';
import { Metadata } from 'next';
import Image from 'next/image';
import { notFound } from 'next/navigation';
import { Calendar, TrendingUp } from 'lucide-react';

import Header from '@/components/Header';
import RankingItem from '@/components/RankingItem';
import ArticleInteractive from './ArticleInteractive';
import ArticleTop from './ArticleTop';

// 💡 [핵심 1] 이 페이지를 Vercel Edge 네트워크(캐시)에 60초 동안 저장합니다. (속도 폭발의 비밀)
export const revalidate = 60; 

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const resolvedParams = await params;
  let { data: article } = await supabase.from('search_archive').select('*').eq('id', resolvedParams.id).single();
  if (!article) {
    const { data: liveArticle } = await supabase.from('live_news').select('*').eq('id', resolvedParams.id).single();
    article = liveArticle;
  }
  if (!article) return { title: 'Not Found | K-ENTER 24' };
  return {
    title: `${article.title} | K-ENTER 24`,
    description: article.summary,
    openGraph: {
      title: article.title,
      description: article.summary,
      images: [article.image_url || '/default-og.png'],
    },
  };
}

export default async function ArticlePage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params;
  const articleId = resolvedParams.id;

  // 💡 [핵심 2] 기사 데이터 가져오는 작업과 랭킹 가져오는 작업을 분리합니다.
  const fetchArticle = async () => {
    let { data } = await supabase.from('search_archive').select('*').eq('id', articleId).single();
    if (!data) {
      const { data: liveArticle } = await supabase.from('live_news').select('*').eq('id', articleId).single();
      data = liveArticle;
    }
    return data;
  };

  const fetchRankings = async () => {
    const { data } = await supabase.from('live_rankings').select('*').order('score', { ascending: false }).limit(10);
    return data;
  };

  // 💡 [핵심 3] Promise.all을 사용해 DB 조회를 '동시에' 실행시켜 시간을 반으로 줄입니다.
  const [article, rankings] = await Promise.all([
    fetchArticle(),
    fetchRankings()
  ]);

  // 기사가 없으면 404
  if (!article) {
    notFound(); 
  }

  const secureImageUrl = article.image_url ? article.image_url.replace('http://', 'https://') : null;

  return (
    <main className="min-h-screen bg-[#f8fafc] text-slate-800 font-sans overflow-x-hidden">
      {/* ---------- 이 아래 HTML 렌더링 부분은 기존 코드와 100% 동일합니다 ---------- */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-0 w-full">
        <Header />
        <ArticleTop insight={article.summary} />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mt-2 w-full pb-20">
          
          <div className="col-span-1 md:col-span-3">
            <article className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
              {secureImageUrl && (
                <div className="relative w-full h-64 sm:h-[450px] bg-slate-900 overflow-hidden">
                  <div className="absolute inset-0 opacity-40">
                    <Image src={secureImageUrl} alt="blur background" fill className="object-cover blur-2xl scale-110" priority />
                  </div>
                  <Image src={secureImageUrl} alt={article.title} fill className="object-contain drop-shadow-2xl z-10 p-2 sm:p-4" priority />
                </div>
              )}
              
              <div className="p-6 sm:p-10">
                <div className="mb-6 flex items-center gap-3">
                  <span className="px-3 py-1 bg-cyan-50 text-cyan-600 border border-cyan-100 text-xs font-black uppercase rounded-lg shadow-sm">
                    {article.category}
                  </span>
                  <span className="flex items-center gap-1 text-slate-400 text-sm font-bold">
                    <Calendar size={14} />
                    {new Date(article.created_at).toLocaleDateString()}
                  </span>
                </div>
                
                <h1 className="text-3xl sm:text-4xl font-black text-slate-900 mb-8 leading-tight tracking-tight">
                  {article.title}
                </h1>
                
                <div className="text-lg text-slate-700 leading-relaxed whitespace-pre-wrap font-medium">
                  {article.summary}
                </div>

                <ArticleInteractive article={article} />
              </div>
            </article>
          </div>

          <div className="hidden md:block col-span-1">
            <div className="sticky top-24">
              <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
                <div className="flex items-center gap-2 mb-4 pb-4 border-b border-slate-100">
                  <TrendingUp className="text-cyan-500" size={20} />
                  <h3 className="font-black text-slate-800 tracking-tight">TOP 10 TRENDS</h3>
                </div>
                
                <div className="flex flex-col">
                  {rankings?.map((item, index) => (
                    <RankingItem key={item.id} rank={index + 1} item={item} />
                  ))}
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}
