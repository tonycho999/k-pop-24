'use client';

import { useEffect, useRef } from 'react';

export default function AdsterraBanner() {
  const bannerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 이미 스크립트가 로드되었으면 중복 실행 방지 (React Strict Mode 대응)
    if (!bannerRef.current || bannerRef.current.childNodes.length > 0) return;

    // 1. 설정 스크립트 생성
    const confScript = document.createElement('script');
    confScript.type = 'text/javascript';
    confScript.innerHTML = `
      atOptions = {
        'key' : '8f6270cc2eff024be5d90122a4d2124e',
        'format' : 'iframe',
        'height' : 90,
        'width' : 728,
        'params' : {}
      };
    `;

    // 2. 실행 스크립트 생성
    const invokeScript = document.createElement('script');
    invokeScript.type = 'text/javascript';
    invokeScript.src = 'https://www.highperformanceformat.com/8f6270cc2eff024be5d90122a4d2124e/invoke.js';
    invokeScript.async = true;

    // 3. div 안에 스크립트 삽입
    bannerRef.current.appendChild(confScript);
    bannerRef.current.appendChild(invokeScript);
  }, []);

  return (
    <div className="w-full flex justify-center my-6 overflow-hidden min-h-[90px]">
      {/* 이 div 안에 Adsterra 광고가 그려집니다 */}
      <div ref={bannerRef}></div>
    </div>
  );
}
