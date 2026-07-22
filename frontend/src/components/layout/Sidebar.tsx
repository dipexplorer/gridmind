"use client";

import { LayoutDashboard, Zap, Map, Settings, LifeBuoy, LogOut, Brain } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'AI Analytics', path: '/ml-analytics', icon: Brain },
    // { name: 'Assets', path: '/assets', icon: Zap }, // Temporarily disabled until implemented
    // { name: 'Map View', path: '/map', icon: Map },
    // { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 h-screen fixed left-0 top-0 bg-[#0B1121] border-r border-slate-800 flex flex-col z-50">
      {/* Brand */}
      <div className="p-6 flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/20 ring-1 ring-white/10">
          <Zap size={20} className="fill-white/20" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight leading-none">
            GridMind
          </h2>
          <p className="text-[10px] font-medium text-slate-400 mt-1 uppercase tracking-widest">APDCL Division</p>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-4 space-y-1.5">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 px-3">Analytics</div>
        {navItems.map((item) => {
          const isActive = pathname === item.path || pathname.startsWith(`${item.path}/`);
          const Icon = item.icon;
          return (
            <Link key={item.name} href={item.path} className="block">
              <div className={`
                flex items-center space-x-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative overflow-hidden
                ${isActive 
                  ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 shadow-inner' 
                  : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent'
                }
              `}>
                {isActive && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-1/2 bg-indigo-500 rounded-r-full" />}
                <Icon size={18} className={`transition-transform duration-200 ${isActive ? 'scale-110' : 'group-hover:scale-110'}`} />
                <span className={`text-sm font-medium ${isActive ? 'font-semibold text-indigo-300' : ''}`}>
                  {item.name}
                </span>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-slate-800/50 space-y-2">
        <button className="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 transition-colors w-full text-left text-sm font-medium">
          <LifeBuoy size={18} />
          <span>Support</span>
        </button>
        <button className="flex items-center space-x-3 px-3 py-2.5 rounded-xl text-slate-400 hover:bg-red-500/10 hover:text-red-400 transition-colors w-full text-left text-sm font-medium">
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
