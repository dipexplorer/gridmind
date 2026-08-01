"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  Activity, ShieldAlert, Cpu, Calendar, Settings, MapPin, Wrench,
  BarChart3, Clock, ArrowLeft, Factory, Zap, Thermometer, Gauge,
  TrendingUp, TrendingDown, CheckCircle, AlertTriangle, Info,
  LayoutDashboard, ChevronRight, Brain, FlaskConical, Battery,
  WifiOff, Wifi, CircleAlert, Layers, BrainCircuit
} from "lucide-react";
import Link from "next/link";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, BarChart, Bar, Cell, ReferenceLine, Area, AreaChart
} from "recharts";
import { apiClient } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────
interface DetailData {
  id: string; transformer_code: string; rated_kva: number;
  voltage_hv_kv: number; voltage_lv_v: number; installation_type: string;
  cooling_type: string; manufacturer: string; address_text: string;
  district: string; is_flood_prone: boolean; is_high_lightning: boolean;
  installation_date: string; operational_status: string; location: string;
  feeder_name: string; substation_name: string; num_consumers?: number;
}
interface TSPoint { time: string; load_percentage: number; voltage_lv: number; current_a: number; temperature_c: number; }
interface MLog { id: string; maintenance_date: string; maintenance_type: string; work_description?: string; findings?: string; oil_bdv_kv?: number; outcome: string; }
interface ShapRow { feature_name: string; feature_value: number; shap_value: number; }
interface Risk {
  anomaly_score: number;
  health_score?: number;
  risk_category: string;
  expected_lifetime_days: number;
  model_predictions?: any;
  shap_values?: ShapRow[];
  xgb_shap_values?: ShapRow[];
}
interface WeatherImpact { ambient_temperature_c: number; weather_penalty_percentage: number; is_hot_day: boolean; }

const RISK_META: Record<string, { color: string; bg: string; border: string; glow: string; label: string }> = {
  CRITICAL: { color: "text-red-700",     bg: "bg-red-500",     border: "border-red-200",    glow: "shadow-red-500/30",    label: "CRITICAL" },
  WARNING:  { color: "text-amber-700",   bg: "bg-amber-400",   border: "border-amber-200",  glow: "shadow-amber-500/30",  label: "WARNING" },
  HEALTHY:  { color: "text-emerald-700", bg: "bg-emerald-500", border: "border-emerald-200",glow: "shadow-emerald-500/30",label: "HEALTHY" },
  UNKNOWN:  { color: "text-slate-500",   bg: "bg-slate-400",   border: "border-slate-200",  glow: "shadow-slate-200",     label: "UNKNOWN" },
};

const featureLabel: Record<string, string> = {
  temp_c: "Oil Temperature",
  load_pct: "Load Factor",
  v_lv: "LV Secondary Voltage",
  curr_a: "Load Current",
  ambient_temp: "Ambient Outdoor Temp",
  age_years: "Asset Operational Age",
  rated_kva: "Rated Capacity (kVA)",
  power_factor: "Power Factor (PF)",
  load_ratio: "Load to Capacity Ratio",
  current_ratio: "Current Load Ratio",
  voltage_deviation: "Voltage Deviation",
  temperature_rise: "Thermal Winding Rise",
  stress_index: "Combined Thermal Stress"
};

// ── Custom Tooltip ─────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white/95 backdrop-blur-sm border border-slate-200 rounded-2xl p-3 shadow-xl text-xs font-medium">
      <p className="text-slate-500 font-bold mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color }} />
          <span className="text-slate-600">{p.name}:</span>
          <span className="font-extrabold text-slate-900">{typeof p.value === "number" ? p.value.toFixed(1) : p.value}</span>
        </div>
      ))}
    </div>
  );
};

// ── Stat Chip ─────────────────────────────────────────────────────────────────
const StatBadge = ({ icon: Icon, label, value, sub, iconBg, trend }: {
  icon: any; label: string; value: string; sub?: string; iconBg: string; trend?: "up" | "down" | "neutral";
}) => (
  <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-5 flex items-center gap-4 hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 group">
    <div className={`p-3.5 rounded-2xl ${iconBg} flex-shrink-0 group-hover:scale-110 transition-transform duration-300`}>
      <Icon size={22} className="opacity-90" />
    </div>
    <div className="min-w-0">
      <p className="text-[10px] text-slate-400 font-extrabold uppercase tracking-widest mb-0.5">{label}</p>
      <p className="text-xl font-extrabold text-slate-900 leading-tight">{value}</p>
      {sub && <p className="text-[10px] text-slate-400 font-medium mt-0.5">{sub}</p>}
    </div>
    {trend && (
      <div className="ml-auto flex-shrink-0">
        {trend === "up" && <TrendingUp size={16} className="text-red-400" />}
        {trend === "down" && <TrendingDown size={16} className="text-emerald-400" />}
      </div>
    )}
  </div>
);

// ── Spec Row ──────────────────────────────────────────────────────────────────
const SpecRow = ({ icon: Icon, label, value }: { icon: any; label: string; value: string }) => (
  <div className="flex items-center gap-3 py-3 border-b border-slate-50 last:border-b-0 group hover:bg-slate-50/50 -mx-2 px-2 rounded-xl transition-colors">
    <div className="p-2 bg-slate-100 rounded-xl group-hover:bg-blue-50 transition-colors flex-shrink-0">
      <Icon size={14} className="text-slate-500 group-hover:text-blue-600 transition-colors" />
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-[10px] text-slate-400 font-extrabold uppercase tracking-wider">{label}</p>
      <p className="text-sm font-bold text-slate-700 truncate">{value || "N/A"}</p>
    </div>
  </div>
);

