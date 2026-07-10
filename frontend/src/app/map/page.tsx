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

      // Fetch risk scores in parallel
      const combined: CombinedData[] = await Promise.all(
        transformers.map(async (t) => {
          const substation_name = t.substation_id ? subMap.get(t.substation_id) : 'Unknown';
          try {
            const scoreRes = await apiClient.get(`/transformers/${t.id}/risk-score`);
            return { ...t, ...scoreRes.data, id: t.id, substation_name };
          } catch {}
          return { ...t, anomaly_score: 0, risk_category: 'UNKNOWN', expected_lifetime_days: 0, substation_name };
        })
      );

      setData(combined);
    } catch (err) {
      console.error('Map data load failed', err);
    } finally {
      setLoading(false);
    }
  }

  const filtered = filter === 'ALL' ? data : data.filter(d => d.risk_category === filter);

  const criticalCount = data.filter(d => d.risk_category === 'CRITICAL').length;
  const highCount     = data.filter(d => d.risk_category === 'HIGH').length;
  const healthyCount  = data.filter(d => d.risk_category === 'LOW' || d.risk_category === 'HEALTHY').length;

  return (
    <div className="fixed inset-0 top-[80px] flex flex-col bg-slate-50">
      {/* ── Top toolbar ────────────────────────────────────────────── */}
      <div className="flex-shrink-0 flex items-center justify-between bg-white/90 backdrop-blur-md border-b border-slate-100 px-6 py-3 gap-4 z-10">

        <div className="flex items-center gap-3">
          <Link href="/dashboard"
            className="flex items-center gap-1.5 text-slate-500 hover:text-slate-900 text-sm font-medium transition-colors">
            <LayoutDashboard size={15} />
            <span className="hidden sm:inline">Dashboard</span>
          </Link>
          <span className="text-slate-300">/</span>
          <span className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
            <Zap size={15} className="text-blue-600" />
            Network Map
          </span>
        </div>

        {/* Risk filter pills */}
        <div className="flex items-center gap-2 flex-wrap">
          {[
            { key: 'ALL',      label: `All (${data.length})`,          color: 'bg-slate-100 text-slate-600 hover:bg-slate-200' },
            { key: 'CRITICAL', label: `Critical (${criticalCount})`,   color: 'bg-red-50 text-red-700 hover:bg-red-100' },
            { key: 'HIGH',     label: `High (${highCount})`,           color: 'bg-amber-50 text-amber-700 hover:bg-amber-100' },
            { key: 'LOW',      label: `Healthy (${healthyCount})`,     color: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100' },
          ].map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all border ${
                filter === f.key
                  ? 'border-blue-500 ring-2 ring-blue-100 bg-blue-600 text-white'
                  : `border-transparent ${f.color}`
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Refresh */}
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 font-medium transition-colors disabled:opacity-50"
        >
          <RotateCw size={15} className={loading ? 'animate-spin' : ''} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
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
