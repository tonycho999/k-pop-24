'use client';
import { createClient } from '@supabase/supabase-js';
import { useEffect, useState } from 'react';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default function Header() {
  const [user, setUser] = useState<any>(null);
  const [menuOpen, setMenuOpen] = useState(false);

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
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${location.origin}/auth/callback` },
    });
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setMenuOpen(false);
  };

  return (
    <nav className="flex justify-between items-center py-6 px-4 md:px-0 mb-4 border-b border-gray-800/50">
      {/* 로고: K-PULSE (네온 효과) */}
      <div className="text-3xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-600 drop-shadow-[0_0_10px_rgba(168,85,247,0.5)]">
        K-PULSE <span className="text-xs text-gray-500 font-medium tracking-normal align-top">24</span>
      </div>

      <div className="relative">
        {user ? (
          <div>
            <button 
              onClick={() => setMenuOpen(!menuOpen)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-900 border border-gray-700 rounded-full hover:border-cyan-500 transition-all"
            >
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              <span className="text-sm font-bold text-gray-200">{user.email?.split('@')[0]}</span>
            </button>

            {/* 드롭다운 메뉴 */}
            {menuOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-gray-900 border border-gray-700 rounded-xl shadow-[0_0_20px_rgba(0,0,0,0.8)] overflow-hidden z-50">
                <div className="px-4 py-3 border-b border-gray-800">
                  <p className="text-xs text-gray-500">Status</p>
                  <p className="text-sm text-cyan-400 font-bold">Free Plan</p>
                </div>
                <a 
                  href="https://app.lemonsqueezy.com/buy/..." 
                  target="_blank"
                  className="block px-4 py-3 text-sm text-white hover:bg-purple-900/50 transition-colors flex justify-between items-center"
                >
                  Subscribe ($15/yr) <span className="text-xs bg-purple-600 px-1 rounded">PRO</span>
                </a>
                <button className="w-full text-left px-4 py-3 text-sm text-gray-400 hover:text-white hover:bg-gray-800">
                  Settings
                </button>
                <button 
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-3 text-sm text-red-400 hover:bg-gray-800 border-t border-gray-800"
                >
                  Log Out
                </button>
              </div>
            )}
          </div>
        ) : (
          <button 
            onClick={handleLogin}
            className="px-6 py-2 text-sm font-bold text-black bg-cyan-400 rounded-full hover:bg-cyan-300 transition-all shadow-[0_0_15px_rgba(34,211,238,0.4)]"
          >
            Log In
          </button>
        )}
      </div>
    </nav>
  );
}
