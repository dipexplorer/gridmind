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
interface Risk { anomaly_score: number; risk_category: string; expected_lifetime_days: number; }
interface WeatherImpact { ambient_temperature_c: number; weather_penalty_percentage: number; is_hot_day: boolean; }

const RISK_META: Record<string, { color: string; bg: string; border: string; glow: string; label: string }> = {
  CRITICAL: { color: "text-red-700",     bg: "bg-red-500",     border: "border-red-200",    glow: "shadow-red-500/30",    label: "CRITICAL" },
  HIGH:     { color: "text-amber-700",   bg: "bg-amber-400",   border: "border-amber-200",  glow: "shadow-amber-500/30",  label: "HIGH" },
  MEDIUM:   { color: "text-blue-700",    bg: "bg-blue-500",    border: "border-blue-200",   glow: "shadow-blue-500/30",   label: "MEDIUM" },
  LOW:      { color: "text-emerald-700", bg: "bg-emerald-500", border: "border-emerald-200",glow: "shadow-emerald-500/30",label: "LOW" },
  HEALTHY:  { color: "text-emerald-700", bg: "bg-emerald-500", border: "border-emerald-200",glow: "shadow-emerald-500/30",label: "HEALTHY" },
  UNKNOWN:  { color: "text-slate-500",   bg: "bg-slate-400",   border: "border-slate-200",  glow: "shadow-slate-200",     label: "UNKNOWN" },
};

