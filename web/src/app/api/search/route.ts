import { NextResponse } from 'next/server';
import { google } from 'googleapis';
import Groq from 'groq-sdk';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  try {
    const { keyword } = await req.json();
    console.log(`🔍 User Searching: ${keyword}`);

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );

    // 1. DB에 있는지 먼저 확인
    const { data: existing } = await supabase
      .from('hourly_reports')
      .select('*')
      .ilike('artist_name', `%${keyword}%`)
      .limit(1);

    if (existing && existing.length > 0) {
      return NextResponse.json({ found: true, data: existing[0] });
    }

    // 2. 없으면 AI 즉시 투입 (Scraping)
    console.log("⚡ DB에 없음. AI 즉시 생성 시작...");
    
    const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
    const customSearch = google.customsearch('v1');

    const newsRes = await customSearch.cse.list({
      cx: process.env.GOOGLE_SEARCH_ENGINE_ID,
      q: `${keyword} K-pop news`,
      auth: process.env.GOOGLE_SEARCH_API_KEY,
      dateRestrict: 'y1', // 1년치 검색
      num: 5,
    });

    if (!newsRes.data.items || newsRes.data.items.length === 0) {
      return NextResponse.json({ found: false, message: "관련 기사를 찾을 수 없습니다." });
    }

    // 3. 요약 생성
    const combined = newsRes.data.items.map(i => `${i.title}: ${i.snippet}`).join('\n');
    const summaryChat = await groq.chat.completions.create({
      messages: [
        { role: "system", content: "Summarize K-Pop news in Korean. Be witty and concise." },
        { role: "user", content: `Summarize news about ${keyword}:\n${combined}` }
      ],
      model: "llama3-70b-8192",
    });

    const summary = summaryChat.choices[0]?.message?.content || "요약 실패";

    // 4. DB 저장 및 반환
    const newItem = {
      artist_name: keyword,
      summary_text: summary,
      keywords: [keyword, 'AI-Generated'],
      created_at: new Date().toISOString()
    };

    await supabase.from('hourly_reports').insert(newItem);

    return NextResponse.json({ found: true, data: newItem, created_now: true });

  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
