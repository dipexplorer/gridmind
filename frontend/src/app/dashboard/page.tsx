"use client";

import React, { useEffect, useState } from 'react';
import { BentoCard } from '@/components/widgets/BentoCard';
import { AIRiskWidget } from '@/components/widgets/AIRiskWidget';
import { TransformerListWidget } from '@/components/widgets/TransformerListWidget';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { Activity, Zap, ShieldAlert, Cpu, Database, BarChart3, ArrowRight, Server } from 'lucide-react';

// Dynamically import Leaflet Map to avoid SSR issues
const TransformerMap = dynamic(() => import('@/components/map/TransformerMap'), { ssr: false });

interface Transformer {
  id: string;
  name: string;
  transformer_code: string;
  rated_kva: number;
  location_name: string;
  operational_status: string;
  location: string;
  substation_id?: string;
  address_text?: string;
  district?: string;
}

interface RiskScore {
  transformer_id: string;
  anomaly_score: number;
  risk_category: string;
  expected_lifetime_days: number;
}

interface Substation {
  id: string;
  name: string;
  code: string;
}

interface CombinedData extends Transformer, Partial<RiskScore> {
  substation_name?: string;
}

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<CombinedData[]>([]);
  const [aiRunStatus, setAiRunStatus] = useState<string>("Loading...");
  const [scanning, setScanning] = useState(false);

  // Filter States
  const [search, setSearch] = useState("");
  const [selectedSubstation, setSelectedSubstation] = useState("all");
  const [selectedRisk, setSelectedRisk] = useState("all");
  const [selectedCapacity, setSelectedCapacity] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [substationsList, setSubstationsList] = useState<string[]>([]);

  async function loadDashboardData() {
    try {
      // 1. Check AI Run status
      const runRes = await fetch("http://localhost:8000/api/v1/ai-runs/latest");
      if (runRes.ok) {
        const runData = await runRes.json();
        setAiRunStatus(`Last updated: ${new Date(runData.started_at).toLocaleTimeString()}`);
      } else {
        setAiRunStatus("No scans run yet");
      }

      // Fetch Substations
      const subRes = await fetch("http://localhost:8000/api/v1/substations/", { cache: 'no-store' });
      const substations: Substation[] = subRes.ok ? await subRes.json() : [];
      const subMap = new Map(substations.map(s => [s.id, s.name]));

      // 2. Fetch all transformers
      const trRes = await fetch("http://localhost:8000/api/v1/transformers/", { cache: 'no-store' });
      const transformers: Transformer[] = await trRes.json();

      // 3. Fetch scores for each transformer (in parallel)
      const combined: CombinedData[] = await Promise.all(
        transformers.map(async (t) => {
          const substation_name = t.substation_id ? subMap.get(t.substation_id) : "Unknown Substation";
          try {
            const scoreRes = await fetch(`http://localhost:8000/api/v1/transformers/${t.id}/risk-score`, { cache: 'no-store' });
            if (scoreRes.ok) {
              const scoreData: RiskScore = await scoreRes.json();
              return { ...t, ...scoreData, id: t.id, substation_name };
            }
          } catch (e) {
            console.error(`Failed to fetch score for ${t.id}`);
          }
          // Fallback if no score
          return { ...t, anomaly_score: 0, risk_category: "UNKNOWN", expected_lifetime_days: 0, substation_name };
        })
      );
      
      setData(combined);
      
      const uniqueSubs = Array.from(new Set(combined.map(c => c.substation_name).filter(Boolean))) as string[];
      setSubstationsList(uniqueSubs);
    } catch (err) {
      console.error("Dashboard data load failed", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboardData();
  }, []);

  const triggerAIScan = async () => {
    setScanning(true);
    try {
      await fetch("http://localhost:8000/api/v1/ai-runs/trigger", { method: 'POST' });
      // Wait for background tasks to process
      setTimeout(async () => {
        await loadDashboardData();
        setScanning(false);
      }, 3000);
    } catch (e) {
      console.error("Scan trigger failed", e);
      setScanning(false);
    }
  };

  // Compute filteredData reactively
  const filteredData = data.filter((item) => {
    const codeMatch = item.transformer_code?.toLowerCase().includes(search.toLowerCase());
    const nameMatch = item.name?.toLowerCase().includes(search.toLowerCase());
    const matchesSearch = !search || codeMatch || nameMatch;

    const matchesSubstation = selectedSubstation === "all" || item.substation_name === selectedSubstation;
    const matchesRisk = selectedRisk === "all" || item.risk_category === selectedRisk;

    let matchesCapacity = true;
    if (selectedCapacity !== "all") {
      if (selectedCapacity === "under_100") {
        matchesCapacity = item.rated_kva < 100;
      } else if (selectedCapacity === "100_250") {
        matchesCapacity = item.rated_kva >= 100 && item.rated_kva <= 250;
      } else if (selectedCapacity === "over_250") {
        matchesCapacity = item.rated_kva > 250;
      }
    }

    const matchesStatus = selectedStatus === "all" || item.operational_status === selectedStatus;

    return matchesSearch && matchesSubstation && matchesRisk && matchesCapacity && matchesStatus;
  });

  // Compute stats based on filteredData
  const healthyCount = filteredData.filter(d => d.risk_category === "LOW").length;
  const mediumCount = filteredData.filter(d => d.risk_category === "MEDIUM").length;
  const highCount = filteredData.filter(d => d.risk_category === "HIGH").length;
  const criticalCount = filteredData.filter(d => d.risk_category === "CRITICAL").length;
  
  const riskChartData = [
    { category: 'Healthy', count: healthyCount, color: '#10B981' },
    { category: 'Medium', count: mediumCount, color: '#3B82F6' },
    { category: 'High', count: highCount, color: '#F59E0B' },
    { category: 'Critical', count: criticalCount, color: '#EF4444' }
  ];

  if (loading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto px-4 pb-12">
      {/* Header Section */}
      <div className="flex justify-between items-center border-b border-slate-100 pb-5">
        <div>
          <h1 className="text-3xl font-heading font-extrabold text-slate-900 tracking-tight">System Intelligence</h1>
          <p className="text-slate-500 mt-1 flex items-center gap-2 text-sm font-medium">
            <Cpu size={16} className="text-primary animate-pulse"/>
            Predictive Health Monitoring Dashboard
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs font-semibold bg-slate-100 text-slate-600 px-3 py-1.5 rounded-full">{aiRunStatus}</span>
          <button 
            onClick={triggerAIScan}
            disabled={scanning}
            className={`
              bg-primary hover:bg-blue-600 text-white px-5 py-2.5 rounded-xl font-medium transition-all shadow-sm shadow-blue-500/20 flex items-center gap-2
              ${scanning ? 'opacity-50 cursor-wait' : 'cursor-pointer'}
            `}
          >
            <Zap size={18} className={scanning ? 'animate-bounce' : ''} />
            {scanning ? 'Running AI Scan...' : 'Force AI Scan'}
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Search Input */}
        <div>
          <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Search Asset</label>
          <input 
            type="text"
            placeholder="e.g. TRF_GHY_001..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-50 border border-slate-100 hover:border-slate-200 rounded-xl px-3.5 py-2 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:border-primary focus:bg-white transition-all"
          />
        </div>

        {/* Substation Dropdown */}
        <div>
          <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Substation</label>
          <select
            value={selectedSubstation}
            onChange={(e) => setSelectedSubstation(e.target.value)}
            className="w-full bg-slate-50 border border-slate-100 hover:border-slate-200 rounded-xl px-3.5 py-2 text-sm text-slate-700 focus:outline-none focus:border-primary focus:bg-white transition-all"
          >
            <option value="all">All Substations</option>
            {substationsList.map((sub, i) => (
              <option key={i} value={sub}>{sub}</option>
            ))}
          </select>
        </div>

        {/* Risk Level Dropdown */}
        <div>
          <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Risk Level</label>
          <select
            value={selectedRisk}
            onChange={(e) => setSelectedRisk(e.target.value)}
            className="w-full bg-slate-50 border border-slate-100 hover:border-slate-200 rounded-xl px-3.5 py-2 text-sm text-slate-700 focus:outline-none focus:border-primary focus:bg-white transition-all"
          >
            <option value="all">All Risk Levels</option>
            <option value="LOW">LOW / HEALTHY</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="HIGH">HIGH</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="UNKNOWN">UNKNOWN</option>
          </select>
        </div>

        {/* Capacity Dropdown */}
        <div>
          <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Capacity</label>
          <select
            value={selectedCapacity}
            onChange={(e) => setSelectedCapacity(e.target.value)}
            className="w-full bg-slate-50 border border-slate-100 hover:border-slate-200 rounded-xl px-3.5 py-2 text-sm text-slate-700 focus:outline-none focus:border-primary focus:bg-white transition-all"
          >
            <option value="all">All Capacities</option>
            <option value="under_100">&lt; 100 kVA</option>
            <option value="100_250">100 - 250 kVA</option>
            <option value="over_250">&gt; 250 kVA</option>
          </select>
        </div>

        {/* Status Dropdown */}
        <div>
          <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Operational Status</label>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="w-full bg-slate-50 border border-slate-100 hover:border-slate-200 rounded-xl px-3.5 py-2 text-sm text-slate-700 focus:outline-none focus:border-primary focus:bg-white transition-all"
          >
            <option value="all">All Statuses</option>
            <option value="IN_SERVICE">IN_SERVICE</option>
            <option value="OUT_OF_SERVICE">OUT_OF_SERVICE</option>
          </select>
        </div>
      </div>

      {/* Bento Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 auto-rows-[160px]">
        
        {/* KPI: Network Health (Span 1) */}
        <BentoCard className="flex flex-col justify-between p-6">
          <div className="flex justify-between items-start">
            <span className="font-heading font-bold text-xs uppercase tracking-wider text-slate-400">Network Health</span>
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl"><Activity size={20} /></div>
          </div>
          <div>
            <div className="text-4xl font-extrabold text-slate-900">
              {filteredData.length > 0 ? Math.round((healthyCount / filteredData.length) * 100) : 0}%
            </div>
            <p className="text-xs text-emerald-600 font-semibold mt-1 flex items-center gap-1">
              <span>●</span> Optimal State
            </p>
          </div>
        </BentoCard>

        {/* KPI: Active Alerts (Span 1) */}
        <BentoCard className="flex flex-col justify-between p-6">
          <div className="flex justify-between items-start">
            <span className="font-heading font-bold text-xs uppercase tracking-wider text-slate-400">Active Alerts</span>
            <div className="p-2 bg-red-50 text-red-600 rounded-xl"><ShieldAlert size={20} /></div>
          </div>
          <div>
            <div className="text-4xl font-extrabold text-slate-900">{highCount + criticalCount}</div>
            <p className="text-xs text-red-600 font-semibold mt-1 flex items-center gap-1">
              <span>●</span> Requires attention
            </p>
          </div>
        </BentoCard>

        {/* KPI: Total Assets (Span 1) */}
        <BentoCard className="flex flex-col justify-between p-6">
          <div className="flex justify-between items-start">
            <span className="font-heading font-bold text-xs uppercase tracking-wider text-slate-400">Total Transformers</span>
            <div className="p-2 bg-blue-50 text-blue-600 rounded-xl"><Database size={20} /></div>
          </div>
          <div>
            <div className="text-4xl font-extrabold text-slate-900">{filteredData.length}</div>
            <p className="text-xs text-slate-500 font-semibold mt-1">Guwahati Region</p>
          </div>
        </BentoCard>

        {/* KPI: Model Info (Span 1) */}
        <BentoCard className="flex flex-col justify-between p-6">
          <div className="flex justify-between items-start">
            <span className="font-heading font-bold text-xs uppercase tracking-wider text-slate-400">AI Model Version</span>
            <div className="p-2 bg-purple-50 text-purple-600 rounded-xl"><Server size={20} /></div>
          </div>
          <div>
            <div className="text-2xl font-extrabold text-slate-900">v2.1.0-beta</div>
            <p className="text-xs text-purple-600 font-semibold mt-1">Isolation Forest + SHAP</p>
          </div>
        </BentoCard>

        {/* Map Widget (Span 3 columns, span 2 rows) */}
        <BentoCard className="md:col-span-2 lg:col-span-3 row-span-2 p-0 overflow-hidden relative border border-slate-100 rounded-2xl shadow-sm h-full min-h-[320px]">
          <div className="absolute inset-0 bg-slate-100 flex items-center justify-center z-0">
            <TransformerMap transformers={filteredData} onMarkerClick={() => {}} />
          </div>
        </BentoCard>

        {/* AI Risk Distribution (Span 1 column, span 2 rows) */}
        <BentoCard className="row-span-2 p-5" title="AI Risk Distribution">
          <div className="mt-4 flex-1 h-[240px]">
            <AIRiskWidget data={riskChartData} />
          </div>
        </BentoCard>

        {/* Asset Health Directory (Span 3 columns, span 2 rows) */}
        <BentoCard className="md:col-span-2 lg:col-span-3 row-span-2 p-6" title="Asset Directory & Risk Matrix">
          <div className="overflow-x-auto mt-4 h-[240px]">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 text-xs font-bold uppercase tracking-wider">
                  <th className="pb-3">Asset Code</th>
                  <th className="pb-3">Capacity</th>
                  <th className="pb-3">Risk Tier</th>
                  <th className="pb-3">Anomaly Score</th>
                  <th className="pb-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {filteredData.slice(0, 10).map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 font-semibold text-slate-800">{tx.transformer_code}</td>
                    <td className="py-3 text-slate-500">{tx.rated_kva} kVA</td>
                    <td className="py-3">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        tx.risk_category === 'CRITICAL' ? 'bg-red-50 text-red-700' : 
                        tx.risk_category === 'HIGH' ? 'bg-amber-50 text-amber-700' : 
                        tx.risk_category === 'MEDIUM' ? 'bg-blue-50 text-blue-700' :
                        'bg-emerald-50 text-emerald-700'
                      }`}>
                        {tx.risk_category}
                      </span>
                    </td>
                    <td className="py-3 font-bold text-slate-700">{tx.anomaly_score?.toFixed(1) || '0.0'}%</td>
                    <td className="py-3 text-right">
                      <Link href={`/dashboard/transformers/${tx.id}`} className="text-primary hover:text-blue-700 font-medium text-xs flex items-center gap-1 ml-auto w-fit">
                        Details <ArrowRight size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </BentoCard>

        {/* Critical Attention List (Span 1 column, span 2 rows) */}
        <BentoCard className="row-span-2 p-5" title="Critical Attention">
          <div className="mt-4 flex-1 h-[240px]">
            <TransformerListWidget transformers={filteredData as any} />
          </div>
        </BentoCard>

      </div>
    </div>
  );
}
