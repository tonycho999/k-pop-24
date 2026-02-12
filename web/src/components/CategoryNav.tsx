'use client';

// 요청하신 카테고리 순서와 명칭으로 교체되었습니다.
const CATEGORIES = [
  { label: 'All Trends', value: 'All' },
  { label: 'K-POP', value: 'k-pop' },
  { label: 'K-Drama', value: 'k-drama' },
  { label: 'K-Movie', value: 'k-movie' },
  { label: 'K-Entertain', value: 'k-entertain' },
  { label: 'K-Culture', value: 'k-culture' }
];

export default function CategoryNav({ active, setCategory }: { active: string, setCategory: (v: string) => void }) {
  return (
    <nav className="flex gap-2 overflow-x-auto pb-4 mb-6 scrollbar-hide">
      {CATEGORIES.map((tab) => (
        <button
          key={tab.value}
          onClick={() => setCategory(tab.value)}
          className={`px-8 py-2.5 rounded-xl text-sm font-bold transition-all whitespace-nowrap border ${
            active === tab.value 
            ? 'bg-cyan-400 text-white border-cyan-400 shadow-md shadow-cyan-100' 
            : 'bg-white text-slate-500 border-slate-100 hover:border-cyan-200 hover:text-cyan-500 shadow-sm'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
