import { supabase } from '@/lib/supabase';
import { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Home, ArrowRight, Sparkles } from 'lucide-react';

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const resolvedParams = await params;
  const { data: article } = await supabase
    .from('live_news')
    .select('*')
    .eq('id', resolvedParams.id)
    .single();

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

  const { data: article, error } = await supabase
    .from('live_news')
    .select('*')
    .eq('id', articleId)
    .single();

  if (error || !article) {
    notFound(); // 데이터를 못 찾으면 깔끔하게 404 페이지로 보냅니다.
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      
      {/* 🧭 상단 네비게이션 바 (심플 로고) */}
      <header className="bg-white/80 backdrop-blur-md sticky top-0 z-50 border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="bg-slate-900 text-white font-black px-2 py-1 rounded-lg text-sm group-hover:bg-cyan-500 transition-colors">
              K-ENTER 24
            </div>
            <span className="font-bold text-slate-600 text-sm hidden sm:block">
              Live K-Culture Trends
            </span>
          </Link>
        </div>
      </header>

      {/* 📰 메인 기사 영역 */}
      <main className="flex-1 py-10 px-4">
        <article className="max-w-3xl mx-auto bg-white rounded-3xl shadow-xl overflow-hidden mb-12 border border-slate-100">
          {article.image_url && (
            <div className="relative w-full h-64 sm:h-96 bg-slate-900">
              <Image 
                src={article.image_url} 
                alt={article.title} 
                fill 
                className="object-cover opacity-90" 
                priority
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
            </div>
          )}
          <div className="p-8 sm:p-12">
            <div className="mb-6 flex items-center gap-3">
              <span className="px-3 py-1 bg-cyan-50 text-cyan-600 border border-cyan-100 text-xs font-black uppercase rounded-lg shadow-sm">
                {article.category}
              </span>
              <span className="text-slate-400 text-sm font-bold">
                {new Date(article.created_at).toLocaleDateString()}
              </span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black text-slate-900 mb-8 leading-tight">
              {article.title}
            </h1>
            <p className="text-lg sm:text-xl text-slate-700 leading-relaxed whitespace-pre-wrap">
              {article.summary}
            </p>
          </div>
        </article>

        {/* 🧲 [핵심] 메인 홈으로 유도하는 대형 배너 (Call To Action) */}
        <div className="max-w-3xl mx-auto px-4 sm:px-0">
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-[32px] p-8 sm:p-12 shadow-2xl relative overflow-hidden group">
            
            {/* 배경 장식 */}
            <div className="absolute -top-10 -right-10 opacity-10 group-hover:scale-110 group-hover:rotate-12 transition-transform duration-700">
              <Sparkles size={180} className="text-cyan-500" />
            </div>
            
            <div className="relative z-10 flex flex-col items-center text-center">
              <span className="text-cyan-400 font-bold tracking-widest text-sm uppercase mb-3">
                Explore More Trends
              </span>
              <h3 className="text-2xl sm:text-3xl font-black text-white mb-4 leading-tight">
                지금 가장 핫한 <span className="text-cyan-400">K-트렌드</span>가<br className="sm:hidden" /> 궁금하신가요?
              </h3>
              <p className="text-slate-300 mb-8 max-w-lg leading-relaxed text-sm sm:text-base">
                K-POP, 드라마, 뷰티, 패션까지! AI가 24시간 분석하는 
                실시간 한국 엔터테인먼트 랭킹을 메인 홈에서 확인하세요.
              </p>
              
              <Link
                href="/"
                className="flex items-center gap-3 px-8 py-4 bg-white hover:bg-cyan-50 text-slate-900 font-black text-lg sm:text-xl rounded-2xl shadow-xl hover:shadow-cyan-500/20 hover:-translate-y-1 transition-all duration-300"
              >
                <Home size={24} className="text-cyan-600" />
                실시간 트렌드 보러가기
                <ArrowRight size={20} className="ml-2 text-slate-400 group-hover:text-cyan-600 transition-colors" />
              </Link>
            </div>

          </div>
        </div>
      </main>
      
    </div>
  );
}
