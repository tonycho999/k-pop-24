'use client';

// 데이터가 없을 때 보여줄 기본값
const MOCK_VIBE = {
  excitement: 50,
  shock: 30,
  sadness: 20
};

export default function VibeCheck({ data }: { data?: any }) {
  const vibe = data || MOCK_VIBE;

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-2xl p-6 h-full flex flex-col justify-center">
      <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
        🔮 AI Vibe Check <span className="text-xs text-gray-500 font-normal">(Sentiment Analysis)</span>
      </h3>
      
      <div className="space-y-6">
        {/* 1. Excitement */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-pink-400 font-bold">🤩 Excitement</span>
            <span className="text-white">{vibe.excitement}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden shadow-[0_0_10px_rgba(236,72,153,0.2)]">
            <div 
              className="bg-gradient-to-r from-pink-500 to-purple-600 h-full rounded-full transition-all duration-1000" 
              style={{ width: `${vibe.excitement}%` }}
            ></div>
          </div>
        </div>

        {/* 2. Shock */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-yellow-400 font-bold">⚡ Shock / Buzz</span>
            <span className="text-white">{vibe.shock}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden shadow-[0_0_10px_rgba(250,204,21,0.2)]">
            <div 
              className="bg-gradient-to-r from-yellow-400 to-orange-500 h-full rounded-full transition-all duration-1000" 
              style={{ width: `${vibe.shock}%` }}
            ></div>
          </div>
        </div>

        {/* 3. Sadness */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-blue-400 font-bold">💧 Sadness / Serious</span>
            <span className="text-white">{vibe.sadness}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-3 overflow-hidden shadow-[0_0_10px_rgba(96,165,250,0.2)]">
            <div 
              className="bg-gradient-to-r from-cyan-400 to-blue-600 h-full rounded-full transition-all duration-1000" 
              style={{ width: `${vibe.sadness}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
}
