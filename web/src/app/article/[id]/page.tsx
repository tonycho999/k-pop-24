import { supabase } from '@/lib/supabase';
import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Image from 'next/image';

// ✅ 1. 구글 로봇에게 검색 결과에 띄울 제목과 썸네일을 알려줍니다.
export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const { data: article } = await supabase
    .from('live_news')
    .select('*')
    .eq('id', params.id)
    .single();

  if (!article) return { title: 'Article Not Found' };

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

// ✅ 2. 실제 누군가 링크를 직접 타고 들어왔을 때 보여줄 화면입니다.
export default async function ArticlePage({ params }: { params: { id: string } }) {
  const { data: article, error } = await supabase
    .from('live_news')
    .select('*')
    .eq('id', params.id)
    .single();

  if (error || !article) {
    notFound();
  }

  return (
    <main className="min-h-screen bg-slate-50 py-10 px-4">
      <article className="max-w-3xl mx-auto bg-white rounded-3xl shadow-xl overflow-hidden">
        {article.image_url && (
          <div className="relative w-full h-80 bg-slate-900">
            <Image src={article.image_url} alt={article.title} fill className="object-cover opacity-80" />
          </div>
        )}
        <div className="p-8 sm:p-12">
          <div className="mb-4">
            <span className="px-3 py-1 bg-cyan-500 text-white text-xs font-black uppercase rounded-lg">
              {article.category}
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black text-slate-900 mb-6 leading-tight">
            {article.title}
          </h1>
          <p className="text-lg text-slate-700 leading-relaxed whitespace-pre-wrap">
            {article.summary}
          </p>
        </div>
      </article>
    </main>
  );
}
