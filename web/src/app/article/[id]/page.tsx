import { supabase } from '@/lib/supabase'; // 🚨 이 경로가 대표님 프로젝트의 supabase 설정 파일 위치와 맞는지 확인해주세요!
import { Metadata } from 'next';
import Image from 'next/image';

// ✅ 최신 Next.js 문법 적용 (params를 비동기로 처리)
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
  // ✅ 최신 Next.js 문법 적용
  const resolvedParams = await params;
  const articleId = resolvedParams.id;

  const { data: article, error } = await supabase
    .from('live_news')
    .select('*')
    .eq('id', articleId)
    .single();

  // 💡 [디버깅 모드] 데이터를 못 찾았을 때 404로 넘기지 않고 화면에 에러를 강제로 출력합니다!
  if (error || !article) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-10 bg-slate-50 text-slate-800">
        <h1 className="text-3xl font-black mb-4">🚨 DB 조회 실패 (디버깅 화면)</h1>
        <p className="mb-2 text-lg">요청한 기사 번호 (ID): <span className="font-mono bg-cyan-100 text-cyan-800 px-3 py-1 rounded">{articleId}</span></p>
        
        <div className="w-full max-w-2xl bg-slate-900 rounded-xl p-6 mt-6 shadow-2xl">
          <p className="mb-4 text-red-400 font-bold">Supabase 응답 결과:</p>
          <pre className="text-green-400 overflow-auto whitespace-pre-wrap text-sm">
            {JSON.stringify(error, null, 2) || "Error 없음: 하지만 해당 ID의 데이터가 DB에 존재하지 않습니다. (파이썬에 의해 이미 삭제된 옛날 기사일 수 있습니다)"}
          </pre>
        </div>
        <p className="mt-8 text-slate-500 font-medium">✅ 이 화면이 뜬다는 것은 'app/article/[id]/page.tsx' 폴더 라우팅 자체는 완벽하게 작동하고 있다는 증거입니다!</p>
      </div>
    );
  }

  // 데이터가 있을 경우 정상 렌더링
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
