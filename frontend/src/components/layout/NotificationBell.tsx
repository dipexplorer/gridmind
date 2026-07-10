"use client";

import React, { useState, useEffect, useRef } from "react";
import { Bell, AlertTriangle, ShieldAlert, X, ChevronRight, Zap } from "lucide-react";
import Link from "next/link";
import { apiClient } from "@/lib/api";

interface Alert {
  id: string;
  transformer_id: string;
  severity: string;
  message: string;
  created_at: string;
}

export function NotificationBell() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch alerts function
  const fetchAlerts = async () => {
    try {
      const res = await apiClient.get("/operations/alerts?unacknowledged_only=true");
      setAlerts(res.data);
    } catch (e) {
      console.error("Failed to fetch alerts", e);
    }
  };

  useEffect(() => {
    fetchAlerts();

    // Setup WebSocket
    let ws: WebSocket;
    const connectWS = async () => {
      try {
        const { supabase } = await import("@/lib/supabaseClient");
        const { data: { session } } = await supabase.auth.getSession();
        if (!session?.access_token) return;

        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
        const wsUrl = API_URL.replace("http://", "ws://").replace("https://", "wss://") + `/ws/notifications?token=${session.access_token}`;
        
        ws = new WebSocket(wsUrl);
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "NEW_ALERT") {
              setAlerts(prev => [data.alert, ...prev]);
            }
          } catch(e) {
            console.error("WS Parse error", e);
          }
        };

        ws.onclose = () => {
          console.log("WS closed, attempting reconnect in 5s");
          setTimeout(connectWS, 5000);
        };
      } catch (e) {
        console.error("WS setup failed", e);
      }
    };

    connectWS();

    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const hasUnread = alerts.length > 0;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className={`relative w-9 h-9 rounded-full flex items-center justify-center transition-all ${
          isOpen ? "bg-blue-50 text-blue-600" : "bg-slate-50 text-slate-500 hover:bg-slate-100"
        }`}
      >
        <Bell size={18} />
        {hasUnread && (
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 border border-white rounded-full animate-pulse" />
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-3 w-80 sm:w-96 bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden z-50 animate-in fade-in slide-in-from-top-4 duration-200 origin-top-right">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-50 bg-slate-50/50">
            <h3 className="font-extrabold text-slate-800 text-sm">Notifications</h3>
            {hasUnread && (
              <span className="text-[10px] font-bold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                {alerts.length} New
              </span>
            )}
          </div>
          
          <div className="max-h-[350px] overflow-y-auto p-2 custom-scrollbar">
            {!hasUnread ? (
              <div className="py-8 text-center text-slate-400">
                <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Bell size={20} className="opacity-50" />
                </div>
                <p className="text-sm font-semibold">You're all caught up!</p>
                <p className="text-xs mt-1">No critical alerts detected.</p>
              </div>
            ) : (
              <div className="space-y-1">
                {alerts.map(alert => (
                  <Link 
                    href={`/dashboard/transformers/${alert.transformer_id}`}
                    key={alert.id}
                    onClick={() => setIsOpen(false)}
                    className="flex items-start gap-3 p-3 rounded-2xl hover:bg-slate-50 transition-colors group relative"
                  >
                    <div className={`p-2 rounded-xl flex-shrink-0 mt-0.5 ${
                      alert.severity === "CRITICAL" ? "bg-red-50 text-red-600" : "bg-amber-50 text-amber-600"
                    }`}>
                      {alert.severity === "CRITICAL" ? <ShieldAlert size={16} /> : <AlertTriangle size={16} />}
                    </div>
                    <div className="flex-1 min-w-0 pr-6">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-slate-800 truncate">{alert.message.split(":")[0]}</span>
                        <span className={`text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded ${
                          alert.severity === "CRITICAL" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                        }`}>
                          {alert.severity}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                        {alert.message.split(":").slice(1).join(":") || alert.message}
                      </p>
                      <p className="text-[9px] font-semibold text-slate-400 mt-1.5">
                        {new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {new Date(alert.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <ChevronRight size={14} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-300 opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0" />
                  </Link>
                ))}
              </div>
            )}
          </div>
          
          {hasUnread && (
            <div className="px-5 py-3 border-t border-slate-50 bg-slate-50/80 text-center">
              <button 
                onClick={fetchAlerts}
                className="text-xs font-bold text-blue-600 hover:text-blue-700 transition-colors flex items-center justify-center gap-1 mx-auto"
              >
                <Zap size={12} /> Sync Latest
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
