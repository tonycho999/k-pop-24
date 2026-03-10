'use client';

import { useEffect, useRef } from 'react';

export default function AdsterraNative() {
  const nativeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!nativeRef.current || nativeRef.current.childNodes.length > 0) return;

    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.async = true;
    script.dataset.cfasync = "false";
    // 스크린샷에 있던 src 주소를 넣습니다
    script.src = "https://pl28887567.effectivegatecpm.com/d26b0385523399170c268fb734e391a9/invoke.js";

    const containerDiv = document.createElement('div');
    // 스크린샷에 있던 id를 정확히 일치시켜야 합니다
    containerDiv.id = "container-d26b0385523399170c268fb734e391a9";

    nativeRef.current.appendChild(script);
    nativeRef.current.appendChild(containerDiv);
  }, []);

  return (
    <div className="w-full my-4 p-4 border rounded-xl bg-gray-50/50 dark:bg-gray-800/20">
      <div className="text-[10px] text-gray-400 mb-2 font-bold uppercase tracking-wider">Sponsored</div>
      <div ref={nativeRef} className="w-full flex justify-center"></div>
    </div>
  );
}
