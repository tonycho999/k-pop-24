'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ThumbsUp, ThumbsDown, Share2, Calendar, ShoppingCart, MapPin } from 'lucide-react'; 
import Image from 'next/image';

interface ArticleModalProps {
  article: any;
  onClose: () => void;
  onVote: (id: string, type: 'likes' | 'dislikes') => void;
}

export default function ArticleModal({ article, onClose, onVote }: ArticleModalProps) {
  // 💡 [추가] 사용자의 지역 정보를 저장할 상태 변수
  const [userRegion, setUserRegion] = useState<'global' | 'sea'>('global'); // 기본값은 글로벌(아마존)
  const [isLoadingRegion, setIsLoadingRegion] = useState(true);

  // 💡 [추가] 컴포넌트가 마운트될 때 IP 기반으로 국가 확인
  useEffect(() => {
    const fetchUserRegion = async () => {
      try {
        // 무료 IP 기반 지역 확인 API 호출
        const response = await fetch('https://ipapi.co/json/');
        const data = await response.json();
        
        // 동남아시아 국가 코드 리스트 (Shopee 주요 국가)
        const seaCountries = ['PH', 'SG', 'MY', 'TH', 'ID', 'VN', 'TW'];
        
        if (seaCountries.includes(data.country_code)) {
          setUserRegion('sea'); // 동남아시아로 판별
        } else {
          setUserRegion('global'); // 그 외는 아마존으로 판별
        }
      } catch (error) {
        console.error('Failed to detect region, defaulting to global', error);
        setUserRegion('global');
      } finally {
        setIsLoadingRegion(false);
      }
    };

    fetchUserRegion();
  }, []);

  if (!article) return null;

  const handleShare = async () => {
    const title = article.title;
    
    // ✅ [수정] 메인 주소가 아닌, '이 기사의 전용 고유 주소'를 공유하도록 변경합니다.
    const baseUrl = typeof window !== 'undefined' ? window.location.origin : 'https://k-enter24.com';
    const articleUrl = `${baseUrl}/article/${article.id}`; 
    
    try {
      if (navigator.share) {
        await navigator.share({
          title: title,
          text: `Check out this K-Trend: ${title}`,
          url: articleUrl, // ✅ 개별 기사 주소가 카톡/인스타 등으로 넘어갑니다.
        });
      } else {
        await navigator.clipboard.writeText(articleUrl); // ✅ 클립보드에도 개별 주소가 복사됩니다.
        alert('Link copied to clipboard!');
      }
    } catch (err) {
      console.error('Error sharing:', err);
    }
  };

// K-Culture 카테고리인지 확인
  const isKCulture = ['k-food', 'k-beauty', 'k-fashion', 'k-lifestyle'].includes(article.category);
  
  // ✅ [버그 수정 1] 여기서 변환(encode)하지 않고 원본 글자 그대로 가져옵니다.
  const rawKeyword = article.amazon_keyword || '';

  // 💡 [추가] 지역별 버튼 컴포넌트 렌더링 함수
  const renderAffiliateButton = () => {
    if (!isKCulture || !rawKeyword || isLoadingRegion) return null;

    if (userRegion === 'sea') {
      // 1. AI가 만들어준 원본 키워드로 순수 쇼피 검색 URL을 만듭니다. (예: ...keyword=k-beauty facial device)
      const targetShopeeUrl = `https://shopee.ph/search?keyword=${rawKeyword}`;
      
      // 2. ✅ [버그 수정 2] 여기서 딱 한 번만! 전체 URL을 안전하게 변환합니다.
      const encodedUrl = encodeURIComponent(targetShopeeUrl);
      
      // 3. 인볼브아시아 링크와 결합
      const involveAsiaLink = `https://invl.me/clnfula?url=${encodedUrl}`;

      // 🧡 동남아시아 (Shopee) 버튼
      return (
        <a 
          href={involveAsiaLink}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-3 w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-[#EE4D2D] to-[#FF7337] hover:from-[#d73f21] hover:to-[#e6612b] text-white font-black text-lg rounded-2xl shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-200"
        >
          <ShoppingCart size={24} className="text-white" />
          Shop "{article.amazon_keyword}" on Shopee
        </a>
      );
    }

    // 💛 글로벌 (Amazon) 버튼
    return (
      <a 
        // ✅ [버그 수정 3] 아마존 링크에 들어갈 때만 띄어쓰기를 따로 변환해 줍니다.
        href={`https://www.amazon.com/s?k=${encodeURIComponent(rawKeyword)}&tag=kculturetrend-20`}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-3 w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-[#FF9900] to-[#FFB84D] hover:from-[#e68a00] hover:to-[#ffa31a] text-slate-900 font-black text-lg rounded-2xl shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-200"
      >
        <ShoppingCart size={24} className="text-slate-900" />
        Shop "{article.amazon_keyword}" on Amazon
      </a>
    );
  };

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          onClick={(e) => e.stopPropagation()} 
          className="bg-white dark:bg-slate-900 w-full max-w-2xl max-h-[90vh] rounded-[32px] overflow-hidden shadow-2xl flex flex-col"
        >
          {/* Header Image 영역 */}
          <div className="relative w-full h-64 sm:h-80 bg-slate-900 overflow-hidden">
            {article.image_url ? (
              <>
                <div className="absolute inset-0 opacity-40">
                  <Image 
                    src={article.image_url} 
                    alt="background blur" 
                    fill
                    className="object-cover blur-2xl scale-110" 
                    priority
                  />
                </div>
                <Image 
                  src={article.image_url} 
                  alt={article.title} 
                  fill
                  className="object-contain drop-shadow-2xl z-10 p-2"
                  priority
                />
              </>
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-slate-900 text-cyan-500 font-bold z-10 relative">
                {article.category}
              </div>
            )}
            
            <button 
              onClick={onClose}
              className="absolute top-4 right-4 p-2 bg-black/40 hover:bg-black/60 backdrop-blur-md rounded-full text-white transition-all z-20"
            >
              <X size={20} />
            </button>
          </div>

          {/* Body */}
          <div className="p-6 sm:p-8 overflow-y-auto flex-1 bg-white dark:bg-slate-900">
            
            <div className="mb-6 pb-6 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-3 mb-3">
                <span className="px-2.5 py-1 bg-cyan-500 text-white text-[10px] font-black uppercase rounded-lg shadow-sm">
                  {article.category}
                </span>
                <span className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 text-xs font-bold">
                  <Calendar size={12} />
                  {new Date(article.created_at).toLocaleDateString()}
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white leading-tight">
                {article.title}
              </h2>
            </div>

            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <span className="text-yellow-500 font-black text-lg">★ {article.score?.toFixed(1) || '0.0'}</span>
                <span className="text-slate-300 text-xs">AI Score</span>
              </div>
              
              <div className="flex gap-3">
                <button 
                  onClick={handleShare}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-800 rounded-xl font-bold text-sm text-slate-600 dark:text-slate-300 hover:bg-cyan-50 dark:hover:bg-cyan-900/30 hover:text-cyan-600 transition-colors"
                >
                  <Share2 size={16} /> Share
                </button>
              </div>
            </div>

            <p className="text-slate-600 dark:text-slate-300 text-lg leading-relaxed mb-8 whitespace-pre-wrap">
              {article.summary}
            </p>

            {/* 💰 [동적 제휴 마케팅 버튼] 지역에 따라 Shopee 또는 Amazon 렌더링 */}
            <div className="flex justify-center mb-10 mt-2">
              {renderAffiliateButton()}
            </div>

            {/* 좋아요/싫어요 버튼 */}
            <div className="flex justify-center gap-6 pb-4">
              <button 
                onClick={() => onVote(article.id, 'likes')}
                className="flex flex-col items-center gap-1 group"
              >
                <div className="w-14 h-14 rounded-2xl bg-slate-50 dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:bg-cyan-50 dark:group-hover:bg-cyan-900/20 group-hover:text-cyan-500 transition-all group-active:scale-95">
                  <ThumbsUp size={24} />
                </div>
                <span className="text-xs font-bold text-slate-400">{article.likes || 0}</span>
              </button>

              <button 
                onClick={() => onVote(article.id, 'dislikes')}
                className="flex flex-col items-center gap-1 group"
              >
                <div className="w-14 h-14 rounded-2xl bg-slate-50 dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:bg-pink-50 dark:group-hover:bg-pink-900/20 group-hover:text-pink-500 transition-all group-active:scale-95">
                  <ThumbsDown size={24} />
                </div>
                <span className="text-xs font-bold text-slate-400">{article.dislikes || 0}</span>
              </button>
            </div>
            
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
