'use client';

import { useRouter } from 'next/navigation';
import CategoryNav from '@/components/CategoryNav';
import InsightBanner from '@/components/InsightBanner';
import AdBanner from '@/components/AdBanner';

export default function ArticleTop({ insight }: { insight?: string }) {
  const router = useRouter();

  // 💡 기사 페이지에서 카테고리 메뉴를 클릭하면 메인 홈으로 돌아가게 만듭니다.
  const handleCategoryClick = () => {
    router.push('/');
  };

  return (
    <div className="flex flex-col gap-0 w-full mb-6">
      {/* 카테고리 네비게이션 */}
      <div className="mb-1 w-full overflow-hidden">
         <CategoryNav active="All" setCategory={handleCategoryClick} />
      </div>
      
      {/* 인사이트 배너 (현재 기사의 요약본을 흘려보냅니다) */}
      <div className="mt-0 w-full"> 
         <InsightBanner insight={insight} />
      </div>
      
      {/* 광고 배너 */}
      <div className="mt-2 w-full">
         <AdBanner />
      </div>
    </div>
  );
}
