'use client';

import { useEffect, useRef } from 'react';
import { X, ExternalLink, ThumbsUp, ThumbsDown, Calendar, Clock, Share2 } from 'lucide-react';

interface ArticleModalProps {
  article: any;
  onClose: () => void;
  onVote: (id: string, type: 'likes' | 'dislikes') => void;
}

export default function ArticleModal({ article, onClose, onVote }: ArticleModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // 모달 외부 클릭 시 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  // ESC 키 누르면 닫기
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  if (!article) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
      {/* 배경 블러 처리 (Backdrop) */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity" />

      {/* 모달 컨텐츠 */}
      <div 
        ref={modalRef}
        className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-[32px] shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200"
      >
        
        {/* 1. 상단 이미지 영역 */}
        <div className="relative w-full h-56 sm:h-72 bg-slate-200 dark:bg-slate-800 shrink-0">
          {article.image_url ? (
            <img 
              src={article.image_url} 
              alt={article.title} 
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-slate-400">
              <span className="text-4xl font-black opacity-20">K-ENTER 24</span>
            </div>
          )}
          
          {/* 이미지 위 그라데이션 (텍스트 가독성용) */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-80" />

          {/* 닫기 버튼 (이미지 위에 둥둥 떠있음) */}
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 p-2 bg-black/30 hover:bg-black/50 backdrop-blur-md rounded-full text-white transition-all z-10"
          >
            <X size={20} />
          </button>

          {/* 카테고리 뱃지 */}
          <div className="absolute top-4 left-4 px-3 py-1 bg-cyan-500/90 backdrop-blur-md text-white text-[10px] font-black uppercase tracking-wider rounded-full shadow-lg">
            {article.category}
          </div>
        </div>

        {/* 2. 텍스트 컨텐츠 영역 (스크롤 가능) */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 custom-scrollbar">
          {/* 메타 정보 (날짜 등) */}
          <div className="flex items-center gap-4 text-xs font-bold text-slate-400 mb-4">
             <div className="flex items-center gap-1.5">
               <Calendar size={14} />
               {new Date(article.created_at).toLocaleDateString()}
             </div>
             <div className="flex items-center gap-1.5">
               <Clock size={14} />
               {new Date(article.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
             </div>
          </div>

          {/* 제목 */}
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white leading-tight mb-6">
            {article.title}
          </h2>

          {/* 본문 (요약) */}
          <div className="prose dark:prose-invert max-w-none">
            <p className="text-base sm:text-lg leading-relaxed text-slate-600 dark:text-slate-300">
              {article.summary}
            </p>
          </div>

          {/* 원문 보러가기 버튼 */}
          <div className="mt-8 pt-8 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
            <a 
              href={article.link} 
              target="_blank" 
              rel="noopener noreferrer"
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 bg-slate-900 dark:bg-cyan-600 text-white font-bold rounded-xl hover:scale-105 transition-transform shadow-lg"
            >
              Read Original Article <ExternalLink size={16} />
            </a>

            {/* 투표 및 공유 버튼 */}
            <div className="flex items-center gap-3 w-full sm:w-auto justify-center">
              <button 
                onClick={() => onVote(article.id, 'likes')}
                className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-900/30 text-slate-600 dark:text-slate-300 rounded-xl transition-colors group"
              >
                <ThumbsUp size={18} className="group-hover:text-blue-500 transition-colors" />
                <span className="text-sm font-bold">{article.likes || 0}</span>
              </button>

              <button 
                onClick={() => onVote(article.id, 'dislikes')}
                className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 dark:bg-slate-800 hover:bg-red-50 dark:hover:bg-red-900/30 text-slate-600 dark:text-slate-300 rounded-xl transition-colors group"
              >
                <ThumbsDown size={18} className="group-hover:text-red-500 transition-colors" />
                <span className="text-sm font-bold">{article.dislikes || 0}</span>
              </button>

              <button className="p-2.5 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400 rounded-xl transition-colors">
                 <Share2 size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
