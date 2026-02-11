import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import Groq from 'groq-sdk';
import { google } from 'googleapis';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);
const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
const customSearch = google.customsearch('v1');

const preciseDelay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export async function GET(request: Request) {
  const authHeader = request.headers.get('authorization');
  const now = new Date();
  const mins = now.getMinutes();

  // 보안 검증 (GitHub Actions에서 보낸 시크릿 확인)
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    // PHASE 1: 뉴스 스크랩 (01~10분)
    if (mins >= 1 && mins <= 10) {
      const msDelay = Math.random() * 240000; 
      await preciseDelay(msDelay);

      const query = "K-POP (idol OR group) comeback OR debut";

      // 1. Google
      const googleRes = await customSearch.cse.list({
        auth: process.env.GOOGLE_SEARCH_API_KEY,
        cx: process.env.GOOGLE_SEARCH_ENGINE_ID,
        q: query,
        dateRestrict: 'd1',
        num: 5
      });

      // 2. Naver
      const naverRes = await fetch(
        `https://openapi.naver.com/v1/search/news.json?query=${encodeURIComponent(query)}&display=5&sort=sim`,
        {
          headers: {
            'X-Naver-Client-Id': process.env.NAVER_CLIENT_ID!,
            'X-Naver-Client-Secret': process.env.NAVER_CLIENT_SECRET!,
          }
        }
      );
      const naverData = await naverRes.json();

      // DB 저장 (Google)
      const googleItems = googleRes.data.items || [];
      for (const item of googleItems) {
        await supabase.from('raw_news').upsert({
          link: item.link, title: item.title, snippet: item.snippet,
          source: item.displayLink, image_url: item.pagemap?.cse_image?.[0]?.src || null
        }, { onConflict: 'link' });
      }

      // DB 저장 (Naver)
      const naverItems = naverData.items || [];
      for (const item of naverItems) {
        await supabase.from('raw_news').upsert({
          link: item.link, 
          title: item.title.replace(/<[^>]*>?/gm, ''),
          snippet: item.description.replace(/<[^>]*>?/gm, ''),
          source: 'Naver News', image_url: null
        }, { onConflict: 'link' });
      }

      return NextResponse.json({ step: 'Scraping Completed' });
    }

    // PHASE 2: AI 분석 (20~25분)
    if (mins >= 20 && mins <= 25) {
      const { data: rawData } = await supabase.from('raw_news').select('*').limit(10).order('created_at', { ascending: false });
      if (!rawData) return NextResponse.json({ status: 'No data' });

      for (const article of rawData) {
        const prompt = `Analyze this K-POP news: "${article.title}". 
        Return JSON ONLY: { "artist": "string", "summary": "1 sentence cyberpunk vibe", "keywords": ["#tag1", "#tag2", "#tag3"], "vibe": { "excitement": 0, "shock": 0, "sadness": 0 } }`;

        const chat = await groq.chat.completions.create({
          messages: [{ role: "user", content: prompt }],
          model: "llama3-8b-8192",
          response_format: { type: "json_object" }
        });

        const result = JSON.parse(chat.choices[0]?.message?.content || "{}");
        
        await supabase.from('live_news').insert({
          artist: result.artist, title: article.title, summary: result.summary,
          keywords: result.keywords, reactions: result.vibe, 
          image_url: article.image_url, source: article.source, is_published: false
        });
      }
      return NextResponse.json({ step: 'AI Analysis Done' });
    }

    // PHASE 3: 배포 (정각)
    if (mins === 0) {
      await supabase.from('live_news').update({ is_published: true, published_at: new Date().toISOString() }).eq('is_published', false);
      return NextResponse.json({ step: 'Release Done' });
    }

    return NextResponse.json({ status: 'Standby' });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
