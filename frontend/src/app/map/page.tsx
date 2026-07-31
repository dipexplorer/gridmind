"use client";

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { AlertTriangle, Filter, LayoutDashboard, RotateCw, Zap } from 'lucide-react';

// Dynamic import - avoids SSR crash because Leaflet uses window
const TransformerMap = dynamic(() => import('@/components/map/TransformerMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-slate-100">
      <div className="text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-3" />
        <p className="text-slate-500 text-sm font-medium">Loading Map…</p>
      </div>
    </div>
  ),
});

interface Transformer { id: string; name: string; transformer_code: string; rated_kva: number; location: string; address_text?: string; district?: string; substation_id?: string; operational_status: string; }
interface RiskScore   { transformer_id: string; anomaly_score: number; risk_category: string; expected_lifetime_days: number; }
interface CombinedData extends Transformer, Partial<RiskScore> { substation_name?: string; }

export default function NetworkMapPage() {
  const [data, setData]     = useState<CombinedData[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('ALL');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      // Fetch substations map
      let subMap = new Map<string, string>();
      try {
        const subRes = await apiClient.get('/substations/');
        subMap = new Map(subRes.data.map((s: any) => [s.id, s.name]));
      } catch {}

      // Fetch transformers
      const trRes = await apiClient.get('/transformers/');
      const transformers: Transformer[] = trRes.data;

      // Map the live real-time status data already present in the transformers response
      // to the format the UI expects, avoiding 1362 separate API calls.
      const combined: CombinedData[] = transformers.map((t: any) => {
        const substation_name = t.substation_id ? subMap.get(t.substation_id) : 'Unknown';
        const score = (t.current_failure_risk || 0) * 100;
        const cat = (t.current_status || 'healthy').toUpperCase();
        return { 
          ...t, 
          anomaly_score: score, 
          risk_category: cat, 
          expected_lifetime_days: cat === 'HEALTHY' ? 365 : (cat === 'WARNING' ? 90 : 7), 
          substation_name 
        };
      });

      setData(combined);
    } catch (err) {
      console.error('Map data load failed', err);
    } finally {
      setLoading(false);
    }
  }

  const filtered = filter === 'ALL' ? data : data.filter(d => d.risk_category === filter);

  const criticalCount = data.filter(d => d.risk_category === 'CRITICAL').length;
  const warningCount  = data.filter(d => d.risk_category === 'WARNING').length;
  const healthyCount  = data.filter(d => d.risk_category === 'HEALTHY').length;
  const unknownCount  = data.filter(d => d.risk_category === 'UNKNOWN').length;

  return (
    <div className="fixed inset-0 top-[80px] flex flex-col bg-slate-50">
      {/* ── Top toolbar ────────────────────────────────────────────── */}
      <div className="flex-shrink-0 flex items-center justify-between bg-white/95 backdrop-blur-xl border-b border-slate-200/60 px-6 py-3 z-10 shadow-sm">

        {/* Left Side: Context & Actions */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-slate-100/80 px-3 py-1.5 rounded-lg border border-slate-200/50">
            <Link href="/dashboard"
              className="flex items-center gap-1.5 text-slate-500 hover:text-slate-900 text-sm font-medium transition-colors">
              <LayoutDashboard size={14} />
              <span className="hidden sm:inline">Dashboard</span>
            </Link>
            <span className="text-slate-300">/</span>
            <span className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
              <Zap size={14} className="text-blue-600 fill-blue-600/20" />
              Network Map
            </span>
          </div>

          <div className="h-6 w-px bg-slate-200"></div>

          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 text-sm text-slate-600 hover:text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-lg font-medium transition-colors disabled:opacity-50 border border-transparent hover:border-blue-100"
          >
            <RotateCw size={14} className={loading ? 'animate-spin text-blue-600' : ''} />
            <span className="hidden sm:inline">{loading ? 'Syncing...' : 'Refresh'}</span>
          </button>
        </div>

        {/* Right Side: Segmented Filter Controls */}
        <div className="flex items-center bg-slate-100/80 p-1 rounded-xl border border-slate-200/60 overflow-x-auto hide-scrollbar max-w-full">
          {[
            { key: 'ALL',      label: 'All',      count: data.length,    activeBg: 'bg-white shadow-sm ring-1 ring-slate-200 text-slate-800',    inactiveBg: 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50', indicator: 'bg-slate-400' },
            { key: 'CRITICAL', label: 'Critical', count: criticalCount,  activeBg: 'bg-white shadow-sm ring-1 ring-slate-200 text-red-700',      inactiveBg: 'text-slate-500 hover:text-red-700 hover:bg-red-50',         indicator: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]' },
            { key: 'WARNING',  label: 'Warning',  count: warningCount,   activeBg: 'bg-white shadow-sm ring-1 ring-slate-200 text-amber-700',    inactiveBg: 'text-slate-500 hover:text-amber-700 hover:bg-amber-50',     indicator: 'bg-amber-500' },
            { key: 'HEALTHY',  label: 'Healthy',  count: healthyCount,   activeBg: 'bg-white shadow-sm ring-1 ring-slate-200 text-emerald-700',  inactiveBg: 'text-slate-500 hover:text-emerald-700 hover:bg-emerald-50', indicator: 'bg-emerald-500' },
          ].filter(f => f.count > 0 || f.key === 'ALL').map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`relative flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
                filter === f.key ? f.activeBg : f.inactiveBg
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${f.indicator}`}></span>
              {f.label}
              <span className={`ml-1 text-xs px-1.5 py-0.5 rounded-md ${filter === f.key ? 'bg-slate-100 text-slate-600' : 'bg-slate-200/50 text-slate-500'}`}>
                {f.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Map area ────────────────────────────────────────────────── */}
      <div className="flex-1 relative overflow-hidden">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
              <p className="text-slate-600 font-semibold text-sm">Loading {data.length || '...'} transformer assets…</p>
              <p className="text-slate-400 text-xs mt-1">Fetching coordinates & AI risk scores</p>
            </div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
            <div className="text-center">
              <AlertTriangle size={40} className="text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500 font-semibold">No transformers match the selected filter.</p>
              <button onClick={() => setFilter('ALL')} className="mt-3 text-blue-600 text-sm font-medium hover:underline">
                Clear filter
              </button>
            </div>
          </div>
        ) : (
          <TransformerMap
            transformers={filtered}
            showSidePanel={true}
          />
        )}
      </div>
    </div>
  );
}
