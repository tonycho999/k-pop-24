import { supabase } from '@/lib/supabase';

export async function GET() {
  const baseUrl = 'https://k-enter24.com';

  // 1. 가장 따끈따끈한 최신 기사(live_news)에서 먼저 50개를 가져옵니다.
  const { data: liveNews } = await supabase
    .from('live_news')
    .select('id, title, summary, created_at')
    .order('created_at', { ascending: false })
    .limit(50);

  let newsItems = liveNews || [];

  // 만약 최신 기사가 50개가 안 된다면, archive에서 모자란 개수만큼 채워옵니다.
  if (newsItems.length < 50) {
    const { data: archiveNews } = await supabase
      .from('search_archive')
      .select('id, title, summary, created_at')
      .order('created_at', { ascending: false })
      .limit(50 - newsItems.length);
      
    if (archiveNews) {
      newsItems = [...newsItems, ...archiveNews];
    }
  }

  // 2. RSS 아이템 리스트로 변환
  const itemsXml = newsItems.map((item) => `
    <item>
      <title><![CDATA[${item.title}]]></title>
      <link>${baseUrl}/article/${item.id}</link>
      <guid isPermaLink="true">${baseUrl}/article/${item.id}</guid>
      <pubDate>${new Date(item.created_at).toUTCString()}</pubDate>
      <description><![CDATA[${item.summary}]]></description>
    </item>
  `).join('');

  // 3. 전체 RSS 껍데기 조립
  const rss = `<?xml version="1.0" encoding="UTF-8"?>
  <rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
      <title>K-ENTER 24 - Top K-Culture Trends</title>
      <link>${baseUrl}</link>
      <description>Get the latest breaking news and trends in K-Pop, K-Drama, K-Movie, and K-Culture.</description>
      <language>en-us</language>
      <atom:link href="${baseUrl}/rss.xml" rel="self" type="application/rss+xml" />
      <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
      ${itemsXml}
    </channel>
  </rss>`;

  // 4. 브라우저/봇이 이 문서를 텍스트가 아닌 'XML'로 인식하도록 헤더 설정
  return new Response(rss, {
    headers: {
      'Content-Type': 'text/xml; charset=utf-8',
      'Cache-Control': 's-maxage=3600, stale-while-revalidate', 
    },
  });
}
