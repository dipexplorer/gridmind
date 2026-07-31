"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";
import AddTransformerModal from "@/components/forms/AddTransformerModal";
import {
  Plus, Search, LayoutDashboard, Zap, ChevronUp, ChevronDown,
  RefreshCw, AlertTriangle, CheckCircle, Clock, ArrowRight, Filter, Download
} from "lucide-react";

interface AssetRow {
  id: string;
  transformer_code: string;
  rated_kva: number;
  operational_status: string;
  district?: string;
  address_text?: string;
  substation_id?: string;
  substation_name?: string;
  risk_category?: string;
  anomaly_score?: number;
  expected_lifetime_days?: number;
}

type SortKey = "transformer_code" | "rated_kva" | "anomaly_score" | "risk_category" | "operational_status";

const RISK_ORDER: Record<string, number> = { CRITICAL: 3, WARNING: 2, HEALTHY: 1, UNKNOWN: 0 };

const riskBadge = (r?: string) => {
  const map: Record<string, string> = {
    CRITICAL: "bg-red-50 text-red-700 border border-red-200",
    WARNING:  "bg-amber-50 text-amber-700 border border-amber-200",
    HEALTHY:  "bg-emerald-50 text-emerald-700 border border-emerald-200",
    UNKNOWN:  "bg-slate-50 text-slate-500 border border-slate-200",
  };
  return `text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full border ${map[r ?? "UNKNOWN"] ?? map.UNKNOWN}`;
};

