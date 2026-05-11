'use client';

import { useState, useEffect } from 'react';
import { ThumbsUp, Share2, ShoppingCart } from 'lucide-react';
import { supabase } from '@/lib/supabase';

export default function ArticleInteractive({ article }: { article: any }) {
  const [userRegion, setUserRegion] = useState<'global' | 'sea'>('global');
  const [votes, setVotes] = useState(article.likes || 0);

  useEffect(() => {
    fetch('https://ipapi.co/json/').then(res => res.json()).then(data => {
      const seaCountries = ['PH', 'SG', 'MY', 'TH', 'ID', 'VN', 'TW'];
      if (seaCountries.includes(data.country_code)) setUserRegion('sea');
    }).catch(() => setUserRegion('global'));
  }, []);

  const isKCulture = ['k-food', 'k-beauty', 'k-fashion', 'k-lifestyle'].includes(article.category);
  const rawKeyword = article.amazon_keyword || '';

  const renderAffiliateButton = () => {
    if (!isKCulture || !rawKeyword) return null;
    if (userRegion === 'sea') {
      const encodedUrl = encodeURIComponent(`https://shopee.ph/search?keyword=${rawKeyword}`);
      return (
        <a href={`https://invl.me/clng0bc?aff_sub=k-enter24&url=${encodedUrl}`} target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-3 w-full sm:w-auto px-8 py-4 bg-[#EE4D2D] text-white font-black text-lg rounded-2xl shadow-lg">
          <ShoppingCart size={24} /> Shop "{rawKeyword}" on Shopee
        </a>
      );
    }
    return (
      <a href={`https://www.amazon.com/s?k=${encodeURIComponent(rawKeyword)}&tag=kculturetrend-20`} target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-3 w-full sm:w-auto px-8 py-4 bg-[#FF9900] text-slate-900 font-black text-lg rounded-2xl shadow-lg">
        <ShoppingCart size={24} /> Shop on Amazon
      </a>
    );
  };

  return (
    <div className="border-t border-slate-100 dark:border-slate-800 pt-8">
      <div className="flex justify-center mb-10">{renderAffiliateButton()}</div>
      <div className="flex justify-center gap-10">
        <button onClick={async () => { setVotes(v => v + 1); await supabase.rpc('increment_vote', { row_id: article.id }); }} className="flex flex-col items-center gap-2 group">
          <div className="w-16 h-16 rounded-2xl bg-slate-50 dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-cyan-500 transition-all"><ThumbsUp size={28} /></div>
          <span className="text-sm font-bold text-slate-400">{votes}</span>
        </button>
        <button onClick={() => { window.navigator.share({ title: article.title, url: window.location.href }); }} className="flex flex-col items-center gap-2 group">
          <div className="w-16 h-16 rounded-2xl bg-slate-50 dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-purple-500 transition-all"><Share2 size={28} /></div>
          <span className="text-sm font-bold text-slate-400">Share</span>
        </button>
      </div>
    </div>
  );
}
