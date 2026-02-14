import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // domains 대신 remotePatterns 사용 (보안 강화 및 경고 해결)
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**', // 모든 외부 이미지 허용 (크롤링 특성상 필요)
      },
    ],
  },
};

export default nextConfig;
