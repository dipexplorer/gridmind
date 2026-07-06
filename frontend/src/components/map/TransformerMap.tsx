"use client";

import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { Activity, AlertTriangle, MapPin } from 'lucide-react';

// Fix Leaflet's default icon path issues in Next.js
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Premium styled glowing map pins containing a lightning bolt (representing a transformer)
const riskStyles = {
  HEALTHY: { text: 'text-emerald-500', glow: 'bg-emerald-400' },
  MEDIUM: { text: 'text-blue-500', glow: 'bg-blue-400' },
  HIGH: { text: 'text-amber-500', glow: 'bg-amber-400' },
  CRITICAL: { text: 'text-red-500', glow: 'bg-red-400' },
  UNKNOWN: { text: 'text-slate-400', glow: 'bg-slate-300' }
};

const createCustomIcon = (riskCategory: string) => {
  const style = riskStyles[riskCategory as keyof typeof riskStyles] || riskStyles.UNKNOWN;
  return L.divIcon({
    className: 'custom-leaflet-marker-glow-pin',
    html: `
      <div class="relative w-10 h-10 flex items-center justify-center group cursor-pointer">
        <!-- Pulse ring behind pin -->
        <div class="absolute w-8 h-8 rounded-full ${style.glow} animate-ping opacity-45" style="animation-duration: 2.5s; top: 1px;"></div>
        <!-- Map Pin SVG -->
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-9 h-9 ${style.text} filter drop-shadow-md transition-transform duration-200 group-hover:scale-110" fill="currentColor">
          <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
        </svg>
        <!-- Lightning Bolt (Zap) Icon Overlay -->
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5 text-white absolute pointer-events-none transition-transform duration-200 group-hover:scale-110" style="top: 8px;">
          <path d="M11.5 2L4 12h7v10l7.5-10h-7V2z"/>
        </svg>
      </div>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 36],
  });
};

const icons = {
  HEALTHY: createCustomIcon('HEALTHY'),
  MEDIUM: createCustomIcon('MEDIUM'),
  HIGH: createCustomIcon('HIGH'),
  CRITICAL: createCustomIcon('CRITICAL'),
  UNKNOWN: createCustomIcon('UNKNOWN')
};

interface TransformerMapProps {
  transformers: any[];
  onMarkerClick?: (transformer: any) => void;
}

export default function TransformerMap({ transformers, onMarkerClick }: TransformerMapProps) {
  
  // Parse location WKT "POINT(lon lat)" -> [lat, lon] (Leaflet uses lat, lon)
  const parseCoordinates = (wkt: string): [number, number] => {
    if (!wkt) return [26.1445, 91.7362]; // Default Guwahati (lat, lon)
    const match = wkt.match(/POINT\(([^ ]+)\s+([^ ]+)\)/);
    if (match) return [parseFloat(match[2]), parseFloat(match[1])];
    return [26.1445, 91.7362];
  };

  const center: [number, number] = transformers.length > 0 
    ? parseCoordinates(transformers[0].location)
    : [26.1445, 91.7362];

  return (
    <div className="w-full h-full relative z-0">
      <MapContainer 
        center={center} 
        zoom={12} 
        scrollWheelZoom={true} 
        style={{ height: '100%', width: '100%', borderRadius: 'inherit' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />
        
        {transformers.map((tx) => {
          const pos = parseCoordinates(tx.location);
          const riskCategory = tx.risk_category || 'UNKNOWN';
          const icon = icons[riskCategory as keyof typeof icons] || icons.UNKNOWN;

          return (
            <Marker 
              key={tx.id} 
              position={pos} 
              icon={icon}
              eventHandlers={{
                click: () => onMarkerClick && onMarkerClick(tx),
              }}
            >
              {/* Sleek Tooltip hover pill displaying name & address (Google Maps style) */}
              <Tooltip 
                direction="top" 
                offset={[0, -28]} 
                opacity={0.98}
                permanent={false}
              >
                <div className="bg-slate-900/95 text-white px-3.5 py-2.5 rounded-2xl border border-slate-800 shadow-2xl backdrop-blur-md text-xs min-w-[200px] max-w-[260px] space-y-1.5 pointer-events-none animate-in fade-in zoom-in-95 duration-100">
                  <div className="font-extrabold text-slate-100 flex items-center justify-between gap-3 border-b border-slate-800 pb-1.5">
                    <span>{tx.name || tx.transformer_code}</span>
                    <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-slate-800 font-black tracking-wider text-slate-300 shrink-0">{tx.rated_kva} kVA</span>
                  </div>
                  <div className="text-[10px] text-slate-400 font-medium leading-relaxed flex items-start gap-1">
                    <MapPin size={11} className="mt-0.5 shrink-0 text-primary" />
                    <span className="break-words">{tx.address_text || "Guwahati Region"}</span>
                  </div>
                </div>
              </Tooltip>

              <Popup className="rounded-xl shadow-lg border-0">
                <div className="p-1 min-w-[200px]">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-bold text-slate-800 text-sm">{tx.name || tx.transformer_code}</h3>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      riskCategory === 'CRITICAL' ? 'bg-red-50 text-red-700' : 
                      riskCategory === 'HIGH' ? 'bg-amber-50 text-amber-700' : 
                      riskCategory === 'MEDIUM' ? 'bg-blue-50 text-blue-700' :
                      'bg-emerald-50 text-emerald-700'
                    }`}>
                      {riskCategory}
                    </span>
                  </div>
                  
                  <div className="space-y-1.5 text-xs text-slate-600">
                    <p className="flex justify-between border-b border-slate-100 pb-1">
                      <span>Capacity:</span> 
                      <span className="font-medium text-slate-800">{tx.rated_kva} kVA</span>
                    </p>
                    <p className="flex justify-between border-b border-slate-100 pb-1">
                      <span>Anomaly Score:</span> 
                      <span className="font-medium text-slate-800">{tx.anomaly_score?.toFixed(1) || 'N/A'}%</span>
                    </p>
                    {tx.expected_lifetime_days !== undefined && (
                      <p className="flex justify-between pt-0.5 items-center">
                        <span className="flex items-center gap-1">
                          <Activity size={12} className={tx.expected_lifetime_days < 30 ? "text-red-500" : "text-amber-500"} /> 
                          Expected Life:
                        </span> 
                        <span className="font-bold text-slate-800">{tx.expected_lifetime_days} days</span>
                      </p>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
