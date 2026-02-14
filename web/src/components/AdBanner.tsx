'use client';

import { useEffect, useState } from 'react';

// 배너 설정 데이터 (나중에 이곳만 수정하면 됩니다)
// probability: 노출 확률 (가중치), 높을수록 자주 나옴
// targetCountry: 특정 국가 코드 (예: 'KR', 'US'). 없으면('All') 전 세계 노출
const BANNER_CONFIG = [
  { 
    id: 1, 
    src: '/banner1.gif', 
    link: 'https://example.com/ad1', 
    probability: 50, // 50% 가중치
    targetCountry: 'All' 
  },
  { 
    id: 2, 
    src: '/banner2.gif', 
    link: 'https://example.com/ad2', 
    probability: 30, // 30% 가중치
    targetCountry: 'KR' // 한국에서만 보임
  },
  // 필요한 만큼 banner3, banner4... 추가 가능
];

export default function AdBanner() {
  const [selectedBanner, setSelectedBanner] = useState<any>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const selectBanner = async () => {
      // 1. 사용자 국가 확인 (무료 API 사용)
      let userCountry = 'All';
      try {
        const res = await fetch('https://ipapi.co/json/');
        const data = await res.json();
        userCountry = data.country_code; // 'KR', 'US' 등
      } catch (e) {
        console.warn('Country detect failed, assuming global');
      }

      // 2. 노출 가능한 배너 필터링
      const availableBanners = BANNER_CONFIG.filter(b => 
        b.targetCountry === 'All' || b.targetCountry === userCountry
      );

      if (availableBanners.length === 0) {
        setIsVisible(false);
        return;
      }

      // 3. 확률에 따른 배너 추첨 (가중치 뽑기)
      // 배너들을 probability만큼 배열에 복사해서 넣고 랜덤으로 하나 뽑음
      // 예: A(50), B(10) -> [A,A,A,A,A, B] 중에서 랜덤
      const weightedPool: any[] = [];
      availableBanners.forEach(banner => {
        for (let i = 0; i < banner.probability; i++) {
          weightedPool.push(banner);
        }
      });

      if (weightedPool.length > 0) {
        const randomIndex = Math.floor(Math.random() * weightedPool.length);
        setSelectedBanner(weightedPool[randomIndex]);
        setIsVisible(true);
      }
    };

    selectBanner();
  }, []);

  // 배너가 없거나 선택되지 않았으면 아예 렌더링하지 않음 (공간 차지 X)
  if (!isVisible || !selectedBanner) return null;

  return (
    <div className="w-full mt-2 mb-4 animate-in fade-in zoom-in duration-500">
      <a 
        href={selectedBanner.link} 
        target="_blank" 
        rel="noopener noreferrer"
        className="block w-full overflow-hidden rounded-2xl shadow-md border border-slate-100 dark:border-slate-800 relative group"
      >
        {/* 'AD' 마크 표시 */}
        <div className="absolute top-0 right-0 bg-slate-200 dark:bg-slate-700 text-[10px] text-slate-500 px-1.5 py-0.5 rounded-bl-lg z-10">
          AD
        </div>
        
        {/* 실제 배너 이미지 */}
        <img 
          src={selectedBanner.src} 
          alt="Advertisement" 
          className="w-full h-auto object-cover max-h-[120px] sm:max-h-[160px] transition-transform group-hover:scale-[1.01]"
          onError={(e) => {
            // 이미지가 깨지거나 파일이 없으면 배너 숨김
            e.currentTarget.style.display = 'none';
            setIsVisible(false);
          }}
        />
      </a>
    </div>
  );
}
