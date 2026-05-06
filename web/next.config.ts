import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ✅ 외부 이미지 도메인 허용 설정 추가
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**', // 모든 https 도메인의 이미지를 허용합니다.
      },
      {
        protocol: 'http',
        hostname: '**', // 간혹 http로 들어오는 오래된 뉴스 이미지도 허용합니다.
      }
    ],
  },
  // (기존에 있던 다른 설정들이 있다면 그대로 유지해주세요)
};

export default nextConfig;
