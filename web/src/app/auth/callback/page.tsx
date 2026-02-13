'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

export default function AuthCallback() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    // 1. URL에 에러가 포함되어 있는지 확인 (#error_description=...)
    const hash = window.location.hash;
    if (hash && hash.includes('error')) {
      setErrorMsg('Login failed: ' + hash);
      return;
    }

    // 2. 세션 교환 시도
    const handleAuth = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        
        if (error) {
          throw error;
        }

        if (session) {
          // 로그인 성공 -> 메인으로 이동
          router.push('/');
        } else {
          // 세션이 없으면 잠시 대기 (Supabase가 처리 중일 수 있음)
          // 하지만 너무 오래 걸리면 문제
          supabase.auth.onAuthStateChange((event, session) => {
            if (event === 'SIGNED_IN' || session) {
               router.push('/');
            }
          });
        }
      } catch (err: any) {
        console.error('Auth Error:', err);
        setErrorMsg(err.message || 'Unknown authentication error');
      }
    };

    handleAuth();
  }, [router]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-white dark:bg-slate-950 p-4">
      {errorMsg ? (
        // 에러 발생 시 빨간 화면 표시
        <div className="max-w-md w-full bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <h2 className="text-xl font-bold text-red-600 mb-2">Login Error 😢</h2>
          <p className="text-sm text-red-500 break-words">{errorMsg}</p>
          <button 
            onClick={() => router.push('/')}
            className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition"
          >
            Go Back Home
          </button>
        </div>
      ) : (
        // 정상 로딩 화면
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-slate-200 border-t-cyan-500 rounded-full animate-spin"></div>
          <div className="text-center">
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">Signing in...</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Verifying your account</p>
          </div>
        </div>
      )}
    </div>
  );
}
