import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Footer from '@/components/Footer'; // 💡 [추가] Footer 컴포넌트 불러오기

const inter = Inter({ subsets: ['latin'] });

// [SEO] 구글 검색 노출을 위한 메타데이터
export const metadata: Metadata = {
  title: 'K-ENTER 24 | Real-time K-Pop & K-Drama News',
  description: 'The world\'s fastest source for K-Entertainment news. Monitoring 1,200+ articles daily in real-time. BTS, BLACKPINK, NewJeans updates instantly.',
  keywords: [
    'K-Pop', 'K-Drama', 'Korean News', 'Real-time News', 'BTS', 'BLACKPINK', 'NewJeans',
    'Kpop','Kdrama', 'Hallyu','Idol', 'Trainee','Comeback', 'Debut', 'Bias', 'Maknae',
    'Hyung', 'Noona', 'Oppa', 'Unnie', 'K-pop trainee', 'K-pop survival show', 'K-pop agency', 'K-pop fan meeting',
    'K-pop lightstick', 'K-pop tour', 'Fanclub', 'Scandal', 
    'K-drama', 'Korean drama','Korean actors','Korean actresses','K-drama cast', 'K-drama OST','K-drama 2026', 'Best K-drama',
    'Romantic K-drama','Historical K-drama', 'K-drama Netflix', 'Korean drama recommendations', 'Korean celebrity', 'Korean star',
    'Korean heartthrob', 'Korean actor Instagram', 'Korean actress profile', 'Korean drama awards','Korean drama list', 'New Korean drama',
  ],
  openGraph: {
    title: 'K-ENTER 24',
    description: 'Real-time K-News Radar. Stop waiting for translations.',
    url: 'https://k-enter24.com',
    siteName: 'K-ENTER 24',
    images: [
      {
        url: '/og-image.png', // public 폴더에 대표 이미지 하나 넣어주시면 좋습니다.
        width: 1200,
        height: 630,
      },
    ],
    locale: 'en_US',
    type: 'website',
  },
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {/* 💡 [추가] 콘텐츠 영역이 화면 전체 높이를 차지하도록 하여 Footer를 맨 아래로 밀어냅니다 */}
        <main className="min-h-screen">
          {children}
        </main>
        {/* 💡 [추가] 모든 페이지 하단에 Footer 고정 */}
        <Footer />
      </body>
    </html >
  );
}
