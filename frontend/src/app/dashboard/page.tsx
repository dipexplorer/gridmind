'use client';
import { useEffect, useState } from 'react';
import TransformerMap from '@/components/map/TransformerMap';
import { getTransformers, getLatestAiRun } from '@/lib/api';

export default function Dashboard() {
  const [transformers, setTransformers] = useState([]);
  const [aiRun, setAiRun] = useState<any>(null);

  useEffect(() => {
    // Fetch data from FastAPI
    getTransformers().then(setTransformers).catch(console.error);
    getLatestAiRun().then(setAiRun).catch(console.error);
  }, []);

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Grid Intelligence Dashboard</h1>
        <p className="text-slate-500 mt-1">Live overview of APDCL transformer network</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider">Total Transformers</h3>
          <p className="text-3xl font-bold text-slate-900 mt-2">{transformers.length}</p>
        </div>
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider">High Risk Assets</h3>
          <p className="text-3xl font-bold text-red-600 mt-2">
            {aiRun?.anomalies_detected || 0}
          </p>
        </div>
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider">Last AI Run</h3>
          <p className="text-lg font-semibold text-slate-900 mt-3">
            {aiRun ? new Date(aiRun.started_at).toLocaleString() : 'Never'}
          </p>
        </div>
      </div>

      {/* Map Section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm h-[600px] overflow-hidden">
        <TransformerMap transformers={transformers} />
      </div>

    </div>
  );
}
