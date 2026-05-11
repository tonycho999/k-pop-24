import { supabase } from '@/lib/supabase';
import { Metadata } from 'next';
import Image from 'next/image';
import { notFound } from 'next/navigation';
import { Calendar, TrendingUp } from 'lucide-react';

import Header from '@/components/Header';
import RankingItem from '@/components/RankingItem';
import ArticleInteractive from './ArticleInteractive';
import ArticleTop from './ArticleTop'; // ✅ 방금 만든 상단 배너 컴포넌트 불러오기

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

  let { data: article } = await supabase.from('search_archive').select('*').eq('id', articleId).single();
  if (!article) {
    const { data: liveArticle } = await supabase.from('live_news').select('*').eq('id', articleId).single();
    article = liveArticle;
  }

  if (!article) {
    notFound(); 
  }

  const { data: rankings } = await supabase
    .from('live_rankings')
    .select('*')
    .order('score', { ascending: false })
    .limit(10);

  const secureImageUrl = article.image_url ? article.image_url.replace('http://', 'https://') : null;

  return (
    <main className="min-h-screen bg-[#f8fafc] text-slate-800 font-sans overflow-x-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-0 w-full">
        
        {/* 🧭 상단 Header */}
        <Header />

        {/* 🚀 [추가됨] 상단 메뉴 + 인사이트 배너 + 광고 배너 */}
        <ArticleTop insight={article.summary} />

        {/* 4단 그리드 레이아웃 (기사 3 : 랭킹 1) */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mt-2 w-full pb-20">
          
          {/* 📰 좌측 (3칸 차지): 기사 본문 영역 */}
          <div className="col-span-1 md:col-span-3">
            <article className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
            {secureImageUrl && (
              <div className="relative w-full h-64 sm:h-[450px] bg-slate-900 overflow-hidden">
                {/* 1. 뒷배경: 이미지를 꽉 채우고 블러(흐림) 처리를 해서 여백을 예쁘게 메꿉니다 */}
                <div className="absolute inset-0 opacity-40">
                  <Image 
                    src={secureImageUrl} 
                    alt="blur background" 
                    fill 
                    className="object-cover blur-2xl scale-110" 
                    priority
                  />
              </div>
              
              {/* 2. 앞배경: 원본 비율을 그대로 유지(object-contain)하여 절대 잘리지 않게 합니다 */}
              <Image 
                src={secureImageUrl} 
                alt={article.title} 
                fill 
                className="object-contain drop-shadow-2xl z-10 p-2 sm:p-4" 
                priority
              />
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

                {/* 💰 수익화 제휴 버튼 & 공유/좋아요 컴포넌트 */}
                <ArticleInteractive article={article} />
              </div>
            </article>
          </div>

          {/* 📈 우측 (1칸 차지): Top 10 랭킹 사이드바 */}
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
