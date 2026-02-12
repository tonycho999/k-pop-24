import { NextResponse } from 'next/server';
import Groq from 'groq-sdk';

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

export async function POST(request: Request) {
  const { text, targetLang } = await request.json();

  try {
    const response = await groq.chat.completions.create({
      messages: [
        { 
          role: "system", 
          content: `You are a professional news translator. Translate the text into [${targetLang}]. Maintain a professional, journalistic tone. Return ONLY the translated text.` 
        },
        { role: "user", content: text }
      ],
      model: "llama-3.3-70b-versatile", // 고성능 모델 사용
    });

    return NextResponse.json({ translatedText: response.choices[0]?.message?.content });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
