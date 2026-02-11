import { google } from 'googleapis';
import Groq from 'groq-sdk';
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

// 1. Supabase 연결
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

// 2. Groq 연결 (AI)
const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY
});

// 3. Google 검색 연결
const customSearch = google.customsearch('v1');

// [1단계] 오늘 핫한 가수 찾기
async function findTrendingArtists() {
  console.log("📡 오늘의 K-POP 이슈 스캔 중... (via Groq)");
  
  try {
    const res = await customSearch.cse.list({
      cx: process.env.GOOGLE_SEARCH_ENGINE_ID,
      q: "K-pop idol breaking news today",
      auth: process.env.GOOGLE_SEARCH_API_KEY,
      dateRestrict: 'd1',
      num: 10,
    });

    if (!res.data.items) return [];

    const headlines = res.data.items.map(item => item.title).join('\n');
    
    // Groq에게 가수 이름 추출 요청
    const chatCompletion = await groq.chat.completions.create({
      messages: [
        {
          role: "system",
          content: "You are a K-Pop expert. Extract popular K-Pop artist names from the text. Return ONLY a comma-separated list. No other text."
        },
        {
          role: "user",
          content: `다음 뉴스 제목에서 언급된 K-Pop 가수 이름만 영어로 추출해줘:\n${headlines}`
        }
      ],
      model: "llama3-70b-8192",
      temperature: 0,
    });

    const text = chatCompletion.choices[0]?.message?.content || "";
    const artists = text.split(',').map(s => s.trim()).filter(s => s.length > 0 && !s.includes("news"));
    const topArtists = [...new Set(artists)].slice(0, 5); 
    
    console.log(`🎯 AI 포착 타겟: ${topArtists.join(', ')}`);
    return topArtists;

  } catch (e) {
    console.error("탐색 실패:", e);
    return ['NewJeans', 'BTS']; // 실패 시 기본값
  }
}

// [2단계] 심층 보도 작성
async function reportArtist(name: string) {
  console.log(`\n🔍 '${name}' 심층 취재 중...`);
  
  const res = await customSearch.cse.list({
    cx: process.env.GOOGLE_SEARCH_ENGINE_ID,
    q: `${name} K-pop news`,
    auth: process.env.GOOGLE_SEARCH_API_KEY,
    dateRestrict: 'd1',
    num: 5, 
  });

  if (!res.data.items || res.data.items.length === 0) return;

  const combinedNews = res.data.items
    .map((item, index) => `기사${index+1}: ${item.title} - ${item.snippet}`)
    .join('\n');

  // Groq에게 요약 요청
  const chatCompletion = await groq.chat.completions.create({
    messages: [
      {
        role: "system",
        content: "You are a witty K-Pop news editor for global fans. Write in Korean."
      },
      {
        role: "user",
        content: `
          아래는 '${name}'의 오늘자 뉴스들이야.
          이걸 바탕으로 팬들이 좋아할 만한 **3줄 요약 리포트**를 작성해줘.

          [필수 조건]
          1. 제목 없이 본문만 작성할 것.
          2. 말투: 친근한 해요체 (예: "오늘 BTS가 ~했대요!").
          3. 핵심 키워드는 HTML 태그로 강조: <span class="text-pink-400 font-bold">강조할단어</span>
          4. 이모지(✨, 🔥)를 적절히 섞어서 생동감 있게.
          5. 마지막엔 <br> 한 줄 띄우고 응원 멘트 추가.

          [뉴스 내용]
          ${combinedNews}
        `
      }
    ],
    model: "llama3-70b-8192",
    temperature: 0.7,
  });

  const summary = chatCompletion.choices[0]?.message?.content || "";

  // DB 저장
  const { error } = await supabase
    .from('hourly_reports')
    .insert({
      artist_name: name,
      summary_text: summary,
      keywords: [name, 'K-Pop', 'Trending']
    });

  if (error) console.error("저장 에러:", error);
  else console.log(`✅ '${name}' 발행 완료!`);
}

async function main() {
  console.log("🚀 K-Pulse 24 뉴스룸 가동 (Engine: Groq Llama3)");
  const trendingArtists = await findTrendingArtists();

  if (trendingArtists.length === 0) {
    console.log("이슈 없음.");
    return;
  }

  for (const artist of trendingArtists) {
    await reportArtist(artist);
    await new Promise(r => setTimeout(r, 1000));
  }
  
  console.log("🏁 발행 끝!");
}

main();
