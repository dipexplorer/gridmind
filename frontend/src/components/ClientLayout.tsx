'use client';

import { usePathname } from 'next/navigation';
import AuthGuard from '@/components/AuthGuard';
import { NotificationBell } from '@/components/layout/NotificationBell';

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/login';

  if (isLoginPage) {
    return <>{children}</>;
  }

  return (
    <AuthGuard>
      {/* Navigation Bar (Floating Style) */}
      <nav className="fixed top-4 left-4 right-4 bg-white/80 backdrop-blur-xl border border-slate-200/60 rounded-2xl shadow-sm z-50 flex items-center justify-between px-6 py-3 transition-all">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-blue-600 rounded-xl flex items-center justify-center shadow-md shadow-blue-500/20 ring-1 ring-white/20">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <span className="font-bold text-xl tracking-tight text-slate-900 leading-none block">GridMind <span className="text-blue-600">AI</span></span>
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest block">Command Center</span>
          </div>
        </div>

        {/* Links */}
        <div className="hidden md:flex items-center gap-6">
          <a href="/dashboard" className={`text-sm font-semibold transition-colors ${pathname === '/dashboard' || pathname.startsWith('/dashboard') ? 'text-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>
            Dashboard
          </a>
          <a href="/map" className={`text-sm font-semibold transition-colors ${pathname === '/map' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>
            Network Map
          </a>
          <a href="/assets" className={`text-sm font-semibold transition-colors ${pathname === '/assets' ? 'text-blue-600' : 'text-slate-500 hover:text-slate-900'}`}>
            Assets Directory
          </a>
        </div>

        {/* User / Actions */}
        <div className="flex items-center gap-4">
          <NotificationBell />
          <div className="hidden sm:block text-right border-l border-slate-200 pl-4">
            <p className="text-sm font-bold text-slate-700 leading-tight">Admin User</p>
            <p className="text-[10px] font-semibold text-slate-400 uppercase">System Operator</p>
          </div>
          <div className="w-9 h-9 rounded-full bg-slate-100 border-2 border-white ring-1 ring-slate-200 flex items-center justify-center text-slate-600 cursor-pointer hover:bg-slate-200 transition-colors shadow-sm">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
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
