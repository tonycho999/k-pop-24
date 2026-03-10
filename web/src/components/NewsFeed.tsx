'use client';

import { LiveNewsItem } from '@/types';
import { Clock, ThumbsUp, ArrowRight } from 'lucide-react';
import Image from 'next/image';
import AdsterraNative from '@/components/AdsterraNative'; // ✅ 추가됨: 네이티브 배너 임포트

interface NewsFeedProps {
  news: LiveNewsItem[];
  loading: boolean;
  onOpen: (item: LiveNewsItem) => void;
  category?: string; // ✅ K-Culture 레이아웃 분기를 위해 추가됨
}

export default function NewsFeed({ news, loading, onOpen, category }: NewsFeedProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6 animate-pulse">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-64 bg-slate-200 dark:bg-slate-800 rounded-[32px]" />
        ))}
      </div>
    );
  }

  if (news.length === 0) {
    return (
      <div className="text-center py-20 bg-white dark:bg-slate-900 rounded-[32px] border border-dashed border-slate-200 dark:border-slate-800">
        <p className="text-slate-400 font-medium">No news updates yet.</p>
      </div>
    );
  }

  // ✅ K-Culture 탭일 경우 전용 4단 매거진 레이아웃 렌더링
  if (category === 'K-Culture') {
    const cultureCategories = ['k-food', 'k-beauty', 'k-fashion', 'k-lifestyle'];

    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 w-full">
        {cultureCategories.map(cat => {
          // 각 서브 카테고리별로 필터링하여 상위 10개만 추출
          const catNews = news.filter(n => n.category === cat).slice(0, 10);
          if (catNews.length === 0) return null;

          return (
            <div key={cat} className="flex flex-col gap-5">
              {/* 기둥 헤더 타이틀 */}
              <div className="bg-slate-900 dark:bg-slate-800 text-white text-center py-2.5 rounded-2xl font-black uppercase tracking-widest shadow-md border border-slate-700">
                {cat.replace('-', ' ')}
              </div>

              {/* 기둥 내 기사 리스트 */}
              <div className="flex flex-col gap-4">
                {catNews.map((item, index) => {
                  const displayRank = index + 1;
                  const isHero = displayRank <= 2; // 1~2위는 큰 사각 박스

                  return (
                    <div
                      key={item.id}
                      onClick={() => onOpen(item)}
                      className={`
                        group relative overflow-hidden rounded-[24px] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer
                        ${isHero ? 'h-[280px] flex flex-col' : 'h-[100px] flex gap-4 items-center pr-3'}
                      `}
                    >
                      {/* 이미지 영역 */}
                      <div className={`
                        relative overflow-hidden bg-slate-100 dark:bg-slate-800
                        ${isHero ? 'h-[60%] w-full' : 'h-full w-[100px] shrink-0'}
                      `}>
                        {item.image_url ? (
                          <Image
                            src={item.image_url}
                            alt={item.title}
                            fill
                            className="object-cover object-top group-hover:scale-105 transition-transform duration-700"
                            sizes="(max-width: 768px) 100vw, 25vw"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-slate-300">
                            <span className="text-[10px] font-bold uppercase tracking-widest">No Image</span>
                          </div>
                        )}
                        <div className="absolute top-2 left-2 bg-white/90 dark:bg-black/80 backdrop-blur-md px-2 py-0.5 rounded-full text-[10px] font-black shadow-lg z-10">
                          <span className="text-cyan-600 dark:text-cyan-400">#{displayRank}</span>
                        </div>
                      </div>

                      {/* 텍스트 영역 */}
                      <div className={`
                        flex flex-col justify-center
                        ${isHero ? 'p-4 h-[40%]' : 'flex-1 py-2'}
                      `}>
                        <h3 className={`
                          font-bold text-slate-800 dark:text-slate-100 leading-tight group-hover:text-cyan-600 transition-colors
                          ${isHero ? 'text-sm line-clamp-2' : 'text-xs line-clamp-3'}
                        `}>
                          {item.title}
                        </h3>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // ✅ 그 외 일반 카테고리 (기존 로직 그대로 유지)
  return (
    <div className="grid grid-cols-1 md:grid-cols-6 gap-6">
      {news.map((item, index) => {
        const displayRank = index + 1;
        const isHero = displayRank <= 2;
        
        // 기존 <= 6 을 <= 8 로 변경! 
        const isMedium = displayRank > 2 && displayRank <= 5;

        // 💡 1. 기존에 바로 반환하던 기사 카드를 하나의 변수(articleCard)로 분리
        const articleCard = (
          <div 
            key={item.id}
            onClick={() => onOpen(item)}
            className={`
              group relative overflow-hidden rounded-[32px] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer
              ${isHero ? 'md:col-span-3 h-[420px]' : isMedium ? 'md:col-span-2 h-[340px]' : 'md:col-span-6 h-[140px] flex gap-6 items-center pr-6'}
            `}
          >
            {/* 이미지 영역 */}
            <div className={`
              relative overflow-hidden bg-slate-100 dark:bg-slate-800
              ${isHero ? 'h-3/5 w-full' : isMedium ? 'h-1/2 w-full' : 'h-full w-1/3 min-w-[140px]'}
            `}>
              {item.image_url ? (
                <Image
                  src={item.image_url}
                  alt={item.title}
                  fill
                  className="object-cover object-top group-hover:scale-105 transition-transform duration-700"
                  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                  priority={isHero}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-slate-300">
                  <span className="text-xs font-bold uppercase tracking-widest">No Image</span>
                </div>
              )}
              
              <div className="absolute top-4 left-4 bg-white/90 dark:bg-black/80 backdrop-blur-md px-3 py-1 rounded-full text-xs font-black shadow-lg z-10">
                <span className="text-cyan-600 dark:text-cyan-400">#{displayRank}</span>
              </div>
            </div>

            {/* 텍스트 영역 */}
            <div className={`
              flex flex-col justify-between
              ${isHero ? 'p-6 h-2/5' : isMedium ? 'p-5 h-1/2' : 'flex-1 py-4'}
            `}>
              <div>
                <div className="flex items-center gap-2 mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                   <span className="text-cyan-600 dark:text-cyan-500">{item.category}</span>
                   <span>•</span>
                   <span className="flex items-center gap-1">
                      <Clock size={10} />
                      NEW
                   </span>
                </div>
                
                <h3 className={`
                  font-bold text-slate-800 dark:text-slate-100 leading-tight group-hover:text-cyan-600 transition-colors
                  ${isHero ? 'text-2xl mb-3 line-clamp-2' : isMedium ? 'text-lg mb-2 line-clamp-2' : 'text-lg mb-1 line-clamp-1'}
                `}>
                  {item.title}
                </h3>

                {(isHero || !isMedium) && (
                   <p className="text-sm text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                     {item.summary}
                   </p>
                )}
              </div>

              <div className="flex items-center justify-between mt-auto pt-4">
                 <div className="flex items-center gap-4 text-xs font-bold text-slate-400">
                    <span className="flex items-center gap-1.5 group-hover:text-cyan-500 transition-colors">
                       <ThumbsUp size={14} />
                       {item.likes || 0}
                    </span>
                    {item.score && (
                        <span className="bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-[10px]">
                           Sc: {item.score.toFixed(0)}
                        </span>
                    )}
                 </div>
                 
                 <div className="w-8 h-8 rounded-full bg-slate-50 dark:bg-slate-800 flex items-center justify-center group-hover:bg-cyan-500 group-hover:text-white transition-colors">
                    <ArrowRight size={14} />
                 </div>
              </div>
            </div>
          </div>
        );

        // 💡 2. 5번째 기사 (큰 카드 2개 + 중간 카드 3개 조합이 끝난 시점) 직후에 광고 삽입
        if (index === 4) {
          return (
            <div key={`ad-wrapper-${item.id}`} className="contents">
              {articleCard}
              {/* 가로 전체 폭(col-span-6)을 차지하도록 광고 영역 할당 */}
              <div className="col-span-1 md:col-span-6 w-full">
                <AdsterraNative />
              </div>
            </div>
          );
        }

        // 광고가 들어가지 않는 나머지 기사들은 그대로 반환
        return articleCard;
      })}
    </div>
  );
}
