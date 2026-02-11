'use client';

const REACTIONS = [
  { country: "USA", flag: "🇺🇸", text: "Positive vibes, expecting Billboard entry!" },
  { country: "Japan", flag: "🇯🇵", text: "Dome tour requests are flooding in." },
  { country: "China", flag: "🇨🇳", text: "Viral on Weibo, merch sold out instantly." },
  { country: "Korea", flag: "🇰🇷", text: "All-kill on charts, domestic fans love it." },
  { country: "Brazil", flag: "🇧🇷", text: "Come to Brazil! We are waiting!" },
];

export default function GlobalReactions() {
  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-2xl p-6 h-full">
      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        🌍 Global Reactions <span className="text-xs text-gray-500 font-normal">(AI Analzyed)</span>
      </h3>
      <div className="space-y-4">
        {REACTIONS.map((item, idx) => (
          <div key={idx} className="flex items-start gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors">
            <span className="text-2xl select-none">{item.flag}</span>
            <div>
              <div className="text-xs text-gray-500 mb-0.5">{item.country}</div>
              <div className="text-sm text-gray-200 leading-snug">
                {item.text}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
