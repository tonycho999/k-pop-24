import { MetadataRoute } from 'next';
import { supabase } from '@/lib/supabase';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://k-enter24.com';

  // 1. 아카이브 뉴스 주소 가져오기
  const { data: archiveNews } = await supabase
    .from('search_archive')
    .select('id, created_at, score')
    .order('created_at', { ascending: false });

  // 2. ✅ 실시간 랭킹 주소 가져오기
  const { data: rankings } = await supabase
    .from('live_rankings') // 랭킹이 저장된 테이블명
    .select('id, updated_at');

  const newsUrls = (archiveNews || []).map((item) => ({
    url: `${baseUrl}/article/${item.id}`,
    lastModified: new Date(item.created_at),
    priority: 0.8,
  }));

  // ✅ 랭킹 전용 URL 리스트 생성
  const rankingUrls = (rankings || []).map((item) => ({
    url: `${baseUrl}/ranking/${item.id}`,
    lastModified: new Date(item.updated_at || new Date()),
    priority: 0.9, // 랭킹 페이지는 중요도가 높으므로 0.9 부여
  }));

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'hourly',
      priority: 1.0,
    },
    ...newsUrls,
    ...rankingUrls, // ✅ 사이트맵에 랭킹 주소들 포함!
  ];
}
