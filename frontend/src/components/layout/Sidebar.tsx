'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: '📊' },
    { name: 'Transformers', path: '/transformers', icon: '⚡' },
    { name: 'Map View', path: '/map', icon: '🗺️' },
    { name: 'Admin', path: '/admin', icon: '⚙️' },
  ];

  return (
    <aside className="w-64 h-screen fixed left-0 top-0 bg-slate-900 border-r border-slate-800 flex flex-col">
      <div className="p-6 flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold shadow-md">
          G
        </div>
        <h2 className="text-xl font-bold text-white tracking-tight">
          GridMind
        </h2>
      </div>

      <nav className="flex-1 px-4 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link key={item.name} href={item.path} className="block">
              <div className={`
                flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors
                ${isActive 
                  ? 'bg-indigo-600 text-white' 
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                }
              `}>
                <span className="text-lg">{item.icon}</span>
                <span className={`font-medium ${isActive ? 'font-semibold' : ''}`}>
                  {item.name}
                </span>
              </div>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
