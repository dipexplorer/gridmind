"use client";

import React, { useEffect, useState, use } from 'react';
import { BentoCard } from '@/components/widgets/BentoCard';
import { Activity, ShieldAlert, Cpu, Calendar, Settings, MapPin, Wrench, BarChart3, Clock, AlertTriangle, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, BarChart, Bar, Cell, ReferenceLine } from 'recharts';

interface DetailData {
  id: string;
  transformer_code: string;
  rated_kva: number;
  voltage_hv_kv: number;
  voltage_lv_v: number;
  installation_type: string;
  cooling_type: string;
  manufacturer: string;
  address_text: string;
  district: string;
  is_flood_prone: boolean;
  is_high_lightning: boolean;
  installation_date: string;
  operational_status: string;
  location: string;
  feeder_name: string;
  substation_name: string;
}

interface TimeseriesPoint {
  time: string;
  load_percentage: number;
  voltage_lv: number;
  current_a: number;
  temperature_c: number;
}

interface MaintenanceLog {
  id: string;
  maintenance_date: string;
  maintenance_type: string;
  components_replaced?: string[];
  work_description?: string;
  findings?: string;
  oil_bdv_kv?: number;
  winding_resistance?: number;
  insulation_megohm?: number;
  outcome: string;
}

interface ShapExplanation {
  feature_name: string;
  feature_value: number;
  shap_value: number;
}

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function TransformerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<DetailData | null>(null);
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceLog[]>([]);
  const [shap, setShap] = useState<ShapExplanation[]>([]);
  const [risk, setRisk] = useState<{ anomaly_score: number; risk_category: string; expected_lifetime_days: number } | null>(null);

  // Form states
  const [mType, setMType] = useState("OIL_FILTERATION");
  const [mDesc, setMDesc] = useState("");
  const [mFindings, setMFindings] = useState("");
  const [oilBdv, setOilBdv] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState(false);

  async function loadData() {
    try {
      // 1. Details
      const detailRes = await fetch(`http://localhost:8000/api/v1/transformers/${id}/detail`, { cache: 'no-store' });
      if (detailRes.ok) {
        const detailData = await detailRes.json();
        setDetail(detailData);
      } else {
        setDetail(null);
      }

      // 2. Timeseries (SCADA)
      const tsRes = await fetch(`http://localhost:8000/api/v1/transformers/${id}/timeseries`, { cache: 'no-store' });
      if (tsRes.ok) {
        const tsData = await tsRes.json();
        setTimeseries(tsData);
      }

      // 3. Maintenance Logs
      const maintRes = await fetch(`http://localhost:8000/api/v1/transformers/${id}/maintenance`, { cache: 'no-store' });
      if (maintRes.ok) {
        const maintData = await maintRes.json();
        setMaintenance(maintData);
      }

      // 4. SHAP Explanations
      const shapRes = await fetch(`http://localhost:8000/api/v1/transformers/${id}/shap-explanations`, { cache: 'no-store' });
      if (shapRes.ok) {
        const shapData = await shapRes.json();
        setShap(shapData);
      }

      // 5. Risk scores
      const riskRes = await fetch(`http://localhost:8000/api/v1/transformers/${id}/risk-score`, { cache: 'no-store' });
      if (riskRes.ok) {
        const riskData = await riskRes.json();
        setRisk(riskData);
      } else {
        setRisk({ anomaly_score: 0, risk_category: "UNKNOWN", expected_lifetime_days: 0 });
      }

    } catch (e) {
      console.error("Failed to load transformer detail data", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [id]);

  const handleMaintenanceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`http://localhost:8000/api/v1/transformers/${id}/maintenance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          maintenance_date: new Date().toISOString().split('T')[0],
          maintenance_type: mType,
          work_description: mDesc,
          findings: mFindings,
          oil_bdv_kv: oilBdv ? parseFloat(oilBdv) : null,
          outcome: "COMPLETED"
        })
      });
      if (res.ok) {
        setSubmitSuccess(true);
        setMDesc("");
        setMFindings("");
        setOilBdv("");
        await loadData();
        setTimeout(() => setSubmitSuccess(false), 3000);
      }
    } catch (err) {
      console.error("Failed to log maintenance", err);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-slate-800">Transformer not found</h2>
        <Link href="/dashboard" className="text-primary mt-4 inline-block hover:underline">Back to Dashboard</Link>
      </div>
    );
  }

  // Format timeseries dates to readable time
  const formattedTimeseries = timeseries.map(pt => ({
    ...pt,
    timeLabel: new Date(pt.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }));

  // Format SHAP data for chart
  const formattedShap = shap.map(s => ({
    feature: s.feature_name.replace('_', ' ').toUpperCase(),
    impact: s.shap_value,
    value: s.feature_value
  })).sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));

  // Current stats (latest point from timeseries)
  const currentRead = timeseries[timeseries.length - 1] || { temperature_c: 0, load_percentage: 0, voltage_lv: 0 };

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto px-4 pb-12">
      {/* Top Navigation */}
      <div className="flex items-center gap-3">
        <Link href="/dashboard" className="p-2 bg-white hover:bg-slate-50 border border-slate-100 rounded-xl transition-colors text-slate-600">
          <ArrowLeft size={18} />
        </Link>
        <span className="text-sm font-medium text-slate-400">Back to Dashboard</span>
      </div>

      {/* Header Info */}
      <div className="flex justify-between items-start border-b border-slate-100 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-heading font-extrabold text-slate-900 tracking-tight">{detail.transformer_code}</h1>
            <span className={`text-xs font-bold px-3 py-1 rounded-full ${
              risk?.risk_category === 'CRITICAL' ? 'bg-red-50 text-red-700' : 
              risk?.risk_category === 'HIGH' ? 'bg-amber-50 text-amber-700' : 
              risk?.risk_category === 'MEDIUM' ? 'bg-blue-50 text-blue-700' :
              'bg-emerald-50 text-emerald-700'
            }`}>
              {risk?.risk_category || 'UNKNOWN'} RISK
            </span>
          </div>
          <p className="text-slate-500 mt-1 flex items-center gap-2 text-sm font-medium">
            <MapPin size={14} className="text-primary"/>
            {detail.substation_name} &bull; {detail.feeder_name}
          </p>
        </div>
        <div className="text-right">
          <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block">Expected Lifetime</span>
          <span className="text-2xl font-extrabold text-slate-800">{risk?.expected_lifetime_days || 'N/A'} Days</span>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-red-50 text-red-600 rounded-xl"><Activity size={24} /></div>
          <div>
            <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">Oil Temp</span>
            <span className="text-xl font-extrabold text-slate-800">{currentRead.temperature_c.toFixed(1)} °C</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-amber-50 text-amber-600 rounded-xl"><BarChart3 size={24} /></div>
          <div>
            <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">Active Load</span>
            <span className="text-xl font-extrabold text-slate-800">{currentRead.load_percentage.toFixed(1)}%</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-xl"><Cpu size={24} /></div>
          <div>
            <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">LV Voltage</span>
            <span className="text-xl font-extrabold text-slate-800">{currentRead.voltage_lv.toFixed(0)} V</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="p-3 bg-purple-50 text-purple-600 rounded-xl"><ShieldAlert size={24} /></div>
          <div>
            <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">Anomaly Score</span>
            <span className="text-xl font-extrabold text-slate-800">{risk?.anomaly_score?.toFixed(1) || '0.0'}%</span>
          </div>
        </div>
      </div>

      {/* Bento Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Columns (Timeseries & SHAP) */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Timeseries IoT Sensor Graph */}
          <BentoCard className="p-6 h-[380px]" title="IoT SCADA Sensors (24h Trend)">
            <div className="flex-1 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={formattedTimeseries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="timeLabel" stroke="#94A3B8" fontSize={11} />
                  <YAxis yAxisId="left" stroke="#3B82F6" fontSize={11} label={{ value: 'Load (%)', angle: -90, position: 'insideLeft', style: { fill: '#3B82F6', fontSize: 11 } }} />
                  <YAxis yAxisId="right" orientation="right" stroke="#EF4444" fontSize={11} label={{ value: 'Temp (°C)', angle: 90, position: 'insideRight', style: { fill: '#EF4444', fontSize: 11 } }} />
                  <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid #E2E8F0' }} />
                  <Legend verticalAlign="top" height={36} iconType="circle" />
                  <Line yAxisId="left" type="monotone" dataKey="load_percentage" stroke="#3B82F6" strokeWidth={2.5} name="Load factor %" activeDot={{ r: 6 }} />
                  <Line yAxisId="right" type="monotone" dataKey="temperature_c" stroke="#EF4444" strokeWidth={2.5} name="Oil Temperature °C" activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </BentoCard>

          {/* SHAP Explanations (Diverging Bar Chart) */}
          <BentoCard className="p-6 h-[340px]" title="AI SHAP Feature Impact Analysis">
            <div className="flex-1 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={formattedShap} layout="vertical" margin={{ left: 20, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis type="number" stroke="#94A3B8" fontSize={11} label={{ value: 'SHAP Value (Risk Contribution)', position: 'insideBottom', offset: -5, style: { fill: '#94A3B8', fontSize: 11 } }} />
                  <YAxis type="category" dataKey="feature" stroke="#94A3B8" fontSize={9} width={130} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: '1px solid #E2E8F0' }} 
                    formatter={(value: any, name: any, props: any) => [
                      `${value > 0 ? '+' : ''}${value.toFixed(3)} (Value: ${props.payload.value})`,
                      'SHAP Impact'
                    ]}
                  />
                  <ReferenceLine x={0} stroke="#CBD5E1" strokeWidth={1.5} />
                  <Bar dataKey="impact">
                    {formattedShap.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={entry.impact > 0 ? '#EF4444' : '#10B981'} 
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </BentoCard>

        </div>

        {/* Right Column (Asset Info, Maintenance & Actions) */}
        <div className="space-y-6">
          
          {/* Asset Metadata */}
          <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4">
            <h3 className="font-heading font-extrabold text-slate-800 text-lg border-b border-slate-100 pb-3 flex items-center gap-2">
              <Settings size={18} className="text-primary"/>
              Asset Specification
            </h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">Manufacturer</span>
                <span className="font-semibold text-slate-700">{detail.manufacturer}</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">KVA Rating</span>
                <span className="font-semibold text-slate-700">{detail.rated_kva} kVA</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">HV Voltage</span>
                <span className="font-semibold text-slate-700">{detail.voltage_hv_kv} kV</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">LV Voltage</span>
                <span className="font-semibold text-slate-700">{detail.voltage_lv_v} V</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">Installation Type</span>
                <span className="font-semibold text-slate-700">{detail.installation_type}</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 font-bold block uppercase tracking-wider">Installed On</span>
                <span className="font-semibold text-slate-700">{new Date(detail.installation_date).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          {/* Maintenance Actions Form */}
          <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4">
            <h3 className="font-heading font-extrabold text-slate-800 text-lg border-b border-slate-100 pb-3 flex items-center gap-2">
              <Wrench size={18} className="text-primary"/>
              Log Site Maintenance
            </h3>
            
            {submitSuccess && (
              <div className="bg-emerald-50 text-emerald-700 p-3 rounded-xl text-xs font-semibold animate-bounce">
                Maintenance successfully logged!
              </div>
            )}

            <form onSubmit={handleMaintenanceSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Action Type</label>
                <select 
                  value={mType} 
                  onChange={(e) => setMType(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-100 rounded-xl p-2.5 text-sm text-slate-700 focus:outline-none focus:border-primary"
                >
                  <option value="OIL_FILTERATION">Oil Filtration / Topup</option>
                  <option value="BUSHING_REPLACEMENT">Bushing Replacement</option>
                  <option value="TAP_CHANGER_OVERHAUL">Tap Changer Overhaul</option>
                  <option value="GENERAL_INSPECTION">General Inspection</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Oil BDV Test (kV)</label>
                <input 
                  type="number" 
                  step="0.1" 
                  placeholder="e.g. 45.5"
                  value={oilBdv}
                  onChange={(e) => setOilBdv(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-100 rounded-xl p-2.5 text-sm text-slate-700 focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Findings</label>
                <input 
                  type="text" 
                  placeholder="e.g. slight winding discoloration"
                  value={mFindings}
                  onChange={(e) => setMFindings(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-100 rounded-xl p-2.5 text-sm text-slate-700 focus:outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Work Done Description</label>
                <textarea 
                  rows={2} 
                  placeholder="Description of maintenance work done"
                  value={mDesc}
                  onChange={(e) => setMDesc(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-100 rounded-xl p-2.5 text-sm text-slate-700 focus:outline-none focus:border-primary resize-none"
                />
              </div>

              <button 
                type="submit" 
                className="w-full bg-primary hover:bg-blue-600 text-white font-medium text-sm py-2.5 rounded-xl transition-all shadow-sm shadow-blue-500/20"
              >
                Submit Action Report
              </button>
            </form>
          </div>

          {/* Maintenance logs list */}
          <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4">
            <h3 className="font-heading font-extrabold text-slate-800 text-lg border-b border-slate-100 pb-3 flex items-center gap-2">
              <Clock size={18} className="text-primary"/>
              Maintenance Timeline
            </h3>
            
            <div className="space-y-4 max-h-[240px] overflow-y-auto pr-1">
              {maintenance.length === 0 ? (
                <p className="text-xs text-slate-400 text-center py-4">No logged inspections found.</p>
              ) : (
                maintenance.map((log) => (
                  <div key={log.id} className="border-l-2 border-primary/20 pl-4 relative space-y-1">
                    <div className="w-2.5 h-2.5 bg-primary rounded-full absolute -left-[6px] top-1.5" />
                    <div className="flex justify-between items-start">
                      <span className="text-xs font-bold text-slate-700">{log.maintenance_type.replace('_', ' ')}</span>
                      <span className="text-[10px] text-slate-400 font-semibold">{new Date(log.maintenance_date).toLocaleDateString()}</span>
                    </div>
                    {log.work_description && (
                      <p className="text-xs text-slate-500 leading-relaxed">{log.work_description}</p>
                    )}
                    {log.oil_bdv_kv !== undefined && (
                      <span className="text-[10px] bg-slate-100 text-slate-600 font-semibold px-2 py-0.5 rounded-full inline-block mt-1">
                        Oil BDV: {log.oil_bdv_kv} kV
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
