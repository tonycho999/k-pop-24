import { MetadataRoute } from 'next';
import { supabase } from '@/lib/supabase';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://k-enter24.com';

  // 1. 최신 라이브 뉴스 가져오기 (가장 높은 우선순위)
  const { data: liveNews } = await supabase
    .from('live_news')
    .select('id, created_at')
    .order('created_at', { ascending: false });

  // 2. 과거 아카이브 뉴스 가져오기
  const { data: archiveNews } = await supabase
    .from('search_archive')
    .select('id, created_at')
    .order('created_at', { ascending: false });

  // ❌ [삭제 완료] 클릭 없는 랭킹(live_rankings) 주소는 404 에러를 유발하므로 사이트맵에서 제거했습니다.

  // 3. 라이브 뉴스 URL 생성 (중요도 0.9)
  const liveUrls = (liveNews || []).map((item) => ({
    url: `${baseUrl}/article/${item.id}`,
    lastModified: new Date(item.created_at),
    priority: 0.9,
  }));

  // 4. 아카이브 뉴스 URL 생성 (중요도 0.7)
  const archiveUrls = (archiveNews || []).map((item) => ({
    url: `${baseUrl}/article/${item.id}`,
    lastModified: new Date(item.created_at),
    priority: 0.7,
  }));

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'always',
      priority: 1.0,
    },
    ...liveUrls,
    ...archiveUrls,
  ];
}