// ── Section Heading ───────────────────────────────────────────────────────────
const SectionTitle = ({ icon: Icon, title, subtitle }: { icon: any; title: string; subtitle?: string }) => (
  <div className="flex items-center gap-3 mb-5">
    <div className="p-2.5 bg-blue-50 rounded-xl">
      <Icon size={18} className="text-blue-600" />
    </div>
    <div>
      <h3 className="font-extrabold text-slate-800 text-base leading-tight">{title}</h3>
      {subtitle && <p className="text-xs text-slate-400 font-medium">{subtitle}</p>}
    </div>
  </div>
);

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function TransformerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const [loading, setLoading]       = useState(true);
  const [detail, setDetail]         = useState<DetailData | null>(null);
  const [timeseries, setTimeseries] = useState<TSPoint[]>([]);
  const [history, setHistory]       = useState<any[]>([]);
  const [maintenance, setMaintenance] = useState<MLog[]>([]);
  const [shap, setShap]             = useState<ShapRow[]>([]);
  const [risk, setRisk]             = useState<Risk | null>(null);
  const [weather, setWeather]       = useState<WeatherImpact | null>(null);
  const [activeChart, setActiveChart] = useState<"load" | "temp" | "voltage" | "current">("load");
  const [selectedModel, setSelectedModel] = useState<"fused" | "isolation_forest" | "xgboost" | "random_forest" | "cox">("fused");

  // Maintenance form
  const [mType, setMType]           = useState("OIL_FILTERATION");
  const [mDesc, setMDesc]           = useState("");
  const [mFindings, setMFindings]   = useState("");
  const [oilBdv, setOilBdv]         = useState("");
  const [submitState, setSubmitState] = useState<"idle" | "loading" | "success" | "error">("idle");

  const currentRisk = React.useMemo(() => {
    if (selectedModel === "fused") {
      return {
        anomaly_score: risk ? (100.0 - (risk.health_score ?? 100.0)) : 0.0,
        risk_category: risk?.risk_category ?? "UNKNOWN",
        expected_lifetime_days: risk?.expected_lifetime_days ?? 365
      };
    }
    if (risk?.model_predictions && (risk.model_predictions as any)[selectedModel]) {
      return (risk.model_predictions as any)[selectedModel];
    }
    return {
      anomaly_score: risk?.anomaly_score ?? 0,
      risk_category: risk?.risk_category ?? "UNKNOWN",
      expected_lifetime_days: risk?.expected_lifetime_days ?? 365
    };
  }, [risk, selectedModel]);

  const loadData = useCallback(async () => {
    try {
      const [detailRes] = await Promise.allSettled([apiClient.get(`/transformers/${id}/detail`)]);
      let detailData: DetailData | null = null;
      if (detailRes.status === "fulfilled") {
        detailData = detailRes.value.data;
        setDetail(detailData);
      }

      const [ts, maint, shapR, riskR, historyR] = await Promise.allSettled([
        apiClient.get(`/transformers/${id}/timeseries`),
        apiClient.get(`/transformers/${id}/maintenance`),
        apiClient.get(`/transformers/${id}/shap-explanations`),
        apiClient.get(`/transformers/${id}/risk-score`),
        apiClient.get(`/transformers/${id}/score-history`),
      ]);
      if (ts.status === "fulfilled")    setTimeseries(ts.value.data);
      if (maint.status === "fulfilled") setMaintenance(maint.value.data);
      if (shapR.status === "fulfilled") setShap(shapR.value.data);
      if (riskR.status === "fulfilled") setRisk(riskR.value.data);
      else setRisk({ anomaly_score: 0, risk_category: "UNKNOWN", expected_lifetime_days: 0 });
      if (historyR.status === "fulfilled") setHistory(historyR.value.data);

      // ── Live Weather: Call Open-Meteo directly from frontend ─────────────────
      // This is fully independent of backend — works even if Render is down.
      // Parse lat/lon from "POINT(lon lat)" string from detail
      try {
        let lat = 26.14;  // Default: Guwahati, Assam
        let lon = 91.74;
        if (detailData?.location) {
          const match = detailData.location.match(/POINT\(([\d.\-]+)\s+([\d.\-]+)\)/);
          if (match) { lon = parseFloat(match[1]); lat = parseFloat(match[2]); }
        }
        const wRes = await fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`,
          { signal: AbortSignal.timeout(4000) }
        );
        if (wRes.ok) {
          const wJson = await wRes.json();
          const ambientTemp: number = wJson?.current_weather?.temperature ?? 30.0;
          const penalty = ambientTemp > 35.0 ? Math.min(15.0, (ambientTemp - 35.0) * 2.0) : 0.0;
          setWeather({
            ambient_temperature_c: ambientTemp,
            weather_penalty_percentage: Math.round(penalty * 10) / 10,
            is_hot_day: ambientTemp > 35.0,
          });
        }
      } catch {
        // Weather fetch failed silently — badge won't show, rest of page is fine
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    if (!risk) return;
    if (selectedModel === "xgboost") {
      setShap(risk.xgb_shap_values || []);
    } else {
      setShap(risk.shap_values || []);
    }
  }, [risk, selectedModel]);

  const handleMaintSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitState("loading");
    try {
      await apiClient.post(`/transformers/${id}/maintenance`, {
        maintenance_date: new Date().toISOString().split("T")[0],
        maintenance_type: mType,
        work_description: mDesc,
        findings: mFindings,
        oil_bdv_kv: oilBdv ? parseFloat(oilBdv) : null,
        outcome: "COMPLETED",
      });
      setSubmitState("success");
      setMDesc(""); setMFindings(""); setOilBdv("");
      await loadData();
      setTimeout(() => setSubmitState("idle"), 3000);
    } catch {
      setSubmitState("error");
      setTimeout(() => setSubmitState("idle"), 3000);
    }
  };

  // ── Loading screen ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-4 border-slate-200" />
            <div className="absolute inset-0 rounded-full border-4 border-blue-600 border-t-transparent animate-spin" />
            <Zap size={22} className="absolute inset-0 m-auto text-blue-600" />
          </div>
          <p className="text-slate-500 font-semibold text-sm">Loading asset intelligence…</p>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center text-center">
        <div>
          <WifiOff size={48} className="text-slate-300 mx-auto mb-4" />
          <h2 className="text-xl font-extrabold text-slate-800 mb-2">Asset Not Found</h2>
          <p className="text-slate-500 text-sm mb-4">This transformer may have been removed or the ID is invalid.</p>
          <Link href="/dashboard" className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-bold hover:bg-blue-700 transition-colors">
            <ArrowLeft size={15} /> Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  // ── Derived data ─────────────────────────────────────────────────────────────

  const riskMeta = RISK_META[currentRisk.risk_category] ?? RISK_META.UNKNOWN;
  const latest   = timeseries[timeseries.length - 1] ?? { temperature_c: 0, load_percentage: 0, voltage_lv: 0, current_a: 0 };
  const formattedTS = timeseries.map(pt => ({
    ...pt,
    t: new Date(pt.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  }));

  const formattedShap = shap.map(s => {
    // For Isolation Forest/Fused, lower decision function score = higher anomaly.
    // Invert the SHAP value and scale by 100.
    // For XGBoost/RF, positive SHAP increases the class probability (increases risk).
    const rawImpact = (selectedModel === "isolation_forest" || selectedModel === "fused")
      ? -100.0 * s.shap_value
      : 100.0 * s.shap_value;

    return {
      feature: featureLabel[s.feature_name] ?? s.feature_name.replace(/_/g, " ").toUpperCase(),
      rawFeatureName: s.feature_name,
      impact:  rawImpact,
      value:   s.feature_value,
      absImpact: Math.abs(rawImpact),
    };
  }).sort((a, b) => b.absImpact - a.absImpact);

  // Chart selector config
  const chartConfig: Record<typeof activeChart, { key: string; color: string; label: string; unit: string }> = {
    load:    { key: "load_percentage", color: "#3B82F6", label: "Load Factor",    unit: "%" },
    temp:    { key: "temperature_c",   color: "#EF4444", label: "Oil Temperature",unit: "°C" },
    voltage: { key: "voltage_lv",      color: "#8B5CF6", label: "LV Voltage",     unit: "V" },
    current: { key: "current_a",       color: "#F59E0B", label: "Current",        unit: "A" },
  };
  const cc = chartConfig[activeChart];

  // Risk score color for gauge
  const scoreColor =
    (currentRisk.anomaly_score) >= 90 ? "#ef4444" :
    (currentRisk.anomaly_score) >= 70 ? "#f59e0b" : "#10b981";

  return (
    <div className="min-h-screen bg-slate-50">

      {/* ── Hero Header ─────────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-8 py-5">
          {/* Breadcrumb */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
              <Link href="/dashboard" className="hover:text-slate-700 transition-colors flex items-center gap-1">
                <LayoutDashboard size={12} /> Dashboard
              </Link>
              <ChevronRight size={12} />

              <span className="text-slate-600 font-bold">{detail.transformer_code}</span>
            </div>

            {/* Active Model Selector */}
            {risk?.model_predictions && (
              <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-xl border border-slate-200/60 shadow-inner">
                {[
                  { id: "fused", label: "Consolidated Fusion (Prod)" },
                  { id: "isolation_forest", label: "Isolation Forest (15%)" },
                  { id: "xgboost", label: "XGBoost (35%)" },
                  { id: "random_forest", label: "Random Forest" },
                  { id: "cox", label: "Cox Survival (50%)" }
                ].map(m => (
                  <button
                    key={m.id}
                    onClick={() => setSelectedModel(m.id as any)}
                    className={`px-3 py-1.5 rounded-lg text-[10px] font-extrabold tracking-wide transition-all ${
                      selectedModel === m.id
                        ? "bg-white text-slate-800 shadow-sm border border-slate-200/10"
                        : "text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
            {/* Identity */}
            <div className="flex items-center gap-5">
              {/* Risk Orb */}
              <div className={`relative w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg ${riskMeta.glow} flex-shrink-0`}
                style={{ background: `linear-gradient(135deg, ${scoreColor}22, ${scoreColor}44)`, border: `2px solid ${scoreColor}33` }}>
                <Zap size={26} style={{ color: scoreColor }} />
                {(currentRisk.risk_category === "CRITICAL" || currentRisk.risk_category === "WARNING") && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 border-2 border-white animate-pulse" />
                )}
              </div>

              <div>
                <div className="flex items-center gap-3 flex-wrap">
                  <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">{detail.transformer_code}</h1>
                  <span className={`inline-flex items-center gap-1.5 text-xs font-extrabold px-3 py-1 rounded-full border ${riskMeta.color} bg-white ${riskMeta.border}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${riskMeta.bg} ${currentRisk.risk_category === "CRITICAL" ? "animate-pulse" : ""}`} />
                    {riskMeta.label} RISK
                  </span>
                  
                  {weather && weather.weather_penalty_percentage > 0 && (
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-orange-50 text-orange-600 border border-orange-200 shadow-sm" title={`Live Ambient Temp: ${weather.ambient_temperature_c}°C`}>
                      ☀️ {weather.ambient_temperature_c.toFixed(1)}°C (Includes +{weather.weather_penalty_percentage.toFixed(1)}% Weather Penalty)
                    </span>
                  )}
                  {weather && weather.weather_penalty_percentage === 0 && (
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 shadow-sm">
                      ☁️ {weather.ambient_temperature_c.toFixed(1)}°C (Optimal Weather)
                    </span>
                  )}

                  <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
                    detail.operational_status === "IN_SERVICE"
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : "bg-slate-100 text-slate-500 border border-slate-200"
                  }`}>
                    {detail.operational_status === "IN_SERVICE" ? <><Wifi size={10} className="inline mr-1" />IN SERVICE</> : <><WifiOff size={10} className="inline mr-1" />OUT OF SERVICE</>}
                  </span>
                </div>
                <p className="text-slate-500 text-sm font-medium mt-1.5 flex items-center gap-3 flex-wrap">
                  <span className="flex items-center gap-1"><MapPin size={13} className="text-blue-500" />{detail.address_text || detail.district || "Location N/A"}</span>
                  {detail.substation_name && <span className="flex items-center gap-1"><Factory size={13} className="text-slate-400" />{detail.substation_name}</span>}
                </p>
              </div>
            </div>

            {/* Lifetime card */}
            <div className="bg-slate-50 border border-slate-100 rounded-2xl px-6 py-4 text-center min-w-[180px]">
              <p className="text-[10px] text-slate-400 font-extrabold uppercase tracking-widest mb-1">Expected Lifetime</p>
              <p className="text-3xl font-black text-slate-900 tracking-tight leading-none">
                {currentRisk.expected_lifetime_days ?? "—"}
              </p>
              <p className="text-xs text-slate-400 font-medium mt-1">days remaining</p>
              {currentRisk.expected_lifetime_days !== undefined && currentRisk.expected_lifetime_days < 90 && (
                <p className="mt-2 text-[10px] font-bold text-amber-600 flex items-center justify-center gap-1">
                  <CircleAlert size={10} /> Schedule maintenance
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Body ────────────────────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-8 py-8 space-y-8">

        {/* ── KPI Strip ──────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatBadge icon={Thermometer}  label="Oil Temperature" value={`${latest.temperature_c.toFixed(1)} °C`}     sub="Latest reading"  iconBg="bg-red-50 text-red-500"      trend={latest.temperature_c > 70 ? "up" : "neutral"} />
          <StatBadge icon={Gauge}        label="Load Factor"     value={`${latest.load_percentage.toFixed(1)}%`}     sub="Current load"    iconBg="bg-amber-50 text-amber-500"  trend={latest.load_percentage > 85 ? "up" : "neutral"} />
          <StatBadge icon={Cpu}          label="LV Voltage"      value={`${latest.voltage_lv.toFixed(0)} V`}         sub="At secondary"    iconBg="bg-blue-50 text-blue-500" />
          <StatBadge icon={ShieldAlert}  label="Anomaly Score"   value={`${(currentRisk.anomaly_score).toFixed(1)}%`} sub="AI risk index"   iconBg="bg-purple-50 text-purple-500" trend={(currentRisk.anomaly_score) > 50 ? "up" : "down"} />
        </div>

        {/* ── Main Grid (Charts + Sidebar) ───────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* LEFT: Charts Column */}
          <div className="lg:col-span-2 space-y-6">

            {/* SCADA Trend Chart */}
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-7">
              <SectionTitle icon={Activity} title="Live SCADA Telemetry (24h)" subtitle="Real-time sensor readings from IoT gateway" />

              {/* Chart pill selector */}
              <div className="flex gap-2 mb-5 flex-wrap">
                {(["load", "temp", "voltage", "current"] as const).map(k => (
                  <button key={k} onClick={() => setActiveChart(k)}
                    className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                      activeChart === k
                        ? "text-white shadow-md"
                        : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                    }`}
                    style={activeChart === k ? { background: chartConfig[k].color } : {}}
                  >
                    {chartConfig[k].label}
                  </button>
                ))}
              </div>

              {formattedTS.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-52 bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-slate-400">
                  <WifiOff size={32} className="mb-2 opacity-40" />
                  <p className="text-sm font-semibold">No telemetry data available</p>
                  <p className="text-xs mt-1">IoT sensors may be offline</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={formattedTS} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor={cc.color} stopOpacity={0.15} />
                        <stop offset="95%" stopColor={cc.color} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis dataKey="t" stroke="#CBD5E1" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#CBD5E1" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey={cc.key}
                      stroke={cc.color}
                      strokeWidth={2.5}
                      fill="url(#areaGrad)"
                      name={`${cc.label} (${cc.unit})`}
                      dot={false}
                      activeDot={{ r: 5, fill: cc.color, stroke: "#fff", strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}

              {/* Mini stats row */}
              {formattedTS.length > 0 && (
                <div className="grid grid-cols-3 gap-3 mt-5 pt-4 border-t border-slate-50">
                  {["Min", "Avg", "Max"].map(stat => {
                    const vals = formattedTS.map(d => (d as any)[cc.key] as number);
                    const v = stat === "Min" ? Math.min(...vals) : stat === "Max" ? Math.max(...vals) : vals.reduce((a, b) => a + b, 0) / vals.length;
                    return (
                      <div key={stat} className="text-center">
                        <p className="text-[10px] text-slate-400 font-extrabold uppercase tracking-wider">{stat}</p>
                        <p className="text-base font-extrabold text-slate-800 mt-0.5">{v.toFixed(1)}<span className="text-xs text-slate-400 font-medium ml-0.5">{cc.unit}</span></p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* AI Health Index Trend */}
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-7">
              <SectionTitle icon={TrendingUp} title="AI Health Index Trend" subtitle="Historical daily health score evaluation history" />

              {history.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-52 bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-slate-400">
                  <TrendingUp size={32} className="mb-2 opacity-40" />
                  <p className="text-sm font-semibold">No historical evaluation data available</p>
                  <p className="text-xs mt-1">Run daily batch predictions to construct history</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={history.map(h => ({
                    ...h,
                    formattedDate: new Date(h.calculated_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })
                  }))} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="healthGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor={scoreColor} stopOpacity={0.15} />
                        <stop offset="95%" stopColor={scoreColor} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis dataKey="formattedDate" stroke="#CBD5E1" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#CBD5E1" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                    <Tooltip content={<CustomTooltip />} />
                    {/* Visual threshold guidelines */}
                    <ReferenceLine y={10} stroke="#ef4444" strokeDasharray="3 3" label={{ value: 'Critical Threshold', fill: '#ef4444', fontSize: 10, position: 'top' }} />
                    <ReferenceLine y={30} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'Warning Threshold', fill: '#f59e0b', fontSize: 10, position: 'top' }} />
                    <Area
                      type="monotone"
                      dataKey="health_score"
                      stroke={scoreColor}
                      strokeWidth={2.5}
                      fill="url(#healthGrad)"
                      name="Health Score (%)"
                      dot={{ r: 4, fill: scoreColor, stroke: "#fff", strokeWidth: 1.5 }}
                      activeDot={{ r: 6, fill: scoreColor, stroke: "#fff", strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* SHAP AI Explanation Chart */}
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-7">
              <SectionTitle icon={BrainCircuit} title="AI Explainability (SHAP)" subtitle="Why did the AI assign this risk score?" />

              {/* Explanation note */}
              <div className="flex items-start gap-3 bg-blue-50/50 border border-blue-100 rounded-2xl p-4 mb-6 text-xs text-blue-700">
                <Info size={15} className="flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold">How to read:</span> <span className="font-medium">Positive values (right/red)</span> indicate the feature is <em>driving the risk score higher</em>. <span className="font-medium">Negative values (left/green)</span> indicate it's keeping the transformer healthier. The bar length represents the relative strength of that influence.
                </div>
              </div>

              {formattedShap.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-slate-400">
                  <Brain size={32} className="mb-2 opacity-40" />
                  <p className="text-sm font-semibold">No AI diagnostics available</p>
                  <p className="text-xs mt-1">Run an AI scan to generate explanations</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Top 6 key factors */}
                  {formattedShap.slice(0, 6).map((item) => {
                    const maxVal = Math.max(...formattedShap.map(x => x.absImpact)) || 1.0;
                    const percentWidth = Math.min(100, (item.absImpact / maxVal) * 100);
                    const isPositive = item.impact > 0;

                    // Feature value formatter helper inside map function
                    const getFeatureValueWithUnit = (key: string, val: number) => {
                      if (key === "temp_c" || key === "ambient_temp" || key === "temperature_rise") return `${val.toFixed(1)} °C`;
                      if (key === "load_pct" || key === "load_ratio" || key === "current_ratio") return `${val.toFixed(1)}%`;
                      if (key === "v_lv") return `${val.toFixed(0)} V`;
                      if (key === "curr_a") return `${val.toFixed(1)} A`;
                      if (key === "age_years") return `${val.toFixed(0)} yrs`;
                      if (key === "rated_kva") return `${val.toFixed(0)} kVA`;
                      return val.toFixed(2);
                    };

                    return (
                      <div key={item.feature} className="group flex flex-col md:flex-row md:items-center justify-between gap-3 p-3 rounded-2xl border border-slate-100 hover:border-slate-200/80 hover:bg-slate-50/50 transition-all">
                        {/* Feature Name & Value */}
                        <div className="flex items-center gap-2.5 min-w-[220px]">
                          <div className={`p-2 rounded-xl flex-shrink-0 ${isPositive ? "bg-red-50 text-red-500" : "bg-emerald-50 text-emerald-500"}`}>
                            {item.rawFeatureName.includes("temp") ? <Thermometer size={14} /> :
                             item.rawFeatureName.includes("load") ? <Gauge size={14} /> :
                             item.rawFeatureName.includes("voltage") || item.rawFeatureName.includes("v_lv") ? <Cpu size={14} /> :
                             item.rawFeatureName.includes("current") || item.rawFeatureName.includes("curr_a") ? <Zap size={14} /> :
                             <Info size={14} />}
                          </div>
                          <div className="flex flex-col">
                            <span className="text-xs font-bold text-slate-800">{item.feature}</span>
                            <span className="text-[10px] font-semibold text-slate-400">Value: {getFeatureValueWithUnit(item.rawFeatureName, item.value)}</span>
                          </div>
                        </div>

                        {/* Centered Diverging Bar */}
                        <div className="flex-1 flex items-center justify-center relative min-w-[120px] px-2">
                          {/* Left half (Negative impact - green) */}
                          <div className="w-1/2 flex justify-end pr-0.5 border-r border-slate-200">
                            {!isPositive && (
                              <div
                                className="h-2 rounded-l-full bg-gradient-to-l from-emerald-500 to-emerald-300"
                                style={{ width: `${percentWidth}%` }}
                              />
                            )}
                          </div>
                          {/* Right half (Positive impact - red) */}
                          <div className="w-1/2 flex justify-start pl-0.5">
                            {isPositive && (
                              <div
                                className="h-2 rounded-r-full bg-gradient-to-r from-red-400 to-red-600"
                                style={{ width: `${percentWidth}%` }}
                              />
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}

                    {/* SHAP Legend */}
                    <div className="flex items-center gap-5 mt-4 pt-4 border-t border-slate-100 text-xs font-semibold text-slate-500">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-red-500" /> Increases Risk
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Reduces Risk
                      </div>
                      <div className="ml-auto text-[10px] text-slate-400 italic">
                        SHAP values dynamically extracted from {selectedModel === "fused" ? "Isolation Forest" : selectedModel.replace(/_/g, " ")} Model
                      </div>
                    </div>
                </div>
              )}
            </div>

            {/* Risk Gauge Card */}
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-7">
              <SectionTitle icon={FlaskConical} title="Risk Score Breakdown" subtitle="Composite AI-computed risk index" />

              {/* Show the Decision Fusion Breakdown when in Consolidated/Fused mode */}
              {selectedModel === "fused" && risk?.model_predictions ? (
                <div className="space-y-6">
                  {/* Top: Flow Diagram Pipeline */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Cox PH Card */}
                    <div className="relative p-4 rounded-2xl bg-gradient-to-br from-slate-50 to-indigo-50/20 border border-slate-200/60 shadow-sm hover:shadow transition-all">
                      <div className="absolute top-3 right-3 text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-50 text-indigo-600 border border-indigo-100">
                        Weight: 50%
                      </div>
                      <p className="text-[10px] text-slate-400 font-extrabold uppercase tracking-wider mb-1">Cox Survival Model</p>
                      <h4 className="text-xl font-black text-indigo-700 leading-none">
                        {(risk.model_predictions.cox?.anomaly_score ?? 0).toFixed(0)}%
                      </h4>
                      <p className="text-[10px] font-semibold text-slate-400 mt-2">Contrib: <span className="text-indigo-600 font-black">+{( (risk.model_predictions.cox?.anomaly_score ?? 0) * 0.50 ).toFixed(1)}%</span></p>
                      <p className="text-[9px] text-slate-400 mt-1 truncate">Time-to-failure reliability index</p>
                    </div>

                    {/* XGBoost/RF Card */}
                    <div className="relative p-4 rounded-2xl bg-gradient-to-br from-slate-50 to-purple-50/20 border border-slate-200/60 shadow-sm hover:shadow transition-all">
                      <div className="absolute top-3 right-3 text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-purple-50 text-purple-600 border border-purple-100">
                        Weight: 35%
                      </div>
                      <p className="text-[10px] text-slate-400 font-extrabold uppercase tracking-wider mb-1">Supervised Classifier</p>
                      <h4 className="text-xl font-black text-purple-700 leading-none">
                        {Math.max(risk.model_predictions.xgboost?.anomaly_score ?? 0, risk.model_predictions.random_forest?.anomaly_score ?? 0).toFixed(0)}%
                      </h4>
                      <p className="text-[10px] font-semibold text-slate-400 mt-2">Contrib: <span className="text-purple-600 font-black">+{( Math.max(risk.model_predictions.xgboost?.anomaly_score ?? 0, risk.model_predictions.random_forest?.anomaly_score ?? 0) * 0.35 ).toFixed(1)}%</span></p>
                      <p className="text-[9px] text-slate-400 mt-1 truncate">Worst of XGB ({risk.model_predictions.xgboost?.anomaly_score ?? 0}%) vs RF ({risk.model_predictions.random_forest?.anomaly_score ?? 0}%)</p>
                    </div>

                    {/* Isolation Forest Card */}
                    <div className="relative p-4 rounded-2xl bg-gradient-to-br from-slate-50 to-cyan-50/20 border border-slate-200/60 shadow-sm hover:shadow transition-all">
                      <div className="absolute top-3 right-3 text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-50 text-cyan-600 border border-cyan-100">
                        Weight: 15%
                      </div>
                      <p className="text-[10px] text-slate-400 font-extrabold uppercase tracking-wider mb-1">Isolation Forest Anomaly</p>
                      <h4 className="text-xl font-black text-cyan-700 leading-none">
                        {(risk.model_predictions.isolation_forest?.anomaly_score ?? 0).toFixed(0)}%
                      </h4>
                      <p className="text-[10px] font-semibold text-slate-400 mt-2">Contrib: <span className="text-cyan-600 font-black">+{( (risk.model_predictions.isolation_forest?.anomaly_score ?? 0) * 0.15 ).toFixed(1)}%</span></p>
                      <p className="text-[9px] text-slate-400 mt-1 truncate">Telemetry outlier detection</p>
                    </div>
                  </div>

                  {/* Flow Connection Arrow */}
                  <div className="flex justify-center items-center -my-2">
                    <div className="w-px h-6 bg-slate-200 border-dashed" />
                  </div>
                </div>
              ) : null}

              {/* Central Consolidated Score Display */}
              <div className="flex items-center gap-8 mt-4 bg-slate-50/50 p-5 rounded-3xl border border-slate-100 shadow-inner">
                {/* Circular gauge */}
                <div className="relative w-32 h-32 flex-shrink-0">
                  <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
                    <circle cx="60" cy="60" r="50" fill="none" stroke="#E2E8F0" strokeWidth="12" />
                    {/* Base score arc */}
                    <circle cx="60" cy="60" r="50" fill="none" stroke={scoreColor} strokeWidth="12"
                      strokeDasharray={`${2 * Math.PI * 50 * (currentRisk.anomaly_score) / 100} ${2 * Math.PI * 50}`}
                      strokeLinecap="round" className="transition-all duration-1000 ease-out" />
                      
                    {/* Weather penalty arc (overlayed on top) */}
                    {weather && weather.weather_penalty_percentage > 0 && (
                      <circle cx="60" cy="60" r="50" fill="none" stroke="#F97316" strokeWidth="12"
                        strokeDasharray={`${2 * Math.PI * 50 * (weather.weather_penalty_percentage) / 100} ${2 * Math.PI * 50}`}
                        strokeDashoffset={`-${2 * Math.PI * 50 * (currentRisk.anomaly_score - weather.weather_penalty_percentage) / 100}`}
                        strokeLinecap="round" className="transition-all duration-1000 ease-out" />
                    )}
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center rotate-0">
                    <span className="text-3xl font-black text-slate-800">{(currentRisk.anomaly_score).toFixed(0)}</span>
                    <span className="text-[10px] font-bold text-slate-400">RISK INDEX</span>
                  </div>
                </div>

                {/* Tier explanations */}
                <div className="flex-1 space-y-2.5">
                  {[
                    { tier: "CRITICAL", range: "90–100", color: "bg-red-500",    active: (currentRisk.anomaly_score) >= 90 },
                    { tier: "WARNING",  range: "70–89",  color: "bg-amber-400",  active: (currentRisk.anomaly_score) >= 70 && (currentRisk.anomaly_score) < 90 },
                    { tier: "HEALTHY",  range: "0–69",   color: "bg-emerald-500",active: (currentRisk.anomaly_score) < 70 },
                  ].map(r => (
                    <div key={r.tier} className={`flex items-center gap-3 py-2 px-3 rounded-xl transition-all ${r.active ? "bg-white shadow-sm ring-1 ring-slate-200" : "opacity-40"}`}>
                      <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${r.color}`} />
                      <span className="text-xs font-extrabold text-slate-700">{r.tier}</span>
                      <span className="text-xs text-slate-400 ml-auto">{r.range}</span>
                      {r.active && <CheckCircle size={13} className="text-emerald-600" />}
                    </div>
                  ))}
                </div>
              </div>

              {/* Weather Factor Breakdown */}
              {weather && (
                <div className={`mt-5 pt-5 border-t border-slate-100 rounded-2xl p-4 ${weather.weather_penalty_percentage > 0 ? "bg-orange-50 border border-orange-100" : "bg-emerald-50 border border-emerald-100"}`}>
                  <p className={`text-[10px] font-extrabold uppercase tracking-widest mb-3 ${weather.weather_penalty_percentage > 0 ? "text-orange-600" : "text-emerald-600"}`}>
                    {weather.weather_penalty_percentage > 0 ? "⚠️ Ambient Heat Stress Applied" : "✅ No Weather Penalty Applied"}
                  </p>
                  <div className="space-y-2">
                    {/* Base score row */}
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-blue-400 flex-shrink-0" />
                        <span className="text-slate-600 font-semibold">Base AI Fused Score</span>
                        <span className="text-slate-400 text-[10px]">(COX 50% + Classifier 35% + IF 15%)</span>
                      </div>
                      <span className="font-extrabold text-slate-800">
                        {Math.max(0, (currentRisk.anomaly_score) - weather.weather_penalty_percentage).toFixed(1)}%
                      </span>
                    </div>
                    {/* Weather penalty row */}
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${weather.weather_penalty_percentage > 0 ? "bg-orange-400" : "bg-slate-200"}`} />
                        <span className="text-slate-600 font-semibold">
                          {weather.is_hot_day ? "☀️" : "☁️"} Weather Penalty
                        </span>
                        <span className="text-slate-400 text-[10px]">({weather.ambient_temperature_c.toFixed(1)}°C ambient)</span>
                      </div>
                      <span className={`font-extrabold ${weather.weather_penalty_percentage > 0 ? "text-orange-600" : "text-slate-400"}`}>
                        {weather.weather_penalty_percentage > 0 ? `+${weather.weather_penalty_percentage.toFixed(1)}%` : "0.0%"}
                      </span>
                    </div>
                    {/* Divider & total */}
                    <div className="border-t border-slate-200 pt-2 flex items-center justify-between text-xs">
                      <span className="font-extrabold text-slate-700">Consolidated Risk Score</span>
                      <span className="font-black text-base" style={{ color: scoreColor }}>{(currentRisk.anomaly_score).toFixed(1)}%</span>
                    </div>
                  </div>
                  {weather.weather_penalty_percentage > 0 && (
                    <p className="text-[10px] text-orange-600 mt-2 font-medium">
                      Outdoor temp {weather.ambient_temperature_c.toFixed(1)}°C exceeds 35°C threshold — thermal stress adds +{weather.weather_penalty_percentage.toFixed(1)}% to failure risk.
                    </p>
                  )}
                </div>
              )}

              {/* Mode Callout */}
              {selectedModel === "fused" ? (
                <div className="mt-5 p-3.5 bg-emerald-50/50 border border-emerald-100 rounded-2xl text-[11px] text-emerald-700 flex items-start gap-2.5">
                  <CheckCircle size={14} className="mt-0.5 text-emerald-500 flex-shrink-0" />
                  <span>
                    <strong>Consolidated Fusion Active:</strong> This represents the production ensemble score. It merges the Cox Proportional Hazards timeline model (50%), the XGBoost/RF classification models (35%), and the Isolation Forest anomaly engine (15%) into a single risk profile.
                  </span>
                </div>
              ) : (
                <div className="mt-5 p-3.5 bg-blue-50/60 border border-blue-100 rounded-2xl text-[11px] text-blue-700 flex items-start gap-2.5">
                  <Info size={14} className="mt-0.5 text-blue-500 flex-shrink-0" />
                  <span>
                    <strong>Individual Diagnostic Mode:</strong> Displaying predictions specifically for the <strong>{selectedModel.replace(/_/g, " ").toUpperCase()}</strong> model. This mode is useful for granular model analysis.
                  </span>
                </div>
              )}
            </div>
          </div>


          {/* RIGHT: Sidebar Column */}
          <div className="space-y-6">

            {/* Asset Specs */}
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-6">
              <SectionTitle icon={Settings} title="Asset Specifications" />
              <SpecRow icon={Factory}  label="Manufacturer"    value={detail.manufacturer || "N/A"} />
              <SpecRow icon={Zap}      label="KVA Rating"      value={`${detail.rated_kva} kVA`} />
              <SpecRow icon={TrendingUp} label="HV Voltage"    value={`${detail.voltage_hv_kv ?? "N/A"} kV`} />
              <SpecRow icon={Activity} label="LV Voltage"      value={`${detail.voltage_lv_v ?? "N/A"} V`} />
              <SpecRow icon={Wrench}   label="Install Type"    value={detail.installation_type || "N/A"} />
              <SpecRow icon={Cpu}      label="Cooling"         value={detail.cooling_type || "N/A"} />
              <SpecRow icon={Calendar} label="Installed On"    value={new Date(detail.installation_date).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })} />
              {detail.num_consumers !== undefined && (
                <SpecRow icon={BarChart3} label="Consumers"   value={`${detail.num_consumers} connections`} />
              )}
            </div>

            {/* Environmental Risks */}
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-6">
              <SectionTitle icon={AlertTriangle} title="Environmental Flags" />
              <div className="space-y-3">
                <div className={`flex items-center gap-3 p-3.5 rounded-2xl border ${detail.is_flood_prone ? "bg-blue-50 border-blue-200" : "bg-slate-50 border-slate-100 opacity-50"}`}>
                  <span className="text-xl">🌊</span>
                  <div>
                    <p className={`text-xs font-extrabold ${detail.is_flood_prone ? "text-blue-700" : "text-slate-400"}`}>Flood-Prone Zone</p>
                    <p className="text-[10px] text-slate-400">{detail.is_flood_prone ? "High inundation risk during monsoon" : "Not in flood zone"}</p>
                  </div>
                  {detail.is_flood_prone && <CheckCircle size={15} className="text-blue-600 ml-auto" />}
                </div>
                <div className={`flex items-center gap-3 p-3.5 rounded-2xl border ${detail.is_high_lightning ? "bg-amber-50 border-amber-200" : "bg-slate-50 border-slate-100 opacity-50"}`}>
                  <span className="text-xl">⚡</span>
                  <div>
                    <p className={`text-xs font-extrabold ${detail.is_high_lightning ? "text-amber-700" : "text-slate-400"}`}>High Lightning Risk</p>
                    <p className="text-[10px] text-slate-400">{detail.is_high_lightning ? "Arrester inspections recommended" : "Normal lightning exposure"}</p>
                  </div>
                  {detail.is_high_lightning && <CheckCircle size={15} className="text-amber-600 ml-auto" />}
                </div>
              </div>
            </div>

            {/* Log Maintenance Form */}
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-6">
              <SectionTitle icon={Wrench} title="Log Site Action" subtitle="Record field maintenance activity" />

              {submitState === "success" && (
                <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-700 p-3 rounded-2xl text-xs font-bold mb-4">
                  <CheckCircle size={15} /> Maintenance logged successfully!
                </div>
              )}
              {submitState === "error" && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 p-3 rounded-2xl text-xs font-bold mb-4">
                  <CircleAlert size={15} /> Failed to save. Try again.
                </div>
              )}

              <form onSubmit={handleMaintSubmit} className="space-y-3">
                {[
                  { label: "Action Type", el: (
                    <select value={mType} onChange={e => setMType(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-100 rounded-xl px-3 py-2.5 text-sm text-slate-700 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all">
                      <option value="OIL_FILTERATION">Oil Filtration / Top-up</option>
                      <option value="BUSHING_REPLACEMENT">Bushing Replacement</option>
                      <option value="TAP_CHANGER_OVERHAUL">Tap Changer Overhaul</option>
                      <option value="GENERAL_INSPECTION">General Inspection</option>
                    </select>
                  )},
                  { label: "Oil BDV Test (kV)", el: (
                    <input type="number" step="0.1" placeholder="e.g. 45.5" value={oilBdv} onChange={e => setOilBdv(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-100 rounded-xl px-3 py-2.5 text-sm text-slate-700 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all" />
                  )},
                  { label: "Findings", el: (
                    <input type="text" placeholder="e.g. slight winding discoloration" value={mFindings} onChange={e => setMFindings(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-100 rounded-xl px-3 py-2.5 text-sm text-slate-700 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all" />
                  )},
                  { label: "Work Description", el: (
                    <textarea rows={2} placeholder="Describe the maintenance work done…" value={mDesc} onChange={e => setMDesc(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-100 rounded-xl px-3 py-2.5 text-sm text-slate-700 focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all resize-none" />
                  )},
                ].map(f => (
                  <div key={f.label}>
                    <label className="text-[10px] text-slate-400 font-extrabold uppercase tracking-wider block mb-1">{f.label}</label>
                    {f.el}
                  </div>
                ))}
                <button type="submit" disabled={submitState === "loading"}
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm py-2.5 rounded-xl transition-all shadow-md shadow-blue-500/20 active:scale-[0.98] duration-200 disabled:opacity-60 disabled:cursor-not-allowed mt-2">
                  {submitState === "loading" ? <><div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> Saving…</> : <><CheckCircle size={15} /> Submit Action Report</>}
                </button>
              </form>
            </div>

            {/* Maintenance Timeline */}
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-6">
              <SectionTitle icon={Clock} title="Maintenance Timeline" subtitle={`${maintenance.length} recorded events`} />
              <div className="space-y-4 max-h-64 overflow-y-auto pr-1">
                {maintenance.length === 0 ? (
                  <div className="text-center py-6 text-slate-400">
                    <Clock size={28} className="mx-auto mb-2 opacity-40" />
                    <p className="text-xs font-medium">No logged inspections found</p>
                  </div>
                ) : maintenance.map(log => (
                  <div key={log.id} className="relative pl-5 border-l-2 border-blue-100">
                    <div className="absolute -left-[5px] top-1.5 w-2.5 h-2.5 bg-blue-500 rounded-full shadow-sm shadow-blue-300" />
                    <div className="flex items-start justify-between gap-2 mb-0.5">
                      <span className="text-xs font-extrabold text-slate-700 leading-tight">{log.maintenance_type.replace(/_/g, " ")}</span>
                      <span className="text-[10px] text-slate-400 font-semibold flex-shrink-0">{new Date(log.maintenance_date).toLocaleDateString("en-IN")}</span>
                    </div>
                    {log.work_description && <p className="text-xs text-slate-500 leading-relaxed">{log.work_description}</p>}
                    {log.findings && <p className="text-xs text-slate-400 italic mt-0.5">{log.findings}</p>}
                    {log.oil_bdv_kv != null && (
                      <span className="mt-1 inline-block text-[10px] bg-blue-50 border border-blue-100 text-blue-700 font-bold px-2 py-0.5 rounded-full">
                        Oil BDV: {log.oil_bdv_kv} kV
                      </span>
                    )}
                    <span className={`mt-1 ml-2 inline-block text-[10px] font-bold px-2 py-0.5 rounded-full ${log.outcome === "COMPLETED" ? "bg-emerald-50 text-emerald-700 border border-emerald-100" : "bg-slate-100 text-slate-500"}`}>
                      {log.outcome}
                    </span>
                  </div>
                ))}
              </div>
            </div>

          </div> {/* end sidebar */}
        </div>
      </div>
    </div>
  );
}
