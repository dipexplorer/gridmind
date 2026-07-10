"use client";

import React, { useEffect, useState } from "react";
import { BentoCard } from "@/components/widgets/BentoCard";
import { apiClient } from "@/lib/api";
import { Wrench, CheckCircle2, Download, Filter, Search, ShieldAlert, X } from "lucide-react";

interface Ticket {
  id: string;
  transformer_id: string;
  status: string;
  priority: string;
  description: string;
  created_at: string;
  transformer_name?: string;
  resolution_notes?: string;
  resolved_at?: string;
}

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  
  // Modal State
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [outcome, setOutcome] = useState("COMPLETED");
  const [resolving, setResolving] = useState(false);

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get("/operations/tickets");
      setTickets(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const handleResolve = async () => {
    if (!selectedTicket || !resolutionNotes) return;
    setResolving(true);
    try {
      await apiClient.post(`/operations/tickets/${selectedTicket.id}/resolve`, {
        resolution_notes: resolutionNotes,
        outcome: outcome
      });
      // Refresh list
      fetchTickets();
      setSelectedTicket(null);
      setResolutionNotes("");
    } catch (e) {
      console.error("Failed to resolve ticket", e);
    } finally {
      setResolving(false);
    }
  };

  const exportToCSV = () => {
    if (tickets.length === 0) return;
    const headers = ["Ticket ID", "Transformer ID", "Status", "Priority", "Description", "Resolution Notes", "Created At", "Resolved At"];
    const rows = tickets.map(t => [
      t.id,
      t.transformer_id,
      t.status,
      t.priority,
      `"${t.description?.replace(/"/g, '""') || ''}"`,
      `"${t.resolution_notes?.replace(/"/g, '""') || ''}"`,
      new Date(t.created_at).toLocaleString(),
      t.resolved_at ? new Date(t.resolved_at).toLocaleString() : ""
    ]);
    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `maintenance_tickets_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredTickets = tickets
    .filter(t => filter === "ALL" ? true : t.status === filter)
    .filter(t => t.description?.toLowerCase().includes(searchTerm.toLowerCase()) || t.transformer_id.toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-heading font-bold text-slate-800 tracking-tight">Maintenance Tickets</h1>
          <p className="text-sm font-medium text-slate-500 mt-1">Manage, resolve, and track AI-generated and manual repair tickets.</p>
        </div>
        <div className="flex items-center gap-3 w-full md:w-auto">
          <button onClick={exportToCSV} className="flex items-center gap-2 bg-white border border-slate-200 text-slate-700 px-4 py-2 rounded-xl text-sm font-bold shadow-sm hover:bg-slate-50 transition-colors">
            <Download size={16} /> Export CSV
          </button>
        </div>
      </div>

      <BentoCard className="min-h-[60vh] p-6">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4 mb-6">
          <div className="flex items-center bg-slate-100 p-1 rounded-xl">
            {["ALL", "OPEN", "RESOLVED"].map(f => (
              <button 
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-all ${filter === f ? "bg-white text-blue-700 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="relative w-full md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input 
              type="text" 
              placeholder="Search description or ID..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-sm rounded-xl pl-9 pr-4 py-2 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <div className="w-8 h-8 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400">
            <CheckCircle2 size={48} className="mb-4 text-emerald-500 opacity-50" />
            <p className="text-lg font-bold text-slate-600">No tickets found</p>
            <p className="text-sm">You are all caught up!</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 text-xs font-bold uppercase tracking-wider">
                  <th className="pb-3 px-2">ID & Transformer</th>
                  <th className="pb-3 px-2">Priority</th>
                  <th className="pb-3 px-2">Status</th>
                  <th className="pb-3 px-2">Description</th>
                  <th className="pb-3 px-2">Date</th>
                  <th className="pb-3 px-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 text-sm">
                {filteredTickets.map(t => (
                  <tr key={t.id} className="hover:bg-slate-50/50 transition-colors group">
                    <td className="py-4 px-2">
                      <div className="font-bold text-slate-800 font-mono text-xs">{t.id.substring(0, 8)}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{t.transformer_id.substring(0, 12)}...</div>
                    </td>
                    <td className="py-4 px-2">
                      <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded flex items-center gap-1 w-fit ${
                        t.priority === 'CRITICAL' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'
                      }`}>
                        {t.priority === 'CRITICAL' ? <ShieldAlert size={10} /> : <Wrench size={10} />}
                        {t.priority}
                      </span>
                    </td>
                    <td className="py-4 px-2">
                      <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded w-fit ${
                        t.status === 'RESOLVED' ? 'bg-emerald-50 text-emerald-600' : 'bg-blue-50 text-blue-600'
                      }`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="py-4 px-2 max-w-xs">
                      <p className="text-slate-700 truncate">{t.description}</p>
                      {t.resolution_notes && (
                        <p className="text-[10px] text-slate-500 mt-1 truncate max-w-[200px] italic">Note: {t.resolution_notes}</p>
                      )}
                    </td>
                    <td className="py-4 px-2 text-slate-500 text-xs">
                      {new Date(t.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-4 px-2 text-right">
                      {t.status === 'OPEN' ? (
                        <button 
                          onClick={() => setSelectedTicket(t)}
                          className="text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 px-3 py-1.5 rounded-lg shadow-sm transition-colors"
                        >
                          Resolve
                        </button>
                      ) : (
                        <span className="text-xs font-bold text-emerald-500 flex items-center justify-end gap-1">
                          <CheckCircle2 size={14} /> Done
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </BentoCard>

      {/* Resolution Modal */}
      {selectedTicket && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col">
            <div className="flex justify-between items-center px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h2 className="font-heading font-bold text-slate-800 text-lg">Resolve Maintenance Ticket</h2>
              <button onClick={() => setSelectedTicket(null)} className="text-slate-400 hover:text-slate-600 p-1 bg-white rounded-full hover:bg-slate-100 transition-colors">
                <X size={18} />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="bg-amber-50 border border-amber-100 p-3 rounded-xl flex gap-3">
                <Wrench className="text-amber-500 shrink-0 mt-0.5" size={16} />
                <div>
                  <p className="text-xs font-bold text-amber-900 uppercase tracking-wider mb-0.5">Ticket Context</p>
                  <p className="text-sm text-amber-800 leading-relaxed">{selectedTicket.description}</p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-2">Resolution Notes</label>
                <textarea 
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="E.g., Replaced cooling fan and filtered oil..."
                  className="w-full h-24 border border-slate-200 rounded-xl p-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-none transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-2">Outcome</label>
                <select 
                  value={outcome}
                  onChange={(e) => setOutcome(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-xl p-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none"
                >
                  <option value="COMPLETED">Completed Successfully</option>
                  <option value="REPAIRED">Repaired Component</option>
                  <option value="REPLACED">Replaced Transformer</option>
                  <option value="MONITORED">Monitored - No Action Required</option>
                </select>
              </div>
            </div>

            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
              <button 
                onClick={() => setSelectedTicket(null)}
                className="px-4 py-2 text-sm font-bold text-slate-600 hover:text-slate-800 transition-colors"
                disabled={resolving}
              >
                Cancel
              </button>
              <button 
                onClick={handleResolve}
                disabled={resolving || !resolutionNotes}
                className="px-6 py-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm hover:shadow transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {resolving ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <CheckCircle2 size={16} />
                )}
                {resolving ? "Resolving..." : "Submit Resolution"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
