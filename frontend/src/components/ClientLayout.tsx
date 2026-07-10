'use client';

import { useState, useRef, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import AuthGuard from '@/components/AuthGuard';
import { NotificationBell } from '@/components/layout/NotificationBell';
import { supabase } from '@/lib/supabaseClient';
import { UserCircle, LogOut, BookOpen, ChevronDown } from 'lucide-react';

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLoginPage = pathname === '/login';
  
  const [profileOpen, setProfileOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSignOut = async () => {
    localStorage.removeItem("supabase_token");
    await supabase.auth.signOut();
    router.push("/login");
  };

  if (isLoginPage) {
    return <>{children}</>;
  }

  return (
    <AuthGuard>
      {/* Navigation Bar (Floating Style) */}
      <nav className="fixed top-4 left-4 right-4 bg-white/80 backdrop-blur-xl border border-slate-200/60 rounded-2xl shadow-sm z-50 flex items-center justify-between px-6 py-3 transition-all">
        {/* Brand */}
        <Link href="/dashboard" className="flex items-center gap-3 group cursor-pointer">
          <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-blue-600 rounded-xl flex items-center justify-center shadow-md shadow-blue-500/20 ring-1 ring-white/20 group-hover:scale-105 transition-transform">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <span className="font-bold text-xl tracking-tight text-slate-900 leading-none block group-hover:text-blue-600 transition-colors">GridMind <span className="text-blue-600">AI</span></span>
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest block">Command Center</span>
          </div>
        </Link>

        {/* Links */}
        <div className="hidden md:flex items-center gap-6">
          <Link href="/dashboard" className={`text-sm font-semibold transition-colors ${pathname === '/dashboard' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>
            Dashboard
          </Link>
          <Link href="/map" className={`text-sm font-semibold transition-colors ${pathname === '/map' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>
            Network Map
          </Link>
          <Link href="/assets" className={`text-sm font-semibold transition-colors ${pathname === '/assets' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>
            Assets Directory
          </Link>
          <Link href="/dashboard/tickets" className={`text-sm font-semibold transition-colors ${pathname === '/dashboard/tickets' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>
            Tickets
          </Link>
          <Link href="/dashboard/settings" className={`text-sm font-semibold transition-colors ${pathname === '/dashboard/settings' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>
            Settings
          </Link>
        </div>

        {/* User / Actions */}
        <div className="flex items-center gap-4">
          <NotificationBell />
          
          <div className="relative" ref={dropdownRef}>
            <div 
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-3 cursor-pointer p-1 pr-2 rounded-full hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-200"
            >
              <div className="hidden sm:block text-right pl-2">
                <p className="text-sm font-bold text-slate-700 leading-tight">Admin User</p>
                <p className="text-[10px] font-semibold text-slate-400 uppercase">System Operator</p>
              </div>
              <div className="w-9 h-9 rounded-full bg-slate-100 border-2 border-white ring-1 ring-slate-200 flex items-center justify-center text-slate-600 shadow-sm">
                <UserCircle size={20} />
              </div>
              <ChevronDown size={14} className={`text-slate-400 transition-transform ${profileOpen ? 'rotate-180' : ''}`} />
            </div>

            {/* Dropdown Menu */}
            {profileOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-xl border border-slate-100 overflow-hidden py-2 animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="px-4 py-3 border-b border-slate-100 mb-1">
                  <p className="text-sm font-bold text-slate-800">Admin User</p>
                  <p className="text-xs text-slate-500">admin@apdcl.org</p>
                </div>
                
                <Link href="/dashboard/settings" onClick={() => setProfileOpen(false)} className="flex items-center gap-3 px-4 py-2 text-sm text-slate-600 hover:text-blue-600 hover:bg-blue-50 transition-colors">
                  <UserCircle size={16} />
                  My Profile
                </Link>
                
                <Link href="#" onClick={() => setProfileOpen(false)} className="flex items-center gap-3 px-4 py-2 text-sm text-slate-600 hover:text-blue-600 hover:bg-blue-50 transition-colors">
                  <BookOpen size={16} />
                  Documentation
                </Link>
                
                <div className="h-px bg-slate-100 my-1"></div>
                
                <button 
                  onClick={handleSignOut}
                  className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
                  <LogOut size={16} />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>
      
      {/* Main Content Area */}
      <main className="pt-24 pb-10 px-4 md:px-8 max-w-[1600px] mx-auto">
        {children}
      </main>
    </AuthGuard>
  );
}
