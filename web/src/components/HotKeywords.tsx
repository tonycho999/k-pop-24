'use client';

// 임시 데이터 (나중에 DB keywords 컬럼을 집계해서 props로 받아도 됨)
const KEYWORDS = [
  { rank: 1, text: "BTS Jin Solo", percent: 95 },
  { rank: 2, text: "NewJeans Comeback", percent: 80 },
  { rank: 3, text: "AESPA Drama", percent: 65 },
  { rank: 4, text: "BlackPink Contract", percent: 50 },
  { rank: 5, text: "SEVENTEEN Tour", percent: 40 },
];

export default function HotKeywords() {
  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-2xl p-6 h-full">
      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        🔥 Hot Keywords <span className="text-xs text-gray-500 font-normal">(Live)</span>
      </h3>
      <div className="space-y-4">
        {KEYWORDS.map((item, idx) => (
          <div key={idx} className="group">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-300 font-medium">
                <span className="text-cyan-400 mr-2">{item.rank}.</span>
                {item.text}
              </span>
              <span className="text-gray-500 text-xs">{item.percent}%</span>
            </div>
            {/* 게이지 바 */}
            <div className="w-full bg-gray-800 rounded-full h-2.5 overflow-hidden">
              <div 
                className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2.5 rounded-full transition-all duration-1000 group-hover:from-pink-500 group-hover:to-purple-500" 
                style={{ width: `${item.percent}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
