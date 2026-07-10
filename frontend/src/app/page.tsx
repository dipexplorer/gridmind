"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { ShieldAlert, Lock, Zap, ArrowRight, Server, Activity } from "lucide-react";

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setMounted(true);
    
    // Automatically redirect to dashboard if already logged in
    const checkSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        router.push('/dashboard');
      }
    };
    checkSession();
  }, [router]);

  if (!mounted) return null;

  return (
    <main className="min-h-screen bg-slate-50 relative flex items-center justify-center overflow-hidden selection:bg-blue-200">
      
      {/* Background Effects (Light Theme) */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#e2e8f0_1px,transparent_1px),linear-gradient(to_bottom,#e2e8f0_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-50" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-100 rounded-full blur-[100px] pointer-events-none" />
      </div>

      {/* Gateway Container */}
      <div className="relative z-10 w-full max-w-lg px-6">
        
        {/* Top Badges */}
        <div className="flex justify-center gap-3 mb-8">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-50 border border-red-200 text-red-600 text-[10px] font-extrabold tracking-widest uppercase shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
            Classified System
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-slate-200 text-slate-500 text-[10px] font-extrabold tracking-widest uppercase shadow-sm">
            <Server size={10} />
            Node: GHY-01
          </div>
        </div>

        {/* Main Card */}
        <div className="bg-white/80 backdrop-blur-xl border border-slate-200/80 rounded-3xl p-10 text-center shadow-xl shadow-slate-200/50">
          
          <div className="w-20 h-20 mx-auto bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/25 ring-1 ring-white/50 mb-6 relative group">
            <div className="absolute inset-0 bg-blue-400/20 rounded-2xl blur-xl group-hover:blur-2xl transition-all duration-500" />
            <Zap size={36} className="text-white relative z-10" />
          </div>

          <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">
            GridMind <span className="text-blue-600">AI</span>
          </h1>
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mb-8">
            Predictive Intelligence Core
          </h2>

          <div className="bg-amber-50/80 rounded-2xl p-5 border border-amber-100 mb-8 text-left space-y-3 shadow-inner">
            <div className="flex items-start gap-3">
              <ShieldAlert size={16} className="text-amber-600 shrink-0 mt-0.5" />
              <p className="text-xs text-amber-800/80 leading-relaxed font-semibold">
                <span className="text-amber-600 font-extrabold">WARNING:</span> This is a secure APDCL intranet portal. Unauthorized access, probing, or exploitation is strictly prohibited and actively monitored.
              </p>
            </div>
          </div>

          <Link 
            href="/login"
            className="group relative flex items-center justify-center gap-3 w-full bg-blue-600 text-white px-6 py-4 rounded-xl font-bold text-sm hover:bg-blue-700 transition-all active:scale-[0.98] shadow-md shadow-blue-500/20"
          >
            <Lock size={16} className="text-white/80" />
            Authenticate & Enter
            <ArrowRight size={16} className="text-white/80 group-hover:translate-x-1 transition-transform" />
          </Link>
          
        </div>

        {/* Footer info */}
        <div className="mt-8 text-center flex flex-col items-center gap-2">
          <div className="flex items-center gap-2 text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">
            <Activity size={12} className="text-emerald-500" />
            Core Systems Online
          </div>
          <p className="text-[10px] font-medium text-slate-400">
            &copy; {new Date().getFullYear()} Assam Power Distribution Company Ltd.
          </p>
        </div>

      </div>
    </main>
  );
}
