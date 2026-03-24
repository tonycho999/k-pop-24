'use client';

import { useState } from 'react';
import { LiveNewsItem } from '@/types';
import { Clock, ThumbsUp, ArrowRight } from 'lucide-react';
import Image from 'next/image';

interface NewsFeedProps {
  news: LiveNewsItem[];
  loading: boolean;
  onOpen: (item: LiveNewsItem) => void;
  category?: string; 
}

export default function NewsFeed({ news, loading, onOpen, category }: NewsFeedProps) {
  // 모바일 뷰에서 사용할 서브 카테고리 탭 상태 (PC에서는 사용 안 함)
  const [activeTab, setActiveTab] = useState('k-food');

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

  // ✅ K-Culture 카테고리 처리 (모바일 탭 뷰 & PC 전체 펼침 뷰 분리)
  if (category === 'K-Culture') {
    const cultureCategories = ['k-food', 'k-beauty', 'k-fashion', 'k-lifestyle'];
    const activeNews = news.filter(n => n.category === activeTab).slice(0, 10);

    // 내부 카드 렌더링 컴포넌트 (중복 코드 방지)
    const renderCard = (item: LiveNewsItem, index: number, isHero: boolean) => (
      <div
        key={item.id}
        onClick={() => onOpen(item)}
        className={`
          group relative overflow-hidden rounded-[24px] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer
          ${isHero ? 'h-[280px] flex flex-col md:col-span-2' : 'h-[100px] flex gap-4 items-center pr-3 col-span-1'}
        `}
      >
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
              sizes="(max-width: 768px) 100vw, 50vw"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-slate-300">
              <span className="text-[10px] font-bold uppercase tracking-widest">No Image</span>
            </div>
          )}
          <div className="absolute top-2 left-2 bg-white/90 dark:bg-black/80 backdrop-blur-md px-2 py-0.5 rounded-full text-[10px] font-black shadow-lg z-10">
            <span className="text-cyan-600 dark:text-cyan-400">#{index + 1}</span>
          </div>
        </div>
        <div className={`
          flex flex-col justify-center
          ${isHero ? 'p-4 h-[40%]' : 'flex-1 py-2'}
        `}>
          <h3 className={`
            font-bold text-slate-800 dark:text-slate-100 leading-tight group-hover:text-cyan-600 transition-colors
            ${isHero ? 'text-lg line-clamp-2' : 'text-xs line-clamp-3'}
          `}>
            {item.title}
          </h3>
        </div>
      </div>
    );

    return (
      <div className="w-full">
        {/* 📱 1. 모바일 뷰 (md 사이즈 이상에서는 숨김) */}
        <div className="md:hidden flex flex-col gap-6">
          <div className="flex overflow-x-auto hide-scrollbar gap-2 pb-2">
            {cultureCategories.map(cat => (
              <button
                key={cat}
                onClick={() => setActiveTab(cat)}
                className={`
                  whitespace-nowrap px-6 py-2.5 rounded-full text-sm font-black uppercase tracking-wider transition-all
                  ${activeTab === cat 
                    ? 'bg-slate-900 dark:bg-cyan-500 text-white shadow-md' 
                    : 'bg-white dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700'}
                `}
              >
                {cat.replace('-', ' ')}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-1 gap-4">
            {activeNews.length === 0 ? (
              <div className="text-center py-10 text-slate-400">No news for {activeTab} yet.</div>
            ) : (
              activeNews.map((item, index) => renderCard(item, index, index < 2))
            )}
          </div>
        </div>

        {/* 💻 2. PC 뷰 (md 사이즈 미만에서는 숨김) - 4개 카테고리 동시 노출 */}
        <div className="hidden md:grid grid-cols-4 gap-6 w-full">
          {cultureCategories.map(cat => {
            // 카테고리별로 상위 5개 기사만 필터링해서 보여줍니다.
            const catNews = news.filter(n => n.category === cat).slice(0, 5);
            return (
              <div key={cat} className="flex flex-col gap-4">
                {/* 각 컬럼의 헤더 (K-FOOD, K-BEAUTY 등) */}
                <div className="border-b-2 border-slate-800 pb-2 mb-2">
                  <h2 className="text-lg font-black text-slate-900 dark:text-white uppercase tracking-wider">
                    {cat.replace('-', ' ')}
                  </h2>
                </div>
                {/* 해당 카테고리의 기사 리스트 (PC에서는 모두 작은 카드로 통일) */}
                {catNews.length === 0 ? (
                  <p className="text-sm text-slate-400">No news yet.</p>
                ) : (
                  catNews.map((item, index) => renderCard(item, index, false))
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // ✅ 그 외 일반 카테고리 (All, K-Pop, K-Drama 등) 기존 렌더링 로직 유지
  return (
    <div className="grid grid-cols-1 md:grid-cols-6 gap-6">
      {news.map((item, index) => {
        const displayRank = index + 1;
        const isHero = displayRank <= 2;
        const isMedium = displayRank > 2 && displayRank <= 5;

        return (
          <div 
            key={item.id}
            onClick={() => onOpen(item)}
            className={`
              group relative overflow-hidden rounded-[32px] bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 cursor-pointer
              ${isHero ? 'md:col-span-3 h-[420px]' : isMedium ? 'md:col-span-2 h-[340px]' : 'md:col-span-6 h-[140px] flex gap-6 items-center pr-6'}
            `}
          >
            {/* ... 기존 이미지 및 텍스트 렌더링 로직 동일 ... */}
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
      })}
    </div>
  );
}
