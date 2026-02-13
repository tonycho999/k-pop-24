'use client';

interface CategoryNavProps {
  active: string;
  setCategory: (c: string) => void;
}

export default function CategoryNav({ active, setCategory }: CategoryNavProps) {
  // [복구 완료] 화면에 보이는 이름(label)과 실제 DB 검색용 값(id)을 분리
  const categories = [
    { id: 'All', label: 'All Trends' },      // 화면: All Trends, 실제값: All
    { id: 'K-Pop', label: 'K-POP' },         // 화면: K-POP, 실제값: K-Pop (DB와 일치)
    { id: 'K-Drama', label: 'K-Drama' },
    { id: 'K-Movie', label: 'K-Movie' },
    { id: 'K-Entertain', label: 'K-Entertain' },
    { id: 'K-Culture', label: 'K-Culture' },
  ];

  return (
    // [유지] pt-1 pb-0 mb-0: 여백 최소화 설정
    <nav className="flex gap-2 sm:gap-3 overflow-x-auto pt-1 pb-0 mb-0 scrollbar-hide">
      {categories.map((cat) => (
        <button
          key={cat.id}
          onClick={() => setCategory(cat.id)} // 클릭 시 실제값(id) 전달
          className={`
            px-4 sm:px-5 py-1.5 sm:py-2 rounded-full text-xs sm:text-sm font-black transition-all whitespace-nowrap
            ${active === cat.id 
              ? 'bg-cyan-500 text-white shadow-md shadow-cyan-200 dark:shadow-none scale-105' 
              : 'bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 border border-slate-100 dark:border-slate-800'}
          `}
        >
          {cat.label} {/* 화면에는 label(대문자 등) 보여줌 */}
        </button>
      ))}
    </nav>
  );
}
