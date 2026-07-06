'use client';

import { usePathname } from 'next/navigation';
import AuthGuard from '@/components/AuthGuard';

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/login';

  if (isLoginPage) {
    return <>{children}</>;
  }

  return (
    <AuthGuard>
      {/* Navigation Bar (Floating Style) */}
      <nav className="fixed top-4 left-4 right-4 bg-white/90 backdrop-blur-md border border-slate-200 rounded-2xl shadow-sm z-50 flex items-center justify-between px-6 py-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <span className="font-bold text-xl tracking-tight text-slate-900">GridMind AI</span>
        </div>
        <div className="flex items-center gap-4 text-sm font-medium">
          <a href="/dashboard" className="text-blue-600 hover:text-blue-500 transition-colors">Dashboard</a>
          <a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Transformers</a>
          <a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Reports</a>
          <div className="w-8 h-8 rounded-full bg-slate-200 border border-slate-300"></div>
        </div>
      </nav>
      
      {/* Main Content Area */}
      <main className="pt-24 pb-10 px-4 md:px-8 max-w-[1600px] mx-auto">
        {children}
      </main>
    </AuthGuard>
  );
}
