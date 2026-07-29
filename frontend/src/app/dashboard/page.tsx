"use client";

import React, { useEffect, useState } from 'react';
import { BentoCard } from '@/components/widgets/BentoCard';
import { AIRiskWidget } from '@/components/widgets/AIRiskWidget';
import { TransformerListWidget } from '@/components/widgets/TransformerListWidget';
import { TicketsWidget, Ticket } from '@/components/widgets/TicketsWidget';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { Activity, Zap, ShieldAlert, Cpu, Database, BarChart3, ArrowRight, Server, Download } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';

// Dynamically import Leaflet Map to avoid SSR issues
const TransformerMap = dynamic(() => import('@/components/map/TransformerMap'), { ssr: false });

interface Transformer {
  id: string;
  name: string;
  transformer_code: string;
  rated_kva: number;
  location_name: string;
  operational_status: string;
  // Raw lat/lon from transformers_flat view
  latitude?: number;
  longitude?: number;
  // location as WKT string (built from lat/lon for map compatibility)
  location: string;
  substation_id?: string;
  address_text?: string;
  district?: string;
  current_status?: string;
  current_failure_risk?: number;
  current_health_score?: number;
  current_load_pct?: number;
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
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<CombinedData[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [lastRefreshed, setLastRefreshed] = useState<string>('Loading...');
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
      // Status shown via lastRefreshed timestamp set at end of load

      // 1. Fetch all transformers from the flat view (lat/lon as plain floats)
      let allTransformers: any[] = [];
      let pageNum = 0;
      const pageSize = 1000;
      let hasMore = true;

      while (hasMore) {
        const { data: chunk, error: trError } = await supabase
          .from('transformers_flat')
          .select('id, transformer_code, rated_kva, age_years, operational_status, district, address_text, substation_id, current_status, current_failure_risk, current_health_score, current_load_pct, current_load_kw, current_oil_temp_c, manufacturer, cooling_type, num_consumers, latitude, longitude')
          .range(pageNum * pageSize, (pageNum + 1) * pageSize - 1);

        if (trError) {
          console.error("Supabase transformers_flat query failed:", trError);
          return;
        }

        if (chunk && chunk.length > 0) {
          allTransformers = [...allTransformers, ...chunk];
          if (chunk.length < pageSize) {
            hasMore = false;
          } else {
            pageNum++;
          }
        } else {
          hasMore = false;
        }
      }

      // 2. Fetch substations for name lookup
      const { data: substationsData } = await supabase
        .from('substations')
        .select('id, name');
      const subMap = new Map((substationsData || []).map((s: any) => [s.id, s.name]));

      // 3. Build combined data with risk category & WKT location string for the map
      const combined: CombinedData[] = (allTransformers || []).map((t: any) => {
        const substation_name = t.substation_id ? subMap.get(t.substation_id) : "Unknown Substation";
        const score = (t.current_failure_risk || 0) * 100;
        let cat = "UNKNOWN";
        if (t.current_failure_risk !== null && t.current_failure_risk !== undefined) {
          if (score >= 90) cat = "CRITICAL";
          else if (score >= 70) cat = "WARNING";
          else cat = "HEALTHY";
        }
        // Build WKT string from flat lat/lon so TransformerMap's parseWKT() works
        const location = (t.latitude && t.longitude)
          ? `POINT(${t.longitude} ${t.latitude})`
          : '';
        return {
          ...t,
          id: t.id,
          location,
          substation_name,
          anomaly_score: score,
          risk_category: cat,
          expected_lifetime_days: cat === "HEALTHY" ? 365 : (cat === "WARNING" ? 90 : 7)
        };
      });

      setData(combined);
      const uniqueSubs = Array.from(new Set(combined.map(c => c.substation_name).filter(Boolean))) as string[];
      setSubstationsList(uniqueSubs);
      setLastRefreshed(`Last synced: ${new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })} IST`);
    } catch (err) {
      console.error("Dashboard data load failed", err);
      setLastRefreshed('Sync failed — retrying...');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadDashboardData();
  }, []);

  const triggerAIScan = async () => {
    setRefreshing(true);
    setScanning(true);
    await loadDashboardData();
    setScanning(false);
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

  // Compute global stats for top KPI cards
  const globalHealthyCount = data.filter(d => d.risk_category === "HEALTHY").length;
  const globalWarningCount = data.filter(d => d.risk_category === "WARNING").length;
  const globalCriticalCount = data.filter(d => d.risk_category === "CRITICAL").length;

  // Compute stats based on filteredData for charts and lists
  const healthyCount = filteredData.filter(d => d.risk_category === "HEALTHY").length;
  const warningCount = filteredData.filter(d => d.risk_category === "WARNING").length;
  const criticalCount = filteredData.filter(d => d.risk_category === "CRITICAL").length;
  const unknownCount = filteredData.filter(d => d.risk_category === "UNKNOWN").length;
  
  const riskChartData = [
    { category: 'Healthy',  count: healthyCount,  color: '#10B981' },
    { category: 'Warning',  count: warningCount,  color: '#F59E0B' },
    { category: 'Critical', count: criticalCount, color: '#EF4444' },
  ];
  if (unknownCount > 0) {
    riskChartData.push({ category: 'Unknown', count: unknownCount, color: '#94A3B8' });
  }

  const exportTicketsToCSV = () => {
    if (tickets.length === 0) return;
    const headers = ["Ticket ID", "Transformer", "Status", "Priority", "Description", "Created At"];
    const rows = tickets.map(t => [
      t.id,
      t.transformer_name || t.transformer_id,
      t.status,
      t.priority,
      `"${t.description.replace(/"/g, '""')}"`,
      new Date(t.created_at).toLocaleString()
    ]);
    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `gridmind_tickets_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

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
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100 px-3 py-1.5 rounded-full flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse inline-block"></span>
            {lastRefreshed}
          </span>
          <button
            onClick={triggerAIScan}
            disabled={refreshing || scanning}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white px-4 py-1.5 rounded-full text-xs font-bold transition-colors"
          >
            <Activity size={13} className={refreshing ? 'animate-spin' : ''} />
            {refreshing ? 'Refreshing...' : 'Refresh Live Data'}
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
            <option value="CRITICAL">🔴 CRITICAL</option>
            <option value="WARNING">🟡 WARNING</option>
            <option value="HEALTHY">🟢 HEALTHY</option>
            <option value="UNKNOWN">⚪ UNKNOWN</option>
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
              {data.length > 0 ? Math.round((globalHealthyCount / data.length) * 100) : 0}%
            </div>
            <p className="text-xs text-emerald-600 font-semibold mt-1 flex items-center gap-1">
              <span>●</span> {globalHealthyCount} Healthy Assets
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
            <div className="text-4xl font-extrabold text-slate-900">{globalWarningCount + globalCriticalCount}</div>
            <p className="text-xs text-red-600 font-semibold mt-1 flex items-center gap-1">
              <span>●</span> {globalCriticalCount} Critical, {globalWarningCount} Warning
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
            <div className="text-4xl font-extrabold text-slate-900">{data.length}</div>
            <p className="text-xs text-slate-500 font-semibold mt-1">Guwahati Region</p>
          </div>
        </BentoCard>

        {/* KPI: System Operations (Span 1) */}
        <BentoCard className="flex flex-col justify-between p-6">
          <div className="flex justify-between items-start mb-2">
            <span className="font-heading font-bold text-xs uppercase tracking-wider text-slate-400">Operations</span>
            <div className="p-2 bg-slate-50 text-slate-600 rounded-xl"><Server size={20} /></div>
          </div>
          <div className="flex flex-col gap-2 mt-auto">
            <button 
              onClick={triggerAIScan}
              disabled={refreshing || scanning}
              className="flex items-center justify-between bg-blue-50 hover:bg-blue-100 disabled:opacity-60 text-blue-700 px-3 py-2 rounded-lg text-xs font-bold transition-colors w-full"
            >
              <span className="flex items-center gap-1.5"><Activity size={14} className={refreshing ? 'animate-spin' : ''} /> {refreshing ? 'Fetching...' : 'Refresh Live Data'}</span>
              <ArrowRight size={14} />
            </button>
            <button 
              onClick={() => {
                const csvContent = "data:text/csv;charset=utf-8,Asset Code,Status,Risk,Load%,District\n" + filteredData.map(d => `${d.transformer_code},${d.operational_status},${d.risk_category},${d.current_load_pct?.toFixed(1) || ''}%,${d.district || ''}`).join("\n");
                const encodedUri = encodeURI(csvContent);
                const link = document.createElement("a");
                link.setAttribute("href", encodedUri);
                link.setAttribute("download", `gridmind_report_${new Date().toISOString().split('T')[0]}.csv`);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
              }}
              className="flex items-center justify-between bg-slate-50 hover:bg-slate-100 text-slate-700 px-3 py-2 rounded-lg text-xs font-bold transition-colors w-full"
            >
              <span className="flex items-center gap-1.5"><Download size={14} /> Export CSV ({filteredData.length})</span>
              <ArrowRight size={14} />
            </button>
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
                  <th className="pb-3 sticky top-0 bg-white z-10">Asset Code</th>
                  <th className="pb-3 sticky top-0 bg-white z-10">Capacity</th>
                  <th className="pb-3 sticky top-0 bg-white z-10">Risk Tier</th>
                  <th className="pb-3 sticky top-0 bg-white z-10">Anomaly Score</th>
                  <th className="pb-3 text-right sticky top-0 bg-white z-10">Action</th>
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
                        tx.risk_category === 'WARNING'  ? 'bg-amber-50 text-amber-700' : 
                        tx.risk_category === 'UNKNOWN'  ? 'bg-slate-100 text-slate-500' :
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

        {/* Tickets Widget (Span 4 columns, span 2 rows) */}
        <BentoCard 
          className="md:col-span-2 lg:col-span-4 row-span-2 p-5" 
          title="Active Maintenance Tickets"
          action={
            <button 
              onClick={exportTicketsToCSV} 
              disabled={tickets.length === 0}
              className="flex items-center gap-1.5 text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              <Download size={14} /> Export CSV
            </button>
          }
        >
          <div className="mt-4 flex-1 h-[240px]">
            <TicketsWidget tickets={tickets} onTicketResolved={loadDashboardData} />
          </div>
        </BentoCard>

      </div>
    </div>
  );
}
