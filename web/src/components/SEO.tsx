'use client';

import Head from 'next/head';

interface SEOProps {
  title?: string;
  description?: string;
  image?: string;
  url?: string;
  articleData?: {
    publishedTime: string;
    author: string;
    category: string;
  };
}

/**
 * ✅ SEO(검색), AEO(답변), GEO(AI 인용)를 위한 통합 메타데이터 컴포넌트
 * 구글 검색 상단 노출은 물론, AI 엔진이 우리 기사를 출처로 인용하도록 유도합니다.
 */
export default function SEO({ 
  title = "K-Enter24 | Real-time K-Culture News & AI Analysis",
  description = "Get the latest K-Pop, K-Drama, and K-Culture trends analyzed by AI. The fastest source for Hallyu fans worldwide.",
  image = "https://k-enter24.com/og-image.png",
  url = "https://k-enter24.com",
  articleData
}: SEOProps) {
  
  // AEO/GEO 최적화의 핵심: AI 엔진이 데이터를 논리적으로 이해하게 돕는 JSON-LD
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": articleData ? "NewsArticle" : "WebSite",
    "headline": title,
    "description": description,
    "image": [image],
    "datePublished": articleData?.publishedTime || new Date().toISOString(),
    "author": [{
      "@type": "Organization",
      "name": "K-Enter24 AI Editor",
      "url": "https://k-enter24.com"
    }],
    "publisher": {
      "@type": "Organization",
      "name": "K-Enter24",
      "logo": {
        "@type": "ImageObject",
        "url": "https://k-enter24.com/logo.png"
      }
    }
  };

  return (
    <>
      {/* 1. 기본 SEO 메타 태그 */}
      <title>{title}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={url} />

      {/* 2. Open Graph (SNS 및 메시지 공유 최적화) */}
      <meta property="og:type" content={articleData ? "article" : "website"} />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={image} />
      <meta property="og:url" content={url} />
      <meta property="og:site_name" content="K-Enter24" />

      {/* 3. Twitter Card (X에서 기사 카드 형태 노출) */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={image} />

      {/* 4. ✅ AEO/GEO 최적화 핵심: 구조화된 데이터 삽입 */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      
      {/* 검색 로봇 수집 설정 */}
      <meta name="robots" content="index, follow, max-image-preview:large" />
    </>
  );
}
