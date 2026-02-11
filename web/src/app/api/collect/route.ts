import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import Groq from 'groq-sdk';
import { google } from 'googleapis';

// --- 환경 변수 설정 ---
const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!);
const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
const customSearch = google.customsearch('v1');

// Vercel 함수 타임아웃 방지를 위한 유틸
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export async function GET(request: Request) {
  // 보안: Vercel Cron만 호출 가능 (헤더 체크)
  // 로컬 테스트 시엔 주석 처리 하세요
  if (request.headers.get('Authorization') !== `Bearer ${process.env.CRON_SECRET}`) {
     return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const now = new Date();
  const minutes = now.getMinutes();
  const hour = now.getHours();

  try {
    // ============================================================
    // PHASE 1: 뉴스 스크랩 (00분 ~ 10분 사이 실행)
    // 목표: 00:01 ~ 00:05 사이 랜덤 시작
    // ============================================================
    if (minutes < 15) {
      // 1. 랜덤 딜레이 (1ms ~ 5분(300,000ms) 사이)
      const randomStart = Math.floor(Math.random() * 300000); 
      console.log(`🕒 [Phase 1] Waiting ${randomStart}ms to start scraping...`);
      await delay(randomStart);

      console.log("🚀 [Phase 1] Scraping Started for ALL K-POP Artists");
      
      // 2. 검색 설정 (특정 가수 리스트 없이 광범위 검색)
      // dateRestrict: 'd1' (지난 24시간)
      const query = "K-POP idol news"; 
      const res = await customSearch.cse.list({
        auth: process.env.GOOGLE_SEARCH_API_KEY,
        cx: process.env.GOOGLE_SEARCH_ENGINE_ID,
        q: query,
        dateRestrict: 'd1', 
        num: 10, // 상위 10개 (API 할당량 고려 조절)
      });

      const items = res.data.items || [];
      
      // 3. Raw Data 저장 (이미지 포함)
      let count = 0;
      for (const item of items) {
        // 이미지 추출 (pagemap 활용)
        const imgUrl = item.pagemap?.cse_image?.[0]?.src 
                    || item.pagemap?.cse_thumbnail?.[0]?.src 
                    || null;

        const { error } = await supabase.from('raw_news').upsert({
          link: item.link,
          title: item.title,
          snippet: item.snippet,
          source: item.displayLink,
          image_url: imgUrl,
          created_at: new Date().toISOString()
        }, { onConflict: 'link' });

        if (!error) count++;
      }
      
      return NextResponse.json({ step: 'Scraping', saved: count });
    }

    // ============================================================
    // PHASE 2: AI 요약 & 분석 (20분 ~ 45분 사이 실행)
    // 목표: 00:20 ~ 00:22 사이 랜덤 시작, 00:50 전 완료
    // ============================================================
    if (minutes >= 20 && minutes < 45) {
      const randomStart = Math.floor(Math.random() * 120000); // 0~2분 대기
      console.log(`🕒 [Phase 2] Waiting ${randomStart}ms to start AI...`);
      await delay(randomStart);

      console.log("🤖 [Phase 2] AI Summarizing & Analyzing...");

      // 1. 아직 처리 안 된 Raw News 가져오기 (랜덤으로 5개씩 처리)
      const { data: rawData } = await supabase.from('raw_news').select('*').limit(5);

      if (!rawData || rawData.length === 0) {
          return NextResponse.json({ step: 'AI', message: 'No raw news to process.' });
      }

      // 2. AI 루프 (가수별 요약 + 태그 + 반응 추론)
      for (const article of rawData) {
        // 나라별 반응 제안: 별도 검색 비용 없이, AI에게 '문맥상 추론'을 맡기는 프롬프트 전략 사용
        const prompt = `
          Analyze this K-POP news snippet:
          Title: "${article.title}"
          Snippet: "${article.snippet}"

          Tasks:
          1. Extract the main Artist Name.
          2. Summarize the event in Cyberpunk style (English, exciting tone).
          3. Extract 3 trend hashtags (e.g., #Comeback).
          4. Infer probable global reactions (USA & Korea) based on the news context.

          Output JSON only:
          {
            "artist": "string",
            "title": "string",
            "summary": "string",
            "keywords": ["#tag1", "#tag2", "#tag3"],
            "reactions": {"US": "reaction string...", "KR": "reaction string..."}
          }
        `;

        const chat = await groq.chat.completions.create({
          messages: [{ role: "user", content: prompt }],
          model: "llama3-8b-8192",
          response_format: { type: "json_object" }
        });

        const content = chat.choices[0]?.message?.content || "{}";
        const result = JSON.parse(content);

        // 3. Live 테이블에 저장 (아직 is_published = false)
        await supabase.from('live_news').insert({
          artist: result.artist || "K-POP Issue",
          title: result.title || article.title,
          summary: result.summary,
          keywords: result.keywords || [],
          reactions: result.reactions || {},
          image_url: article.image_url,
          source: article.source,
          is_published: false // 01:00에 공개됨
        });
      }

      return NextResponse.json({ step: 'AI', processed: rawData.length });
    }

    // ============================================================
    // PHASE 3: 배포, 정리, 아카이빙 (55분 ~ 05분 사이 실행)
    // 목표: 01:00 정각 웹 노출, 24시간 지난 데이터 삭제
    // ============================================================
    if (minutes >= 55 || minutes < 5) {
      console.log("🏁 [Phase 3] Publishing & Cleanup...");

      // 1. 배포: 숨겨진 기사 공개 (is_published -> true)
      await supabase.from('live_news')
        .update({ is_published: true, published_at: new Date().toISOString() })
        .eq('is_published', false);

      // 2. 청소: 24시간 지난 원본 삭제
      const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
      await supabase.from('raw_news').delete().lt('created_at', yesterday);
      // (선택) live_news도 너무 오래된 건 정리 가능

      // 3. [중요] 23:00 영구 보존 로직
      // 서버 시간 기준 23시라면, 현재 떠있는 모든 기사를 아카이브로 복사
      if (hour === 23) {
         console.log("💾 Archiving Today's News...");
         
         // 현재 게시된 뉴스 조회
         const { data: todaysNews } = await supabase
            .from('live_news')
            .select('*')
            .eq('is_published', true);

         if (todaysNews && todaysNews.length > 0) {
            // 아카이브 테이블로 복사
            const archiveData = todaysNews.map(news => ({
                artist: news.artist,
                title: news.title,
                summary: news.summary,
                image_url: news.image_url,
                keywords: news.keywords,
                reactions: news.reactions,
                archived_date: new Date() // 오늘 날짜
            }));
            
            await supabase.from('archive_news').insert(archiveData);
         }
      }

      return NextResponse.json({ step: 'Publish & Archive' });
    }

    return NextResponse.json({ message: 'Standby...' });

  } catch (error: any) {
    console.error("❌ Cron Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
