import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ✅ [추가] 주소 끝에 슬래시(/)를 강제로 제거하여 주소를 하나로 통일합니다.
  // 예: k-enter24.com/ -> k-enter24.com으로 자동 리다이렉트
  trailingSlash: false, 

  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**', 
      },
    ],
  },
};

export default nextConfig;
