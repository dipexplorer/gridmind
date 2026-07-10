"use client";

import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import Link from 'next/link';
import { AlertTriangle, X, Zap, MapPin, Activity, Clock, Info } from 'lucide-react';

// Fix Leaflet's default icon path issues in Next.js
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// ─── Icon Factory ─────────────────────────────────────────────────────────────
// Each risk category gets a colour-coded glowing pin.
// CRITICAL pins also get a faster blink via CSS animation.
const RISK_COLORS: Record<string, { pin: string; pulse: string; label: string }> = {
  CRITICAL: { pin: '#ef4444', pulse: 'rgba(239,68,68,0.5)',  label: '#ef4444' },
  HIGH:     { pin: '#f59e0b', pulse: 'rgba(245,158,11,0.45)', label: '#f59e0b' },
  MEDIUM:   { pin: '#3b82f6', pulse: 'rgba(59,130,246,0.4)', label: '#3b82f6' },
  LOW:      { pin: '#10b981', pulse: 'rgba(16,185,129,0.4)', label: '#10b981' },
  HEALTHY:  { pin: '#10b981', pulse: 'rgba(16,185,129,0.4)', label: '#10b981' },
  UNKNOWN:  { pin: '#94a3b8', pulse: 'rgba(148,163,184,0.3)', label: '#94a3b8' },
};

const makeIcon = (risk: string) => {
  const c = RISK_COLORS[risk] ?? RISK_COLORS.UNKNOWN;
  const isCritical = risk === 'CRITICAL';
  const pulseAnim = isCritical
    ? 'animation: criticalBlink 0.9s ease-in-out infinite;'
    : 'animation: normalPulse 2.4s ease-in-out infinite;';

  return L.divIcon({
    className: '',
    html: `
      <style>
        @keyframes criticalBlink { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.3;transform:scale(1.35)} }
        @keyframes normalPulse   { 0%,100%{opacity:.6;transform:scale(1)} 50%{opacity:.1;transform:scale(1.4)} }
      </style>
      <div style="position:relative;width:36px;height:44px;display:flex;align-items:flex-start;justify-content:center;">
        <!-- Pulse ring -->
        <div style="
          position:absolute;top:2px;left:50%;transform:translateX(-50%);
          width:30px;height:30px;border-radius:50%;
          background:${c.pulse};
          ${pulseAnim}
        "></div>
        <!-- Pin body -->
        <svg width="36" height="44" viewBox="0 0 36 44" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M18 0C10.268 0 4 6.268 4 14c0 9.9 14 30 14 30s14-20.1 14-30C32 6.268 25.732 0 18 0z"
            fill="${c.pin}" stroke="white" stroke-width="2"/>
          <!-- Zap icon inside pin -->
          <path d="M21 6l-6 8h5l-4 10 10-12h-5z" fill="white" opacity="0.95"/>
        </svg>
      </div>`,
    iconSize:   [36, 44],
    iconAnchor: [18, 44],
    popupAnchor: [0, -44],
  });
};

// Pre-build icons for all categories
const ICONS: Record<string, L.DivIcon> = {};
Object.keys(RISK_COLORS).forEach(k => { ICONS[k] = makeIcon(k); });
const getIcon = (risk: string) => ICONS[risk] ?? ICONS.UNKNOWN;

// ─── Map auto-fit helper ───────────────────────────────────────────────────────
function FitBounds({ positions }: { positions: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length > 0) {
      const bounds = L.latLngBounds(positions);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    }
  }, [map, positions]);
  return null;
}

// ─── Types ────────────────────────────────────────────────────────────────────
interface TransformerMapProps {
  transformers: any[];
  onMarkerClick?: (transformer: any) => void;
  showSidePanel?: boolean;  // Full-page mode enables the detail side panel
}

// ─── Parse WKT coords ─────────────────────────────────────────────────────────
const parseWKT = (wkt: string): [number, number] | null => {
  if (!wkt) return null;
  const m = wkt.match(/POINT\(([^ ]+)\s+([^ ]+)\)/);
  if (m) return [parseFloat(m[2]), parseFloat(m[1])]; // [lat, lon]
  return null;
};

