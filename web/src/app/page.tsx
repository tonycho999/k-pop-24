// web/src/app/page.tsx
'use client';

import { useState, useEffect } from 'react';
import KeywordTicker from '@/components/KeywordTicker';

// 타입 정의
type Article = {
  id: number;
  title: string;
  summary: string;
  artist: string;
  date: string;
  image: string; // 이미지 URL (없으면 기본값)
};

// 더미 데이터 (서버 연동 전 UI 확인용)
const MOCK_NEWS: Article[] = [
  {
    id: 1,
    artist: "BTS",
    title: "BTS Jin Discharge: Global Fans Celebrate",
    summary: "Jin completed his military service today. Thousands of fans gathered...",
    date: "2024-06-12",
    image: "https://placehold.co/600x400/000000/FFF?text=BTS+News"
  },
  {
    id: 2,
    artist: "NewJeans",
    title: "NewJeans 'How Sweet' Breaks Records",
    summary: "NewJeans' latest single has topped the Billboard Global charts...",
    date: "2024-06-12",
    image: "https://placehold.co/600x400/000000/FFF?text=NewJeans"
  }
];

export default function Home() {
  const [articles, setArticles] = useState<Article[]>(MOCK_NEWS);
  const [clickedCount, setClickedCount] = useState(0);
  const [isSubscribed, setIsSubscribed] = useState(false); // 나중에 DB 연동

  // 로컬 스토리지에서 오늘 클릭 횟수 확인
  useEffect(() => {
    const today = new Date().toISOString().slice(0, 10);
    const storedDate = localStorage.getItem('lastClickDate');
    const storedCount = localStorage.getItem('clickCount');

    if (storedDate === today && storedCount) {
      setClickedCount(parseInt(storedCount));
    } else {
      // 날짜가 바뀌었으면 리셋
      localStorage.setItem('lastClickDate', today);
      localStorage.setItem('clickCount', '0');
      setClickedCount(0);
    }
  }, []);

  const handleCardClick = (id: number) => {
    if (!isSubscribed && clickedCount >= 1) {
      alert("🔒 Free limit reached! Subscribe to read more K-POP news.");
      return;
    }

    // 클릭 카운트 증가
    const newCount = clickedCount + 1;
    setClickedCount(newCount);
    localStorage.setItem('clickCount', newCount.toString());
    
    alert(`📢 Opening Article #${id} details...`);
    // 여기에 실제 상세 페이지 이동 로직 추가 예정
  };

  return (
    <main className="min-h-screen bg-black text-white p-4 font-sans selection:bg-pink-500 selection:text-white">
      {/* 헤더 영역 */}
      <header className="flex justify-between items-center py-6 mb-4">
        <h1 className="text-3xl font-extrabold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-pink-500 via-purple-500 to-cyan-500 animate-pulse">
          K-POP 24
        </h1>
        <button className="text-xs font-bold border border-pink-500 text-pink-500 px-3 py-1 rounded hover:bg-pink-500 hover:text-white transition-all">
          SUBSCRIBE ($15/yr)
        </button>
      </header>

      {/* 실시간 티커 컴포넌트 */}
      <KeywordTicker />

      {/* 뉴스 카드 그리드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
        {articles.map((news) => (
          <div 
            key={news.id}
            onClick={() => handleCardClick(news.id)}
            className="group relative bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden hover:border-cyan-400 transition-all duration-300 hover:shadow-[0_0_20px_#22d3ee40] cursor-pointer"
          >
            {/* 썸네일 */}
            <div className="h-48 bg-gray-800 relative overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={news.image} alt={news.artist} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                <div className="absolute top-2 left-2 bg-black/70 px-2 py-1 rounded text-xs text-cyan-400 font-bold backdrop-blur-sm border border-cyan-500/30">
                    {news.artist}
                </div>
            </div>

            {/* 내용 */}
            <div className="p-5">
              <h2 className="text-xl font-bold mb-2 leading-tight group-hover:text-cyan-300 transition-colors">
                {news.title}
              </h2>
              <p className="text-gray-400 text-sm line-clamp-2">
                {news.summary}
              </p>
              <div className="mt-4 flex justify-between items-center text-xs text-gray-500">
                <span>{news.date}</span>
                <span className="group-hover:translate-x-1 transition-transform">Read more →</span>
              </div>
            </div>

            {/* 잠금 오버레이 (무료 유저 클릭 소진 시 시각적 효과용) */}
            {!isSubscribed && clickedCount >= 1 && (
                <div className="absolute inset-0 bg-black/60 backdrop-blur-[1px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="text-center">
                        <div className="text-2xl mb-1">🔒</div>
                        <span className="text-xs font-bold text-pink-500">SUBSCRIBE TO UNLOCK</span>
                    </div>
                </div>
            )}
          </div>
        ))}
      </div>
    </main>
  );
}
