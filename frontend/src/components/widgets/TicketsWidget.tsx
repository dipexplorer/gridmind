import React from 'react';
import Link from 'next/link';
import { ArrowRight, CheckCircle2, Wrench } from 'lucide-react';
import { apiClient } from '@/lib/api';

export interface Ticket {
  id: string;
  transformer_id: string;
  status: string;
  priority: string;
  description: string;
  created_at: string;
  transformer_name?: string;
}

interface TicketsWidgetProps {
  tickets: Ticket[];
  onTicketResolved?: () => void;
}

export function TicketsWidget({ tickets, onTicketResolved }: TicketsWidgetProps) {
  const handleResolve = async (ticketId: string) => {
    try {
      await apiClient.post(`/operations/tickets/${ticketId}/resolve`, {
        resolution_notes: "Resolved via dashboard quick action",
        outcome: "COMPLETED"
      });
      if (onTicketResolved) {
        onTicketResolved();
      }
    } catch (e) {
      console.error("Failed to resolve ticket", e);
    }
  };

  if (!tickets || tickets.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400">
        <CheckCircle2 size={32} className="mb-2 text-emerald-500 opacity-50" />
        <p className="text-sm font-medium">No open tickets</p>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto h-full pr-2 space-y-3 custom-scrollbar">
      {tickets.map((t) => (
        <div key={t.id} className="bg-white border border-slate-100 rounded-xl p-4 shadow-sm hover:border-slate-200 transition-all flex flex-col gap-2 relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-transparent to-transparent group-hover:from-red-400 group-hover:to-orange-400 opacity-50" />
          
          <div className="flex justify-between items-start pl-2">
            <div>
              <h4 className="text-xs font-bold text-slate-800">{t.transformer_name || t.transformer_id.substring(0, 8)}</h4>
              <p className="text-[10px] text-slate-500 mt-0.5 truncate max-w-[150px]">{t.description}</p>
            </div>
            <span className={`text-[9px] font-extrabold uppercase px-2 py-0.5 rounded flex items-center gap-1 ${
              t.priority === 'CRITICAL' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'
            }`}>
              <Wrench size={10} />
              {t.priority}
            </span>
          </div>

          <div className="flex justify-between items-center mt-2 pl-2">
            <span className="text-[10px] text-slate-400">{new Date(t.created_at).toLocaleDateString()}</span>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => handleResolve(t.id)}
                className="text-[10px] font-bold text-emerald-600 bg-emerald-50 hover:bg-emerald-100 px-2 py-1 rounded transition-colors"
              >
                RESOLVE
              </button>
              <Link href={`/dashboard/transformers/${t.transformer_id}`} className="text-primary hover:bg-blue-50 p-1 rounded">
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
