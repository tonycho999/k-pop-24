import { supabase } from '@/lib/supabase';

// 💡 GET 요청이 올 때마다 동적으로 RSS XML을 생성하여 반환합니다.
export async function GET() {
  const baseUrl = 'https://k-enter24.com';

  // 1. 최신 기사 50개만 가져옵니다 (RSS는 보통 최신 글 위주로 보여줍니다)
  const { data: news } = await supabase
    .from('search_archive')
    .select('id, title, summary, created_at')
    .order('created_at', { ascending: false })
    .limit(50);

  // 2. RSS 아이템 리스트로 변환 (XML 문법에 맞게 조립)
  const itemsXml = (news || []).map((item) => `
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
      <title>K-ENTER24 - Top K-Culture Trends</title>
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
      'Cache-Control': 's-maxage=3600, stale-while-revalidate', // 1시간 동안 캐시 유지
    },
  });
}