export default function AssetsPage() {
  const [assets, setAssets]     = useState<AssetRow[]>([]);
  const [loading, setLoading]   = useState(true);
  const [showModal, setShowModal] = useState(false);

  // Filters & sort
  const [search, setSearch]         = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [sortKey, setSortKey]       = useState<SortKey>("risk_category");
  const [sortDir, setSortDir]       = useState<"desc" | "asc">("desc");
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // 1. Fetch substations for name lookup
      const { data: substationsData } = await supabase
        .from('substations')
        .select('id, name');
      const subMap = new Map((substationsData || []).map((s: any) => [s.id, s.name]));

      // 2. Fetch all transformers from the flat view directly
      let allTransformers: any[] = [];
      let pageNum = 0;
      const pageSize = 1000;
      let hasMore = true;

      while (hasMore) {
        const { data: chunk, error: trError } = await supabase
          .from('transformers_flat')
          .select('id, transformer_code, rated_kva, operational_status, district, address_text, substation_id, current_status, current_failure_risk, current_health_score')
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

      const rows: AssetRow[] = allTransformers.map((t: any) => {
        const substation_name = t.substation_id ? subMap.get(t.substation_id) : "Unknown Substation";
        const risk_category = t.current_status ? t.current_status.toUpperCase() : "UNKNOWN";
        const anomaly_score = (t.current_failure_risk || 0) * 100;
        return {
          id: t.id,
          transformer_code: t.transformer_code,
          rated_kva: t.rated_kva,
          operational_status: t.operational_status,
          district: t.district,
          address_text: t.address_text,
          substation_id: t.substation_id,
          substation_name,
          risk_category,
          anomaly_score,
          expected_lifetime_days: t.current_health_score ? Math.round(t.current_health_score * 3.65) : 0
        };
      });

      setAssets(rows);
    } catch (err) {
      console.error("Assets load failed", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Sort handler
  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  // Reset page when filters or sort change
  useEffect(() => {
    setCurrentPage(1);
  }, [search, riskFilter, statusFilter, sortKey, sortDir]);

  // Filtered and sorted assets
  const displayed = assets
    .filter(a => {
      const s = search.toLowerCase();
      const matchSearch = !s || a.transformer_code.toLowerCase().includes(s) || (a.district ?? "").toLowerCase().includes(s) || (a.address_text ?? "").toLowerCase().includes(s);
      const matchRisk   = riskFilter === "ALL" || a.risk_category === riskFilter;
      const matchStatus = statusFilter === "ALL" || a.operational_status === statusFilter;
      return matchSearch && matchRisk && matchStatus;
    })
    .sort((a, b) => {
      let diff = 0;
      if (sortKey === "transformer_code") diff = a.transformer_code.localeCompare(b.transformer_code);
      else if (sortKey === "rated_kva")   diff = (a.rated_kva ?? 0) - (b.rated_kva ?? 0);
      else if (sortKey === "anomaly_score") diff = (a.anomaly_score ?? 0) - (b.anomaly_score ?? 0);
      else if (sortKey === "risk_category") diff = (RISK_ORDER[a.risk_category ?? ""] ?? 0) - (RISK_ORDER[b.risk_category ?? ""] ?? 0);
      else if (sortKey === "operational_status") diff = a.operational_status.localeCompare(b.operational_status);
      return sortDir === "asc" ? diff : -diff;
    });

  const totalPages = Math.ceil(displayed.length / itemsPerPage);
  const paginatedData = displayed.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  // Status counters
  const critical = assets.filter(a => a.risk_category === "CRITICAL").length;
  const warning  = assets.filter(a => a.risk_category === "WARNING").length;
  const healthy  = assets.filter(a => a.risk_category === "HEALTHY").length;
  const unknown  = assets.filter(a => a.risk_category === "UNKNOWN" || !a.risk_category).length;

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k
      ? sortDir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} />
      : <ChevronDown size={12} className="opacity-20" />;

  const exportToCSV = () => {
    if (displayed.length === 0) return;
    
    const headers = [
      "Asset Code",
      "Substation",
      "Capacity (kVA)",
      "Status",
      "Risk Tier",
      "AI Anomaly Score",
      "Expected Lifetime (Days)",
      "Location"
    ];
    
    const rows = displayed.map(a => [
      a.transformer_code,
      a.substation_name || "—",
      a.rated_kva,
      a.operational_status,
      a.risk_category || "UNKNOWN",
      (a.anomaly_score ?? 0).toFixed(1) + "%",
      a.expected_lifetime_days || "—",
      `"${(a.district || a.address_text || "—").replace(/"/g, '""')}"`
    ]);
    
    const csvContent = [
      headers.join(","),
      ...rows.map(r => r.join(","))
    ].join("\n");
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `gridmind_assets_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <AddTransformerModal open={showModal} onClose={() => setShowModal(false)} onSuccess={load} />

      {/* Header section */}
      <div className="bg-white border-b border-slate-200/50 px-8 py-6 mb-6">
        <div className="max-w-[1600px] mx-auto flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
              <Zap className="text-blue-600" size={24} />
              Assets Directory
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              {loading ? "Loading assets..." : `${assets.length} transformer assets in APDCL region`}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={exportToCSV} disabled={displayed.length === 0} className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-100 border border-slate-200 transition-colors disabled:opacity-50">
              <Download size={15} /> Export CSV
            </button>
            <button onClick={load} className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-100 border border-slate-200 transition-colors">
              <RefreshCw size={15} className={loading ? "animate-spin" : ""} /> Refresh
            </button>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/20 transition-all"
            >
              <Plus size={16} /> Add Transformer
            </button>
          </div>
        </div>

        {/* Dynamic status pill filters */}
        <div className="max-w-[1600px] mx-auto flex items-center gap-3 mt-5 flex-wrap">
          {[
            { label: "Critical", value: critical, color: "text-red-700 bg-red-50 border-red-200",      icon: "🔴" },
            { label: "Warning",  value: warning,  color: "text-amber-700 bg-amber-50 border-amber-200", icon: "🟡" },
            { label: "Healthy",  value: healthy,  color: "text-emerald-700 bg-emerald-50 border-emerald-200", icon: "🟢" },
            { label: "Unknown",  value: unknown,  color: "text-slate-600 bg-slate-100 border-slate-200", icon: "⚪" },
            { label: "Total",    value: assets.length, color: "text-slate-800 bg-white border-slate-300 shadow-sm", icon: "📊" },
          ].filter(s => s.value > 0).map(s => (
            <div key={s.label} className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-bold ${s.color}`}>
              <span>{s.icon}</span>
              <span>{s.label}: {s.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Table & Filtering */}
      <div className="max-w-[1600px] mx-auto px-4 md:px-8">
        <div className="bg-white rounded-2xl border border-slate-200/50 shadow-sm px-5 py-4 flex items-center gap-4 flex-wrap mb-6">
          <div className="flex items-center gap-2 text-slate-400 flex-1 min-w-[200px] bg-slate-50 border border-slate-100 rounded-xl px-3 py-2 focus-within:border-blue-400 transition-all">
            <Search size={15} className="flex-shrink-0" />
            <input
              className="bg-transparent flex-1 text-sm text-slate-700 placeholder-slate-400 focus:outline-none"
              placeholder="Search by code, district, address…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Filter size={14} className="text-slate-400" />
            <select
              className="text-sm bg-slate-50 border border-slate-100 rounded-xl px-3 py-2 text-slate-700 focus:outline-none focus:border-blue-400 transition-all"
              value={riskFilter}
              onChange={e => setRiskFilter(e.target.value)}
            >
              <option value="ALL">All Risk Levels</option>
              <option value="CRITICAL">🔴 CRITICAL</option>
              <option value="WARNING">🟡 WARNING</option>
              <option value="HEALTHY">🟢 HEALTHY</option>
              <option value="UNKNOWN">⚪ UNKNOWN</option>
            </select>
            <select
              className="text-sm bg-slate-50 border border-slate-100 rounded-xl px-3 py-2 text-slate-700 focus:outline-none focus:border-blue-400 transition-all"
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="IN_SERVICE">In Service</option>
              <option value="OUT_OF_SERVICE">Out of Service</option>
            </select>
          </div>
          {displayed.length !== assets.length && (
            <span className="text-xs text-slate-500 font-medium">Showing {displayed.length} of {assets.length}</span>
          )}
        </div>

        {loading ? (
          <div className="bg-white rounded-2xl border border-slate-200/50 flex items-center justify-center h-64 shadow-sm">
            <div className="text-center">
              <div className="animate-spin h-8 w-8 rounded-full border-b-2 border-blue-600 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">Loading assets directory...</p>
            </div>
          </div>
        ) : displayed.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200/50 flex items-center justify-center h-48 shadow-sm">
            <div className="text-center text-slate-400">
              <AlertTriangle size={36} className="mx-auto mb-2 opacity-50 text-amber-500" />
              <p className="font-semibold">No assets match your search filters.</p>
              <button className="mt-2 text-blue-600 text-sm hover:underline" onClick={() => { setSearch(""); setRiskFilter("ALL"); setStatusFilter("ALL"); }}>
                Clear filters
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200/50 shadow-sm overflow-hidden mb-10">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-150 bg-slate-50/80">
                    {([
                      { key: "transformer_code", label: "Asset Code" },
                      { key: "rated_kva",         label: "Capacity" },
                      { key: "risk_category",     label: "Risk Tier" },
                      { key: "anomaly_score",     label: "AI Score" },
                      { key: "operational_status", label: "Status" },
                    ] as { key: SortKey; label: string }[]).map(col => (
                      <th
                        key={col.key}
                        onClick={() => toggleSort(col.key)}
                        className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-450 cursor-pointer hover:text-slate-700 select-none"
                      >
                        <span className="flex items-center gap-1.5">{col.label} <SortIcon k={col.key} /></span>
                      </th>
                    ))}
                    <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-450 text-right">Location</th>
                    <th className="px-6 py-4 text-xs font-bold uppercase tracking-wider text-slate-450 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {paginatedData.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4">
                        <span className="font-bold text-slate-800 text-sm">{a.transformer_code}</span>
                        {a.substation_name && <p className="text-[10px] text-slate-400 mt-0.5">{a.substation_name}</p>}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600 font-medium">{a.rated_kva} kVA</td>
                      <td className="px-6 py-4">
                        <span className={riskBadge(a.risk_category)}>{a.risk_category ?? "UNKNOWN"}</span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{
                                width: `${Math.min(a.anomaly_score ?? 0, 100)}%`,
                                background: a.risk_category === "CRITICAL" ? "#ef4444" : a.risk_category === "WARNING" ? "#f59e0b" : a.risk_category === "UNKNOWN" ? "#94a3b8" : "#10b981"
                              }}
                            />
                          </div>
                          <span className="text-sm font-bold text-slate-750">{(a.anomaly_score ?? 0).toFixed(1)}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`flex items-center gap-1.5 text-xs font-semibold ${a.operational_status === "IN_SERVICE" ? "text-emerald-700" : "text-slate-400"}`}>
                          {a.operational_status === "IN_SERVICE" ? <CheckCircle size={12} className="text-emerald-500" /> : <Clock size={12} />}
                          {a.operational_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-500 text-right">
                        <span className="truncate max-w-[200px] inline-block">{a.district || a.address_text || "—"}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href={`/dashboard/transformers/${a.id}`}
                          className="inline-flex items-center gap-1 text-xs font-bold text-blue-600 bg-blue-50 hover:bg-blue-100 border border-transparent hover:border-blue-200 px-3 py-1.5 rounded-lg transition-all"
                        >
                          Details <ArrowRight size={12} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500 font-medium">
              <div>{displayed.length} assets found · Showing {(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, displayed.length)}</div>
              <div className="flex gap-2">
                <button 
                  disabled={currentPage === 1} 
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 disabled:opacity-50 text-slate-600 transition-colors"
                >Prev</button>
                <span className="px-2 py-1.5 flex items-center text-slate-500">Page {currentPage} of {totalPages || 1}</span>
                <button 
                  disabled={currentPage >= totalPages || totalPages === 0} 
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 disabled:opacity-50 text-slate-600 transition-colors"
                >Next</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
