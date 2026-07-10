"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import AddTransformerModal from "@/components/forms/AddTransformerModal";
import {
  Plus, Search, LayoutDashboard, Zap, ChevronUp, ChevronDown,
  RefreshCw, AlertTriangle, CheckCircle, Clock, ArrowRight, Filter
} from "lucide-react";

interface Transformer {
  id: string;
  transformer_code: string;
  name?: string;
  rated_kva: number;
  operational_status: string;
  district?: string;
  address_text?: string;
  substation_id?: string;
}

interface RiskScore {
  transformer_id: string;
  anomaly_score: number;
  risk_category: string;
  expected_lifetime_days: number;
}

interface AssetRow extends Transformer, Partial<RiskScore> {
  substation_name?: string;
}

type SortKey = "transformer_code" | "rated_kva" | "anomaly_score" | "risk_category" | "operational_status";

const RISK_ORDER: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1, HEALTHY: 1, UNKNOWN: 0 };

const riskBadge = (r?: string) => {
  const map: Record<string, string> = {
    CRITICAL: "bg-red-100 text-red-700 border border-red-200",
    HIGH:     "bg-amber-100 text-amber-700 border border-amber-200",
    MEDIUM:   "bg-blue-100 text-blue-700 border border-blue-200",
    LOW:      "bg-emerald-100 text-emerald-700 border border-emerald-200",
    HEALTHY:  "bg-emerald-100 text-emerald-700 border border-emerald-200",
    UNKNOWN:  "bg-slate-100 text-slate-500 border border-slate-200",
  };
  return `text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded-full ${map[r ?? "UNKNOWN"] ?? map.UNKNOWN}`;
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
  const [sortDir, setSortDir]       = useState<"asc" | "desc">("desc");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      let subMap = new Map<string, string>();
      try {
        const sr = await apiClient.get("/substations/");
        subMap = new Map(sr.data.map((s: any) => [s.id, s.name]));
      } catch {}

      const tr = await apiClient.get("/transformers/");
      const transformers: Transformer[] = tr.data;

      const rows: AssetRow[] = await Promise.all(
        transformers.map(async (t) => {
          const substation_name = t.substation_id ? subMap.get(t.substation_id) : undefined;
          try {
            const sr = await apiClient.get(`/transformers/${t.id}/risk-score`);
            return { ...t, ...sr.data, id: t.id, substation_name };
          } catch {}
          return { ...t, anomaly_score: 0, risk_category: "UNKNOWN", expected_lifetime_days: 0, substation_name };
        })
      );
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

  // Derived filtered + sorted list
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

  // Stats
  const critical = assets.filter(a => a.risk_category === "CRITICAL").length;
  const high     = assets.filter(a => a.risk_category === "HIGH").length;
  const healthy  = assets.filter(a => a.risk_category === "LOW" || a.risk_category === "HEALTHY").length;

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k
      ? sortDir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} />
      : <ChevronDown size={12} className="opacity-20" />;

  return (
    <div className="min-h-screen bg-slate-50">
      <AddTransformerModal open={showModal} onClose={() => setShowModal(false)} onSuccess={load} />

      {/* Page header */}
      <div className="bg-white border-b border-slate-100 px-8 py-6">
        <div className="max-w-7xl mx-auto">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-4">
            <Link href="/dashboard" className="hover:text-slate-700 transition-colors flex items-center gap-1">
              <LayoutDashboard size={12} /> Dashboard
            </Link>
            <span>/</span>
            <span className="text-slate-600 font-semibold">Assets Directory</span>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-extrabold text-slate-900 flex items-center gap-3">
                <Zap className="text-blue-600" size={24} />
                Assets Directory
              </h1>
              <p className="text-slate-500 text-sm mt-1">
                {loading ? "Loading…" : `${assets.length} transformer assets in Guwahati region`}
              </p>
            </div>
            <div className="flex items-center gap-3">
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

          {/* Stat pills */}
          <div className="flex items-center gap-4 mt-5 flex-wrap">
            {[
              { label: "Critical", value: critical, color: "text-red-700 bg-red-50 border-red-200", icon: "🔴" },
              { label: "High Risk", value: high,     color: "text-amber-700 bg-amber-50 border-amber-200", icon: "🟡" },
              { label: "Healthy",  value: healthy,   color: "text-emerald-700 bg-emerald-50 border-emerald-200", icon: "🟢" },
              { label: "Total",    value: assets.length, color: "text-blue-700 bg-blue-50 border-blue-200", icon: "📊" },
            ].map(s => (
              <div key={s.label} className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-bold ${s.color}`}>
                <span>{s.icon}</span>
                <span>{s.label}: {s.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-8 py-6">
        {/* Filter Bar */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm px-5 py-4 flex items-center gap-4 flex-wrap mb-6">
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
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low / Healthy</option>
              <option value="UNKNOWN">Unknown</option>
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

        {/* Table */}
        {loading ? (
          <div className="bg-white rounded-2xl border border-slate-100 flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin h-10 w-10 rounded-full border-b-2 border-blue-600 mx-auto mb-3" />
              <p className="text-slate-500 text-sm">Loading assets…</p>
            </div>
          </div>
        ) : displayed.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-100 flex items-center justify-center h-48">
            <div className="text-center text-slate-400">
              <AlertTriangle size={36} className="mx-auto mb-2 opacity-50" />
              <p className="font-semibold">No assets match your filters.</p>
              <button className="mt-2 text-blue-600 text-sm hover:underline" onClick={() => { setSearch(""); setRiskFilter("ALL"); setStatusFilter("ALL"); }}>
                Clear filters
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/80">
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
                      className="px-5 py-3.5 text-[10px] font-extrabold uppercase tracking-widest text-slate-400 cursor-pointer hover:text-slate-700 transition-colors select-none"
                    >
                      <span className="flex items-center gap-1">{col.label} <SortIcon k={col.key} /></span>
                    </th>
                  ))}
                  <th className="px-5 py-3.5 text-[10px] font-extrabold uppercase tracking-widest text-slate-400 text-right">Location</th>
                  <th className="px-5 py-3.5 text-[10px] font-extrabold uppercase tracking-widest text-slate-400 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {displayed.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="px-5 py-4">
                      <span className="font-bold text-slate-800 text-sm">{a.transformer_code}</span>
                      {a.substation_name && <p className="text-[10px] text-slate-400 mt-0.5">{a.substation_name}</p>}
                    </td>
                    <td className="px-5 py-4 text-sm text-slate-600 font-medium">{a.rated_kva} kVA</td>
                    <td className="px-5 py-4">
                      <span className={riskBadge(a.risk_category)}>{a.risk_category ?? "UNKNOWN"}</span>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.min(a.anomaly_score ?? 0, 100)}%`,
                              background: a.risk_category === "CRITICAL" ? "#ef4444" : a.risk_category === "HIGH" ? "#f59e0b" : "#10b981"
                            }}
                          />
                        </div>
                        <span className="text-sm font-bold text-slate-700">{(a.anomaly_score ?? 0).toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <span className={`flex items-center gap-1.5 text-xs font-semibold ${a.operational_status === "IN_SERVICE" ? "text-emerald-700" : "text-slate-400"}`}>
                        {a.operational_status === "IN_SERVICE" ? <CheckCircle size={12} /> : <Clock size={12} />}
                        {a.operational_status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-sm text-slate-500">
                      <span className="truncate max-w-[160px] block">{a.district || a.address_text || "—"}</span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        href={`/dashboard/transformers/${a.id}`}
                        className="inline-flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-800 transition-colors opacity-0 group-hover:opacity-100"
                      >
                        Details <ArrowRight size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-5 py-3 border-t border-slate-50 bg-slate-50/50 text-xs text-slate-400 font-medium">
              {displayed.length} assets shown · Click column headers to sort
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
