'use client';

interface NewsFeedProps {
  articles: any[];
  user: any;
  onLogin: () => void;
}

export default function NewsFeed({ articles, user, onLogin }: NewsFeedProps) {
  return (
    <section className="mb-8 max-w-7xl mx-auto">
      <h2 className="text-xl font-bold mb-4 text-gray-200">Live Briefing</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {articles.map((news) => (
          <div key={news.id} className="group relative h-80 rounded-xl overflow-hidden border border-gray-800 hover:border-cyan-500 transition-all bg-gray-900">
            {/* 배경 이미지 */}
            <div className="absolute inset-0">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img 
                src={news.image_url || "/logo.png"} 
                alt={news.title}
                className="w-full h-full object-cover opacity-50 group-hover:opacity-30 transition-opacity" 
              />
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-transparent" />

            {/* 콘텐츠 내용 */}
            <div className="absolute bottom-0 left-0 p-5 w-full">
               <div className="flex gap-2 mb-2">
                  <span className="text-xs text-cyan-300 font-bold bg-cyan-900/40 px-2 py-0.5 rounded border border-cyan-500/30">
                    {news.artist}
                  </span>
                  {/* 해시태그 1개만 노출 */}
                  {news.keywords?.slice(0, 1).map((tag: string, i: number) => (
                      <span key={i} className="text-[10px] text-pink-400 border border-pink-500/30 px-1.5 py-0.5 rounded">
                          {tag}
                      </span>
                  ))}
               </div>

               <h3 className="text-white font-bold text-lg leading-snug mb-2 line-clamp-2">
                  {news.title}
               </h3>
               
               {/* 로그인 여부에 따른 블러 처리 로직 */}
               <div className="relative">
                  <p className={`text-sm text-gray-300 line-clamp-3 ${!user ? 'blur-sm select-none opacity-50' : ''}`}>
                    {news.summary}
                  </p>
                  
                  {!user && (
                    <div className="absolute inset-0 flex items-center justify-center pt-2">
                      <button 
                        onClick={onLogin} 
                        className="text-xs font-bold text-cyan-400 border border-cyan-500 px-3 py-1 rounded-full bg-black/80 hover:bg-cyan-500 hover:text-black transition-all"
                      >
                        🔒 Login to Read
                      </button>
                    </div>
                  )}
               </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
