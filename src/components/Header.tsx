'use client';
import { createClient } from '@supabase/supabase-js';
import { useEffect, useState } from 'react';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default function Header() {
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user);
    };
    getUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogin = async () => {
    alert("구글 로그인 기능 연결 준비 중!"); 
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  return (
    <nav className="flex justify-between items-center py-6 mb-8 border-b border-gray-800">
      <div className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-pink-600">
        K-POP 24
      </div>
      <div>
        {user ? (
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-400">{user.email?.split('@')[0]}님</span>
            <button 
              onClick={handleLogout}
              className="px-4 py-2 text-sm font-bold text-gray-300 hover:text-white border border-gray-700 rounded-full hover:bg-gray-800 transition-all"
            >
              Log Out
            </button>
          </div>
        ) : (
          <button 
            onClick={handleLogin}
            className="px-6 py-2 text-sm font-bold text-black bg-white rounded-full hover:bg-gray-200 transition-all shadow-[0_0_15px_rgba(255,255,255,0.3)]"
          >
            Log In / Subscribe
          </button>
        )}
      </div>
    </nav>
  );
}
