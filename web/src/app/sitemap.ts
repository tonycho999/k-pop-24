import { MetadataRoute } from 'next';
import { supabase } from '@/lib/supabase';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://k-enter24.com';

  // DB에서 모든 기사의 ID와 생성일을 가져옵니다.
  const { data: news } = await supabase
    .from('live_news')
    .select('id, created_at')
    .order('created_at', { ascending: false });

  const newsUrls = (news || []).map((item) => ({
    url: `${baseUrl}/article/${item.id}`,
    lastModified: new Date(item.created_at),
    changeFrequency: 'daily' as const,
    priority: 0.8,
  }));

  return [
    {
      url: baseUrl, // 메인 홈
      lastModified: new Date(),
      changeFrequency: 'hourly',
      priority: 1.0,
    },
    ...newsUrls, // DB에 있는 수백 개의 기사 주소가 여기에 쫙 펼쳐집니다!
  ];
}
