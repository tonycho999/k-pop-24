import { MetadataRoute } from 'next';
// import { supabase } from '@/lib/supabase'; // 나중에 개별 기사 페이지 생기면 사용

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://k-enter24.com';

  return [
    {
      url: `${baseUrl}`, // 메인 페이지
      lastModified: new Date(),
      changeFrequency: 'always', // 💡 핵심: 'daily' -> 'always'로 변경 (실시간 강조)
      priority: 1.0,             // 💡 구글에게 이 페이지가 1순위라고 알림
    },
    {
      url: `${baseUrl}/auth/login`, // 로그인 페이지
      lastModified: new Date(),
      changeFrequency: 'monthly',   // 로그인은 자주 변하지 않음
      priority: 0.5,                // 우선순위 낮춤
    }
  ];
}
