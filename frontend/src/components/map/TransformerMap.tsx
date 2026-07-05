"use client";

import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { Activity, AlertTriangle } from 'lucide-react';

// Fix Leaflet's default icon path issues in Next.js
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom Icons for different risk levels
const createCustomIcon = (colorClass: string) => {
  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `<div class="w-4 h-4 rounded-full border-2 border-white shadow-md ${colorClass}"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
};

const icons = {
  HEALTHY: createCustomIcon('bg-emerald-500'),
  MEDIUM: createCustomIcon('bg-blue-500'),
  HIGH: createCustomIcon('bg-amber-500'),
  CRITICAL: createCustomIcon('bg-red-500'),
  UNKNOWN: createCustomIcon('bg-slate-400')
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
                      <span className="font-medium text-slate-800">{tx.anomaly_score?.toFixed(1) || 'N/A'}</span>
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
