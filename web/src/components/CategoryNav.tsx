'use client';

interface CategoryNavProps {
  active: string;
  setCategory: (c: string) => void;
}

export default function CategoryNav({ active, setCategory }: CategoryNavProps) {
  const categories = ['All', 'K-POP', 'K-Drama', 'K-Movie', 'K-Entertain', 'K-Culture'];

  return (
    // [수정] pt-1 pb-0 mb-0: 하단 여백을 완전히 없애서 아래 배너와 붙게 설정
    <nav className="flex gap-2 sm:gap-3 overflow-x-auto pt-1 pb-0 mb-0 scrollbar-hide">
      {categories.map((cat) => (
        <button
          key={cat}
          onClick={() => setCategory(cat)}
          className={`
            /* [수정] py-2 -> py-1.8 (버튼 높이를 줄여서 더 컴팩트하게) */
            px-4 sm:px-5 py-1.8 sm:py-2 rounded-full text-xs sm:text-sm font-black transition-all whitespace-nowrap
            ${active === cat 
              ? 'bg-cyan-500 text-white shadow-md shadow-cyan-200 dark:shadow-none scale-105' 
              : 'bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 border border-slate-100 dark:border-slate-800'}
          `}
        >
          {cat}
        </button>
      ))}
    </nav>
  );
}
