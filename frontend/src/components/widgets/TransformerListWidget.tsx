"use client";

import React from 'react';
import { AlertTriangle, MapPin, Activity } from 'lucide-react';
import Link from 'next/link';

interface Transformer {
  id: string;
  name: string;
  location_name: string;
  risk_category: string;
  expected_lifetime_days?: number;
}

interface TransformerListWidgetProps {
  transformers: Transformer[];
}

export function TransformerListWidget({ transformers }: TransformerListWidgetProps) {
  // Only show high and critical risk
  const riskyTransformers = transformers.filter(t => 
    ['HIGH', 'CRITICAL'].includes(t.risk_category)
  );

  return (
    <div className="h-full overflow-y-auto pr-2 custom-scrollbar">
      {riskyTransformers.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-slate-400 p-6 text-center">
          <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mb-3">
            <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="font-medium text-slate-600">All Systems Healthy</p>
          <p className="text-sm mt-1">No high risk transformers detected.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {riskyTransformers.map((t) => (
            <Link 
              key={t.id} 
              href={`/dashboard/transformers/${t.id}`}
              className="flex items-start p-3 rounded-xl border border-border hover:bg-slate-50 hover:border-slate-300 transition-colors cursor-pointer group"
            >
              <div className={`p-2 rounded-lg shrink-0 mt-0.5 ${t.risk_category === 'CRITICAL' ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600'}`}>
                <AlertTriangle size={18} strokeWidth={2.5} />
              </div>
              <div className="ml-3 flex-1 min-w-0">
                <div className="flex justify-between items-baseline">
                  <h4 className="font-heading font-semibold text-sm text-foreground truncate">{t.name}</h4>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    t.risk_category === 'CRITICAL' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
                  }`}>
                    {t.risk_category}
                  </span>
                </div>
                <div className="flex items-center text-xs text-slate-500 mt-1 gap-3">
                  <span className="flex items-center gap-1 truncate">
                    <MapPin size={12} /> {t.location_name}
                  </span>
                  {t.expected_lifetime_days !== undefined && (
                    <span className="flex items-center gap-1 shrink-0 font-medium text-slate-600">
                      <Activity size={12} className={t.expected_lifetime_days < 30 ? "text-red-500" : "text-amber-500"} /> 
                      TTF: {t.expected_lifetime_days}d
                    </span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
