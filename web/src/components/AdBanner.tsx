'use client';

import Image from 'next/image';
import Link from 'next/link';

export default function AdBanner() {
  // 💰 대표님의 실제 Involve Asia 수익 링크 적용 완료!
  const AD_LINK = "https://invl.us/clncdlz"; 
  
  // 🖼️ byFood 캠페인에 어울리는 고화질 음식/여행 배너 이미지 (추후 교체 가능)
  const AD_IMAGE_PC = "https://images.unsplash.com/photo-1580651315530-69c8e0026377?auto=format&fit=crop&q=80&w=1200&h=120"; 
  const AD_IMAGE_MOBILE = "https://images.unsplash.com/photo-1580651315530-69c8e0026377?auto=format&fit=crop&q=80&w=600&h=150";

  // 배너 활성화 (광고 보이게 설정)
  const isPlaceholder = false; 

  if (isPlaceholder) {
    return (
      <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center p-4 border border-slate-200 dark:border-slate-700 min-h-[90px]">
         <span className="text-slate-400 text-sm font-bold tracking-widest uppercase">Advertisement Space</span>
      </div>
    );
  }

  return (
    <div className="w-full relative rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow group border border-slate-100 dark:border-slate-800">
      <Link href={AD_LINK} target="_blank" rel="noopener noreferrer" className="block w-full">
        {/* 우측 상단 AD 뱃지 (광고임을 명시) */}
        <div className="absolute top-2 right-2 bg-black/30 backdrop-blur-md text-white text-[9px] px-1.5 py-0.5 rounded z-10 font-bold tracking-wider">
          AD
        </div>
        
        {/* 💻 PC용 배너 (md 이상 화면에서 노출) */}
        <div className="hidden md:block relative w-full h-[90px] lg:h-[120px]">
          <Image 
            src={AD_IMAGE_PC} 
            alt="Sponsored Advertisement" 
            fill 
            className="object-cover group-hover:scale-[1.02] transition-transform duration-500" 
            unoptimized 
          />
        </div>
        
        {/* 📱 모바일용 배너 (md 미만 화면에서 노출) */}
        <div className="block md:hidden relative w-full h-[70px] sm:h-[90px]">
          <Image 
            src={AD_IMAGE_MOBILE} 
            alt="Sponsored Advertisement" 
            fill 
            className="object-cover group-hover:scale-[1.02] transition-transform duration-500" 
            unoptimized 
          />
        </div>
      </Link>
    </div>
  );
}
