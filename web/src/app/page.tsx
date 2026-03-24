import { supabase } from '@/lib/supabase';
import HomeClient from '@/components/HomeClient';
import SEO from '@/components/SEO'; // ✅ 1. SEO 컴포넌트 임포트

export const revalidate = 60;

export default async function Page() {
  const { data: news, error } = await supabase
    .from('live_news')
    .select('*')
    .order('score', { ascending: false })
    .limit(30);

  if (error) {
    console.error('Failed to fetch news:', error);
  }

  return (
    <>
      {/* ✅ 2. 메인 페이지 전용 SEO 데이터 명시 (AI 엔진에게 이 페이지가 홈임을 알림) */}
      <SEO 
        title="K-ENTER 24 | Real-time K-News Radar"
        description="Stop waiting for translations. Get real-time AI-analyzed K-Pop & K-Drama news instantly."
      />
      <HomeClient initialNews={news || []} />
    </>
  );
}