const featureLabel: Record<string, string> = {
  temperature_c: "Oil Temperature (°C)",
  load_percentage: "Load Factor (%)",
  voltage_lv: "LV Voltage (V)",
  current_a: "Current (A)",
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
  const [maintenance, setMaintenance] = useState<MLog[]>([]);
  const [shap, setShap]             = useState<ShapRow[]>([]);
  const [risk, setRisk]             = useState<Risk | null>(null);
  const [weather, setWeather]       = useState<WeatherImpact | null>(null);
  const [activeChart, setActiveChart] = useState<"load" | "temp" | "voltage" | "current">("load");

  // Maintenance form
  const [mType, setMType]           = useState("OIL_FILTERATION");
  const [mDesc, setMDesc]           = useState("");
  const [mFindings, setMFindings]   = useState("");
  const [oilBdv, setOilBdv]         = useState("");
  const [submitState, setSubmitState] = useState<"idle" | "loading" | "success" | "error">("idle");

  const loadData = useCallback(async () => {
    try {
      const [detailRes] = await Promise.allSettled([apiClient.get(`/transformers/${id}/detail`)]);
      let detailData: DetailData | null = null;
      if (detailRes.status === "fulfilled") {
        detailData = detailRes.value.data;
        setDetail(detailData);
      }

      const [ts, maint, shapR, riskR] = await Promise.allSettled([
        apiClient.get(`/transformers/${id}/timeseries`),
        apiClient.get(`/transformers/${id}/maintenance`),
        apiClient.get(`/transformers/${id}/shap-explanations`),
        apiClient.get(`/transformers/${id}/risk-score`),
      ]);
      if (ts.status === "fulfilled")    setTimeseries(ts.value.data);
      if (maint.status === "fulfilled") setMaintenance(maint.value.data);
      if (shapR.status === "fulfilled") setShap(shapR.value.data);
      if (riskR.status === "fulfilled") setRisk(riskR.value.data);
      else setRisk({ anomaly_score: 0, risk_category: "UNKNOWN", expected_lifetime_days: 0 });

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
  const riskMeta = RISK_META[risk?.risk_category ?? "UNKNOWN"] ?? RISK_META.UNKNOWN;
  const latest   = timeseries[timeseries.length - 1] ?? { temperature_c: 0, load_percentage: 0, voltage_lv: 0, current_a: 0 };
  const formattedTS = timeseries.map(pt => ({
    ...pt,
    t: new Date(pt.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  }));

  const formattedShap = shap.map(s => ({
    feature: featureLabel[s.feature_name] ?? s.feature_name.replace(/_/g, " ").toUpperCase(),
    impact:  s.shap_value,
    value:   s.feature_value,
    absImpact: Math.abs(s.shap_value),
  })).sort((a, b) => b.absImpact - a.absImpact);

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
    (risk?.anomaly_score ?? 0) >= 70 ? "#ef4444" :
    (risk?.anomaly_score ?? 0) >= 40 ? "#f59e0b" : "#10b981";

  return (
    <div className="min-h-screen bg-slate-50">

      {/* ── Hero Header ─────────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-8 py-5">
          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-4 font-medium">
            <Link href="/dashboard" className="hover:text-slate-700 transition-colors flex items-center gap-1">
              <LayoutDashboard size={12} /> Dashboard
            </Link>
            <ChevronRight size={12} />
            <Link href="/assets" className="hover:text-slate-700 transition-colors flex items-center gap-1">
              <Layers size={12} /> Assets
            </Link>
            <ChevronRight size={12} />
            <span className="text-slate-600 font-bold">{detail.transformer_code}</span>
          </div>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
            {/* Identity */}
            <div className="flex items-center gap-5">
              {/* Risk Orb */}
              <div className={`relative w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg ${riskMeta.glow} flex-shrink-0`}
                style={{ background: `linear-gradient(135deg, ${scoreColor}22, ${scoreColor}44)`, border: `2px solid ${scoreColor}33` }}>
                <Zap size={26} style={{ color: scoreColor }} />
                {(risk?.risk_category === "CRITICAL" || risk?.risk_category === "HIGH") && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 border-2 border-white animate-pulse" />
                )}
              </div>

              <div>
                <div className="flex items-center gap-3 flex-wrap">
                  <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">{detail.transformer_code}</h1>
                  <span className={`inline-flex items-center gap-1.5 text-xs font-extrabold px-3 py-1 rounded-full border ${riskMeta.color} bg-white ${riskMeta.border}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${riskMeta.bg} ${risk?.risk_category === "CRITICAL" ? "animate-pulse" : ""}`} />
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
                {risk?.expected_lifetime_days ?? "—"}
              </p>
              <p className="text-xs text-slate-400 font-medium mt-1">days remaining</p>
              {risk?.expected_lifetime_days !== undefined && risk.expected_lifetime_days < 90 && (
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
          <StatBadge icon={ShieldAlert}  label="Anomaly Score"   value={`${(risk?.anomaly_score ?? 0).toFixed(1)}%`} sub="AI risk index"   iconBg="bg-purple-50 text-purple-500" trend={(risk?.anomaly_score ?? 0) > 50 ? "up" : "down"} />
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

            {/* SHAP AI Explanation Chart */}
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-7">
              <SectionTitle icon={BrainCircuit} title="AI Explainability (SHAP)" subtitle="Why did the AI assign this risk score?" />

              {/* Explanation note */}
              <div className="flex items-start gap-3 bg-blue-50 border border-blue-100 rounded-2xl p-4 mb-5 text-xs text-blue-700">
                <Info size={15} className="flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold">How to read:</span> <span className="font-medium">Positive (red) bars</span> mean the feature is <em>pushing the risk score higher</em>. <span className="font-medium">Negative (green) bars</span> mean it's keeping the transformer healthier. Longer bar = stronger influence.
                </div>
              </div>

              {formattedShap.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-slate-400">
                  <Brain size={32} className="mb-2 opacity-40" />
                  <p className="text-sm font-semibold">No AI diagnostics available</p>
                  <p className="text-xs mt-1">Run an AI scan to generate explanations</p>
                </div>
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={formattedShap} layout="vertical" margin={{ top: 0, right: 25, left: 10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#F8FAFC" horizontal={false} />
                      <XAxis type="number" stroke="#CBD5E1" fontSize={10} tickLine={false} axisLine={false}
                        tickFormatter={v => `${v > 0 ? "+" : ""}${v.toFixed(2)}`} />
                      <YAxis type="category" dataKey="feature" stroke="#94A3B8" fontSize={11} width={140} tickLine={false} axisLine={false} />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (!active || !payload?.length) return null;
                          const d = payload[0].payload;
                          return (
                            <div className="bg-white border border-slate-200 rounded-2xl p-3 shadow-xl text-xs">
                              <p className="font-extrabold text-slate-800 mb-1">{d.feature}</p>
                              <p className="text-slate-500">Sensor value: <span className="font-bold text-slate-800">{d.value?.toFixed?.(2) ?? d.value}</span></p>
                              <p className={`font-bold mt-1 ${d.impact > 0 ? "text-red-600" : "text-emerald-600"}`}>
                                Risk contribution: {d.impact > 0 ? "+" : ""}{d.impact.toFixed(4)}
                              </p>
                            </div>
                          );
                        }}
                      />
                      <ReferenceLine x={0} stroke="#CBD5E1" strokeWidth={1.5} />
                      <Bar dataKey="impact" radius={[0, 6, 6, 0]} maxBarSize={28}>
                        {formattedShap.map((entry, i) => (
                          <Cell key={i} fill={entry.impact > 0 ? "#EF4444" : "#10B981"} fillOpacity={0.85} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>

                  {/* SHAP Legend */}
                  <div className="flex items-center gap-5 mt-4 pt-4 border-t border-slate-50 text-xs font-semibold">
                    <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-sm bg-red-500 flex-shrink-0" /> Increases risk</div>
                    <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-sm bg-emerald-500 flex-shrink-0" /> Reduces risk</div>
                    <div className="ml-auto text-slate-400 text-[10px] italic">SHAP values from IsolationForest model</div>
                  </div>
                </>
              )}
            </div>

            {/* Risk Gauge Card */}
            <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-7">
              <SectionTitle icon={FlaskConical} title="Risk Score Breakdown" subtitle="Composite AI-computed risk index" />
              <div className="flex items-center gap-8">
                {/* Circular gauge */}
                <div className="relative w-32 h-32 flex-shrink-0">
                  <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
                    <circle cx="60" cy="60" r="50" fill="none" stroke="#F1F5F9" strokeWidth="12" />
                    <circle cx="60" cy="60" r="50" fill="none" stroke={scoreColor} strokeWidth="12"
                      strokeDasharray={`${2 * Math.PI * 50 * (risk?.anomaly_score ?? 0) / 100} ${2 * Math.PI * 50}`}
                      strokeLinecap="round" className="transition-all duration-1000 ease-out" />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center rotate-0">
                    <span className="text-2xl font-black" style={{ color: scoreColor }}>{(risk?.anomaly_score ?? 0).toFixed(0)}</span>
                    <span className="text-[10px] font-bold text-slate-400">/ 100</span>
                  </div>
                </div>
                {/* Tier explanations */}
                <div className="flex-1 space-y-2.5">
                  {[
                    { tier: "CRITICAL", range: "70–100", color: "bg-red-500",    active: (risk?.anomaly_score ?? 0) >= 70 },
                    { tier: "HIGH",     range: "40–69",  color: "bg-amber-400",  active: (risk?.anomaly_score ?? 0) >= 40 && (risk?.anomaly_score ?? 0) < 70 },
                    { tier: "MEDIUM",   range: "20–39",  color: "bg-blue-500",   active: (risk?.anomaly_score ?? 0) >= 20 && (risk?.anomaly_score ?? 0) < 40 },
                    { tier: "LOW",      range: "0–19",   color: "bg-emerald-500",active: (risk?.anomaly_score ?? 0) < 20 },
                  ].map(r => (
                    <div key={r.tier} className={`flex items-center gap-3 py-2 px-3 rounded-xl transition-all ${r.active ? "bg-slate-50 ring-1 ring-slate-200" : "opacity-40"}`}>
                      <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${r.color}`} />
                      <span className="text-xs font-extrabold text-slate-700">{r.tier}</span>
                      <span className="text-xs text-slate-400 ml-auto">{r.range}</span>
                      {r.active && <CheckCircle size={13} className="text-emerald-600" />}
                    </div>
                  ))}
                </div>
              </div>
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
