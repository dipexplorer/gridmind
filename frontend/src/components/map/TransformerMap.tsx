'use client';
import { useState } from 'react';
import Map, { Marker, NavigationControl, Popup } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

export default function TransformerMap({ transformers = [] }: { transformers: any[] }) {
  const [popupInfo, setPopupInfo] = useState<any | null>(null);

  // Parse location WKT "POINT(lon lat)" -> [lon, lat]
  const parseCoordinates = (wkt: string) => {
    if (!wkt) return [91.7362, 26.1445]; // Default Guwahati
    const match = wkt.match(/POINT\(([^ ]+)\s+([^ ]+)\)/);
    if (match) return [parseFloat(match[1]), parseFloat(match[2])];
    return [91.7362, 26.1445];
  };

  return (
    <div className="w-full h-full">
      <Map
        initialViewState={{
          longitude: 91.7362,
          latitude: 26.1445,
          zoom: 11
        }}
        mapStyle="mapbox://styles/mapbox/light-v11"
        mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN || ''}
      >
        <NavigationControl position="top-right" />

        {transformers.map((tx) => {
          const [lng, lat] = parseCoordinates(tx.location);
          const isHighRisk = tx.is_high_lightning;
          
          return (
            <Marker
              key={tx.id}
              longitude={lng}
              latitude={lat}
              anchor="bottom"
              onClick={e => {
                e.originalEvent.stopPropagation();
                setPopupInfo(tx);
              }}
            >
              <div className={`
                w-4 h-4 rounded-full border-2 border-white cursor-pointer shadow-md
                ${isHighRisk ? 'bg-red-500' : 'bg-emerald-500'}
              `} />
            </Marker>
          );
        })}

        {popupInfo && (
          <Popup
            anchor="top"
            longitude={parseCoordinates(popupInfo.location)[0]}
            latitude={parseCoordinates(popupInfo.location)[1]}
            onClose={() => setPopupInfo(null)}
            className="rounded-lg shadow-lg"
          >
            <div className="text-slate-900 p-1">
              <strong className="block text-sm">Code: {popupInfo.transformer_code}</strong>
              <p className="text-xs mt-1 text-slate-600">Capacity: {popupInfo.rated_kva} kVA</p>
              <p className="text-xs text-slate-600">Status: {popupInfo.operational_status}</p>
            </div>
          </Popup>
        )}
      </Map>
    </div>
  );
}
