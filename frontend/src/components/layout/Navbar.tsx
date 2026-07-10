'use client';
import { Bell, Search, User } from 'lucide-react';

export default function Navbar() {
  return (
    <header className="h-16 w-full fixed top-0 right-0 left-64 z-10 bg-white/80 backdrop-blur-md border-b border-slate-100 flex items-center justify-between px-8">
      <div className="flex items-center text-slate-800">
        <h1 className="text-lg font-bold font-heading">Command Center</h1>
      </div>

      <div className="flex items-center space-x-6">
        {/* Search */}
        <div className="hidden md:flex items-center bg-slate-50 border border-slate-100 rounded-full px-3 py-1.5 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-100 transition-all">
          <Search size={16} className="text-slate-400 mr-2" />
          <input 
            type="text" 
            placeholder="Search network..." 
            className="bg-transparent border-none focus:outline-none text-sm text-slate-700 placeholder-slate-400 w-48"
          />
        </div>
        
        {/* Notifications */}
        <button className="relative p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-full transition-colors">
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
        </button>
        
        {/* Profile */}
        <div className="flex items-center space-x-3 pl-4 border-l border-slate-100 cursor-pointer group">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-bold text-slate-700 group-hover:text-indigo-600 transition-colors">Admin User</p>
            <p className="text-[10px] font-semibold text-slate-400 uppercase">System Operator</p>
          </div>
          <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 shadow-sm ring-2 ring-white border border-slate-200">
            <User size={18} />
          </div>
        </div>
      </div>
    </header>
  );
}