// ─── Legend Component ─────────────────────────────────────────────────────────
function MapLegend() {
  const items = [
    { risk: 'CRITICAL', label: 'Critical Risk' },
    { risk: 'HIGH',     label: 'High Risk' },
    { risk: 'MEDIUM',   label: 'Medium Risk' },
    { risk: 'LOW',      label: 'Healthy / Low' },
    { risk: 'UNKNOWN',  label: 'Unknown / No Data' },
  ];
  return (
    <div className="absolute bottom-6 left-4 z-[1000] bg-white/95 backdrop-blur-md rounded-2xl shadow-xl border border-slate-100 p-4 min-w-[160px]">
      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">Risk Legend</p>
      {items.map(it => (
        <div key={it.risk} className="flex items-center gap-2 mb-1.5 last:mb-0">
          <span className="w-3 h-3 rounded-full flex-shrink-0 ring-1 ring-white shadow"
                style={{ background: RISK_COLORS[it.risk]?.pin }}></span>
          <span className="text-xs font-medium text-slate-600">{it.label}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Detail Side Panel ────────────────────────────────────────────────────────
function SidePanel({ tx, onClose }: { tx: any; onClose: () => void }) {
  const risk = tx.risk_category ?? 'UNKNOWN';
  const color = RISK_COLORS[risk] ?? RISK_COLORS.UNKNOWN;
  const score = tx.anomaly_score?.toFixed(1) ?? '—';
  const lifetime = tx.expected_lifetime_days;

  return (
    <div className="absolute top-0 right-0 h-full w-[300px] bg-white/98 backdrop-blur-md z-[1001] shadow-2xl border-l border-slate-100 flex flex-col animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="flex items-start justify-between p-5 border-b border-slate-100">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Transformer</p>
          <h3 className="font-extrabold text-slate-900 text-base leading-tight mt-0.5">
            {tx.name || tx.transformer_code}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">{tx.transformer_code}</p>
        </div>
        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors text-slate-400">
          <X size={16} />
        </button>
      </div>

      {/* Risk Badge */}
      <div className="px-5 py-3 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500">AI Risk Category</span>
          <span className="text-xs font-bold px-3 py-1 rounded-full text-white"
                style={{ background: color.pin }}>
            {risk}
          </span>
        </div>
        {/* Score bar */}
        <div className="mt-3">
          <div className="flex justify-between text-xs text-slate-500 mb-1.5">
            <span>Anomaly Score</span>
            <span className="font-bold text-slate-800">{score}%</span>
          </div>
          <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${Math.min(parseFloat(score) || 0, 100)}%`, background: color.pin }}
            />
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        <Row icon={<Zap size={13} />}         label="Capacity"        value={`${tx.rated_kva} kVA`} />
        <Row icon={<MapPin size={13} />}      label="Location"        value={tx.address_text || tx.district || 'Guwahati Region'} />
        <Row icon={<Activity size={13} />}    label="Status"          value={tx.operational_status || '—'} />
        <Row icon={<Info size={13} />}        label="District"        value={tx.district || '—'} />
        {lifetime !== undefined && (
          <Row icon={<Clock size={13} />}
               label="Expected Lifetime"
               value={lifetime < 30 ? `⚠ ${lifetime} days` : `${lifetime} days`}
               highlight={lifetime < 30} />
        )}
        {tx.substation_name && (
          <Row icon={<MapPin size={13} />} label="Substation" value={tx.substation_name} />
        )}
      </div>

      {/* Actions */}
      <div className="p-5 border-t border-slate-100">
        <Link
          href={`/dashboard/transformers/${tx.id}`}
          className="block w-full text-center text-sm font-semibold text-white py-2.5 rounded-xl transition-all hover:opacity-90 shadow-md"
          style={{ background: color.pin }}
        >
          View Full Analysis →
        </Link>
      </div>
    </div>
  );
}

function Row({ icon, label, value, highlight = false }: { icon: React.ReactNode; label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-start gap-2.5">
      <div className="mt-0.5 text-slate-400 flex-shrink-0">{icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
        <p className={`text-sm font-semibold truncate ${highlight ? 'text-red-600' : 'text-slate-800'}`}>{value}</p>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function TransformerMap({ transformers, onMarkerClick, showSidePanel = false }: TransformerMapProps) {
  const [selected, setSelected] = useState<any>(null);

  const validTransformers = transformers.filter(tx => tx.location && parseWKT(tx.location));
  const positions: [number, number][] = validTransformers.map(tx => parseWKT(tx.location)!);
  
  const center: [number, number] = positions.length > 0 ? positions[0] : [26.1445, 91.7362];

  const handleMarkerClick = (tx: any) => {
    if (showSidePanel) {
      setSelected(tx);
    }
    onMarkerClick?.(tx);
  };

  // Stats for full-page header bar
  const criticalCount = transformers.filter(t => t.risk_category === 'CRITICAL').length;
  const highCount     = transformers.filter(t => t.risk_category === 'HIGH').length;

  return (
    <div className="relative w-full h-full overflow-hidden">
      {/* Full-page top stats bar */}
      {showSidePanel && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-white/95 backdrop-blur-md rounded-2xl shadow-xl border border-slate-100 px-5 py-2 flex items-center gap-5">
          <Stat color="#ef4444" label="Critical" value={criticalCount} blink />
          <div className="w-px h-5 bg-slate-200" />
          <Stat color="#f59e0b" label="High Risk" value={highCount} />
          <div className="w-px h-5 bg-slate-200" />
          <Stat color="#10b981" label="Total Assets" value={transformers.length} />
        </div>
      )}

      {/* Map */}
      <MapContainer
        center={center}
        zoom={12}
        scrollWheelZoom={true}
        zoomControl={true}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />
        {positions.length > 1 && <FitBounds positions={positions} />}

        {validTransformers.map((tx) => {
          const pos = parseWKT(tx.location)!;
          const risk = tx.risk_category ?? 'UNKNOWN';

          return (
            <Marker
              key={tx.id}
              position={pos}
              icon={getIcon(risk)}
              eventHandlers={{ click: () => handleMarkerClick(tx) }}
            >
              {/* Hover tooltip */}
              <Tooltip direction="top" offset={[0, -44]} opacity={1} permanent={false}>
                <div className="bg-slate-900 text-white rounded-xl px-3 py-2 text-xs shadow-2xl min-w-[180px] pointer-events-none">
                  <div className="font-extrabold border-b border-slate-700 pb-1.5 mb-1.5 flex items-center justify-between gap-3">
                    <span>{tx.name || tx.transformer_code}</span>
                    <span className="text-[9px] font-black uppercase px-1.5 py-0.5 rounded"
                          style={{ background: RISK_COLORS[risk]?.pin ?? '#94a3b8' }}>
                      {risk}
                    </span>
                  </div>
                  <div className="text-slate-400 flex items-start gap-1">
                    <MapPin size={10} className="mt-0.5 shrink-0" />
                    <span>{tx.address_text || tx.district || 'Guwahati'}</span>
                  </div>
                  <div className="mt-1 text-slate-300">
                    Score: <strong>{tx.anomaly_score?.toFixed(1) ?? '—'}%</strong> · {tx.rated_kva} kVA
                  </div>
                  {showSidePanel && <p className="mt-1.5 text-[10px] text-indigo-400 font-semibold">Click to view details →</p>}
                </div>
              </Tooltip>

              {/* Click popup (dashboard widget mode only — no side panel) */}
              {!showSidePanel && (
                <Popup className="rounded-2xl overflow-hidden" maxWidth={240}>
                  <div className="p-1 min-w-[200px]">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-extrabold text-slate-800 text-sm">{tx.name || tx.transformer_code}</h3>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white ml-2 flex-shrink-0"
                            style={{ background: RISK_COLORS[risk]?.pin }}>
                        {risk}
                      </span>
                    </div>
                    <div className="space-y-1.5 text-xs text-slate-600">
                      <p className="flex justify-between border-b border-slate-100 pb-1">
                        <span>Capacity:</span>
                        <span className="font-bold text-slate-800">{tx.rated_kva} kVA</span>
                      </p>
                      <p className="flex justify-between border-b border-slate-100 pb-1">
                        <span>Anomaly Score:</span>
                        <span className="font-bold text-slate-800">{tx.anomaly_score?.toFixed(1) ?? '—'}%</span>
                      </p>
                      {tx.expected_lifetime_days !== undefined && (
                        <p className="flex justify-between">
                          <span className="flex items-center gap-1"><Activity size={11} /> Expected Life:</span>
                          <span className="font-bold text-slate-800">{tx.expected_lifetime_days} days</span>
                        </p>
                      )}
                    </div>
                    <Link
                      href={`/dashboard/transformers/${tx.id}`}
                      className="mt-3 block text-center text-[11px] font-bold text-white py-1.5 rounded-lg"
                      style={{ background: RISK_COLORS[risk]?.pin }}
                    >
                      Full Analysis →
                    </Link>
                  </div>
                </Popup>
              )}
            </Marker>
          );
        })}
      </MapContainer>

      {/* Legend */}
      <MapLegend />

      {/* Side panel (full-page mode) */}
      {showSidePanel && selected && (
        <SidePanel tx={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function Stat({ color, label, value, blink = false }: { color: string; label: string; value: number; blink?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${blink ? 'animate-pulse' : ''}`}
            style={{ background: color }}></span>
      <div>
        <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider leading-none">{label}</p>
        <p className="text-base font-extrabold text-slate-900 leading-tight">{value}</p>
      </div>
    </div>
  );
}
