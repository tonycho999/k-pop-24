'use client';
import { createClient } from '@supabase/supabase-js';
import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import KeywordTicker from '@/components/KeywordTicker';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default function Home() {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [viewCount, setViewCount] = useState(0);

  // 무료 기사 카운트 (하루 1개)
  useEffect(() => {
    const today = new Date().toDateString();
    const savedDate = localStorage.getItem('viewDate');
    const savedCount = parseInt(localStorage.getItem('viewCount') || '0');

    if (savedDate !== today) {
      localStorage.setItem('viewDate', today);
      localStorage.setItem('viewCount', '0');
      setViewCount(0);
    } else {
      setViewCount(savedCount);
    }
    
    fetchReports();
  }, []);

  const fetchReports = async () => {
    const { data } = await supabase
      .from('hourly_reports')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(20);
    if (data) setReports(data);
    setLoading(false);
  };

  const handleSearch = async () => {
    if (!searchQuery) return;
    setIsSearching(true);
    
    // 5분 안내 메시지
    alert("🚀 AI가 과거 데이터를 분석 중입니다.\n데이터가 없으면 생성까지 최대 1~5분이 소요될 수 있습니다.");

    const res = await fetch('/api/search', {
      method: 'POST',
      body: JSON.stringify({ keyword: searchQuery }),
    });
    const result = await res.json();
    
    if (result.found) {
      setReports([result.data, ...reports]); // 찾은거 맨 위에 추가
    } else {
      alert("검색 결과를 찾을 수 없습니다.");
    }
    setIsSearching(false);
  };

  const handleReadArticle = (id: number) => {
    if (viewCount >= 1) {
      alert("🔒 무료 1일 1회 읽기가 끝났습니다.\n구독(Subscribe)하고 무제한으로 즐기세요!");
      return;
    }
    localStorage.setItem('viewCount', (viewCount + 1).toString());
    setViewCount(viewCount + 1);
    alert("🔓 기사 잠금 해제! (오늘 남은 횟수: 0회)");
    // 실제로는 여기서 모달을 띄우거나 페이지 이동
  };

  return (
    <main className="min-h-screen bg-[#050505] text-white selection:bg-pink-500 selection:text-white">
      {/* 배경 은은한 빛 효과 */}
      <div className="fixed top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-900/20 rounded-full blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-900/20 rounded-full blur-[120px]"></div>
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6">
        <Header />

        {/* 검색 박스 */}
        <div className="relative max-w-3xl mx-auto mt-10 mb-2">
          <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search Artists (ex: BTS 2024)" 
            className="w-full bg-gray-900/80 border border-gray-700 text-white px-8 py-5 rounded-2xl focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all shadow-xl text-lg backdrop-blur-sm"
          />
          <button 
            onClick={handleSearch}
            disabled={isSearching}
            className="absolute right-3 top-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white px-8 py-2.5 rounded-xl font-bold transition-all shadow-lg disabled:opacity-50"
          >
            {isSearching ? 'Scanning...' : 'Search'}
          </button>
        </div>

        {/* 실시간 티커 */}
        <KeywordTicker keywords={['BTS', 'NewJeans', 'Seventeen', 'Blackpink', 'Stray Kids', 'IU', 'Aespa', 'IVE', 'Le Sserafim', 'Twice']} />

        {/* 메인 뉴스 그리드 */}
        <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
          <span className="w-2 h-8 bg-pink-500 rounded-full block"></span>
          Today's Top Headlines
        </h2>

        {loading ? (
          <div className="text-center py-20 text-gray-600 animate-pulse">Loading K-Pop Matrix...</div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {reports.map((item: any, idx: number) => (
              <div key={idx} className="group relative bg-[#111] rounded-2xl overflow-hidden border border-gray-800 hover:border-pink-500/50 transition-all duration-300 hover:shadow-[0_0_30px_rgba(236,72,153,0.15)] hover:-translate-y-1">
                {/* 썸네일 대신 그라데이션 박스 (이미지가 없어서) */}
                <div className="h-40 bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center relative overflow-hidden">
                  <div className="absolute inset-0 bg-black/40 group-hover:bg-transparent transition-all"></div>
                  <h3 className="text-3xl font-black text-white/20 group-hover:text-white/40 transition-all z-10 uppercase">{item.artist_name}</h3>
                </div>

                <div className="p-6">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-cyan-400 text-xs font-bold tracking-wider uppercase border border-cyan-900 bg-cyan-900/20 px-2 py-1 rounded">
                      NEWS
                    </span>
                    <span className="text-gray-500 text-xs">
                      {new Date(item.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </span>
                  </div>
                  
                  <h3 className="text-xl font-bold text-white mb-2 line-clamp-1">{item.artist_name} Issue</h3>
                  <div className="text-gray-400 text-sm line-clamp-3 mb-6 leading-relaxed">
                    {item.summary_text.replace(/<[^>]*>?/gm, '')}
                  </div>

                  <button 
                    onClick={() => handleReadArticle(item.id)}
                    className="w-full py-3 rounded-lg bg-gray-800 hover:bg-pink-600 text-gray-300 hover:text-white font-bold text-sm transition-all flex items-center justify-center gap-2"
                  >
                    {viewCount >= 1 ? '🔒 Locked (Subscribe)' : '🔓 Read Full Story'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
