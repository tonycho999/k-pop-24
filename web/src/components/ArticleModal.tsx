'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, ThumbsUp, ThumbsDown, Share2, Calendar } from 'lucide-react';

interface ArticleModalProps {
  article: any;
  onClose: () => void;
  onVote: (id: string, type: 'likes' | 'dislikes') => void;
}

export default function ArticleModal({ article, onClose, onVote }: ArticleModalProps) {
  if (!article) return null;

  // [추가] 모달 내부 공유 버튼 로직
  const handleShare = async () => {
    const title = article.title;
    const url = article.link; // 또는 article.original_link
    
    try {
      if (navigator.share) {
        await navigator.share({
          title: title,
          text: `Check out this news: ${title}`,
          url: url,
        });
      } else {
        await navigator.clipboard.writeText(url);
        alert('Link copied to clipboard!');
      }
    } catch (err) {
      console.error('Error sharing:', err);
    }
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
          onClick={(e) => e.stopPropagation()} // 모달 내부 클릭 시 닫힘 방지
          className="bg-white dark:bg-slate-900 w-full max-w-2xl max-h-[90vh] rounded-[32px] overflow-hidden shadow-2xl flex flex-col"
        >
          {/* Header Image */}
          <div className="relative h-64 sm:h-80 bg-slate-200">
            <img 
              src={article.image_url || `https://placehold.co/800x600/111/cyan?text=${article.category}`} 
              alt={article.title} 
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent" />
            
            <button 
              onClick={onClose}
              className="absolute top-4 right-4 p-2 bg-black/30 hover:bg-black/50 backdrop-blur-md rounded-full text-white transition-all"
            >
              <X size={20} />
            </button>

            <div className="absolute bottom-0 left-0 p-6 sm:p-8 w-full">
              <div className="flex items-center gap-3 mb-3">
                <span className="px-2.5 py-1 bg-cyan-500 text-white text-[10px] font-black uppercase rounded-lg shadow-lg">
                  {article.category}
                </span>
                <span className="flex items-center gap-1.5 text-slate-300 text-xs font-bold">
                  <Calendar size={12} />
                  {new Date(article.created_at).toLocaleDateString()}
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-white leading-tight line-clamp-3">
                {article.title}
              </h2>
            </div>
          </div>

          {/* Body */}
          <div className="p-6 sm:p-8 overflow-y-auto flex-1 bg-white dark:bg-slate-900">
            <div className="flex items-center justify-between mb-6 pb-6 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-yellow-500 font-black text-lg">★ {article.score}</span>
                <span className="text-slate-300 text-xs">AI Score</span>
              </div>
              
              <div className="flex gap-3">
                {/* [수정] 공유 버튼에 handleShare 연결 */}
                <button 
                  onClick={handleShare}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-800 rounded-xl font-bold text-sm text-slate-600 dark:text-slate-300 hover:bg-cyan-50 dark:hover:bg-cyan-900/30 hover:text-cyan-600 transition-colors"
                >
                  <Share2 size={16} /> Share
                </button>
                <a 
                  href={article.link} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900 dark:bg-cyan-600 text-white rounded-xl font-bold text-sm hover:opacity-90 transition-opacity"
                >
                  Read Original <ExternalLink size={16} />
                </a>
              </div>
            </div>

            <p className="text-slate-600 dark:text-slate-300 text-lg leading-relaxed mb-8">
              {article.summary}
            </p>

            <div className="flex justify-center gap-6">
              <button 
                onClick={() => onVote(article.id, 'likes')}
                className="flex flex-col items-center gap-1 group"
              >
                <div className="w-14 h-14 rounded-2xl bg-slate-50 dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:bg-cyan-50 dark:group-hover:bg-cyan-900/20 group-hover:text-cyan-500 transition-all group-active:scale-95">
                  <ThumbsUp size={24} />
                </div>
                <span className="text-xs font-bold text-slate-400">{article.likes}</span>
              </button>

              <button 
                onClick={() => onVote(article.id, 'dislikes')}
                className="flex flex-col items-center gap-1 group"
              >
                <div className="w-14 h-14 rounded-2xl bg-slate-50 dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:bg-pink-50 dark:group-hover:bg-pink-900/20 group-hover:text-pink-500 transition-all group-active:scale-95">
                  <ThumbsDown size={24} />
                </div>
                <span className="text-xs font-bold text-slate-400">{article.dislikes}</span>
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
