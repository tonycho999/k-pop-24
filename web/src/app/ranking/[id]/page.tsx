import { Metadata } from 'next';
import { supabase } from '@/lib/supabase';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, TrendingUp, Calendar, ChevronRight, Hash } from 'lucide-react';

// 💡 1. [SEO 핵심] 구글 봇을 위한 동적 메타데이터 생성
export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const { data } = await supabase
    .from('live_rankings') // 랭킹 테이블명 (실제 DB에 맞게 확인 필요)
    .select('title, category, meta_info')
    .eq('id', params.id)
    .single();

  if (!data) return { title: 'Trend Not Found' };

  return {
    title: `${data.title} - K-Trend Top Ranking`,
    description: `Discover why ${data.title} is currently trending in the ${data.category} chart. Get the latest insights, news, and updates.`,
    keywords: [data.title, data.category, 'K-Culture', 'Trend', 'Ranking'],
  };
}

// 💡 2. 서버 사이드 렌더링(SSR) 페이지 본문
export default async function RankingDetailPage({ params }: { params: { id: string } }) {
  // A. 랭킹 아이템 상세 정보 가져오기
  const { data: item } = await supabase
    .from('live_rankings')
    .select('*')
    .eq('id', params.id)
    .single();

  if (!item) {
    notFound(); // 데이터가 없으면 자동으로 404 페이지로 이동
  }

  // B. 해당 키워드와 관련된 뉴스 아카이브 가져오기 (페이지 정보량(Text)을 늘려 SEO 점수 극대화)
  // title이나 keyword 컬럼에 해당 랭킹 타이틀이 포함된 기사를 찾습니다.
  const { data: relatedNews } = await supabase
    .from('search_archive')
    .select('id, title, summary, created_at')
    .ilike('title', `%${item.title}%`)
    .order('created_at', { ascending: false })
    .limit(10);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 pb-20">
      {/* 상단 네비게이션 */}
      <div className="sticky top-0 z-10 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center">
          <Link href="/" className="p-2 -ml-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors">
            <ArrowLeft size={24} className="text-slate-700 dark:text-slate-300" />
          </Link>
          <span className="ml-2 font-black text-slate-900 dark:text-white uppercase tracking-wider text-sm">
            Trend Report
          </span>
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-4 pt-8">
        {/* 헤더 섹션 */}
        <div className="bg-white dark:bg-slate-900 rounded-3xl p-6 sm:p-10 shadow-lg border border-slate-100 dark:border-slate-800 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="px-3 py-1 bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400 text-xs font-black uppercase rounded-lg">
              {item.category || 'Trending'}
            </span>
            <span className="flex items-center gap-1 text-slate-400 text-xs font-bold">
              <TrendingUp size={14} />
              {item.score ? `${item.score.toFixed(0)} Points` : 'Hot'}
            </span>
          </div>
          
          <h1 className="text-3xl sm:text-5xl font-black text-slate-900 dark:text-white leading-tight mb-4 tracking-tight">
            {item.title}
          </h1>
          
          <p className="text-lg text-slate-500 dark:text-slate-400 font-medium">
            {item.meta_info || item.info || `Check out the latest updates and news regarding ${item.title}.`}
          </p>
        </div>

        {/* 관련 뉴스/아카이브 섹션 (SEO 핵심: 텍스트 덩어리) */}
        <div className="mb-6 flex items-center gap-2 px-2">
          <Hash size={20} className="text-cyan-500" />
          <h2 className="text-xl font-black text-slate-800 dark:text-slate-200">
            Related News & Updates
          </h2>
        </div>

        {relatedNews && relatedNews.length > 0 ? (
          <div className="flex flex-col gap-4">
            {relatedNews.map((news) => (
              <Link 
                href={`/article/${news.id}`} 
                key={news.id}
                className="block bg-white dark:bg-slate-900 p-5 rounded-2xl shadow-sm hover:shadow-md border border-slate-100 dark:border-slate-800 transition-all group"
              >
                <div className="flex justify-between items-start gap-4">
                  <div className="flex-1">
                    <h3 className="font-bold text-slate-800 dark:text-slate-200 text-lg mb-2 group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors line-clamp-2">
                      {news.title}
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 line-clamp-2 mb-3">
                      {news.summary}
                    </p>
                    <div className="flex items-center gap-1.5 text-xs text-slate-400 font-bold">
                      <Calendar size={12} />
                      {new Date(news.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                    <ChevronRight size={20} className="text-cyan-500" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="bg-slate-100 dark:bg-slate-800/50 rounded-2xl p-8 text-center border border-slate-200 dark:border-slate-700/50 border-dashed">
            <p className="text-slate-500 dark:text-slate-400 font-medium">
              We are currently gathering more deep insights about <strong className="text-slate-700 dark:text-slate-300">{item.title}</strong>. Check back soon!
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
