"use client";

import React, { useState, useEffect } from "react";
import { 
  Settings, Save, AlertTriangle, Activity, Loader2, Info, 
  BrainCircuit, Bell, Database, Shield, Zap, Mail, Smartphone,
  Clock, Trash2, Power
} from "lucide-react";
import { apiClient } from "@/lib/api";

interface SystemSettings {
  id: string;
  critical_threshold: number;
  high_threshold: number;
  medium_threshold: number;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string, type: 'success' | 'error' } | null>(null);
  
  const [activeTab, setActiveTab] = useState<'notifications' | 'data' | 'system'>('notifications');

  // Mocks for UI
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [smsAlerts, setSmsAlerts] = useState(false);
  const [retention, setRetention] = useState("90");
  const [maintenanceMode, setMaintenanceMode] = useState(false);



  const handleSaveMock = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      setMessage({ text: "Preferences saved successfully!", type: 'success' });
      setTimeout(() => setMessage(null), 3000);
    }, 800);
  };



  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-3">
          <Settings className="text-blue-600" size={32} />
          Command Center Settings
        </h1>
        <p className="text-slate-500 mt-2 font-medium">Manage AI parameters, notifications, and global system behaviors.</p>
      </div>

      {message && (
        <div className={`p-4 rounded-xl flex items-center gap-3 border animate-in fade-in slide-in-from-top-2 ${
          message.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-red-50 border-red-200 text-red-800'
        }`}>
          {message.type === 'success' ? <Activity size={20} /> : <AlertTriangle size={20} />}
          <span className="text-sm font-bold">{message.text}</span>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Sidebar */}
        <div className="w-full lg:w-64 shrink-0 space-y-2">

          <button 
            onClick={() => setActiveTab('notifications')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all ${activeTab === 'notifications' ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}
          >
            <Bell size={18} /> Notifications & Alerts
          </button>
          <button 
            onClick={() => setActiveTab('data')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all ${activeTab === 'data' ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}
          >
            <Database size={18} /> Data Management
          </button>
          <button 
            onClick={() => setActiveTab('system')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold transition-all ${activeTab === 'system' ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}
          >
            <Shield size={18} /> System & Security
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1">
          


          {/* TAB: Notifications */}
          {activeTab === 'notifications' && (
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden animate-in fade-in duration-300">
              <div className="p-6 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
                <h2 className="text-lg font-bold text-slate-800">Alert Preferences</h2>
                <p className="text-sm text-slate-500">Configure how you receive system alerts.</p>
              </div>
              
              <div className="p-6 space-y-6">
                <div className="flex items-center justify-between p-4 border border-slate-200 rounded-2xl hover:border-blue-200 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-blue-50 text-blue-600 rounded-xl"><Mail size={24} /></div>
                    <div>
                      <h3 className="font-bold text-slate-800">Email Notifications</h3>
                      <p className="text-sm text-slate-500">Receive critical alerts via email.</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => setEmailAlerts(!emailAlerts)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${emailAlerts ? 'bg-blue-600' : 'bg-slate-200'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${emailAlerts ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>

                <div className="flex items-center justify-between p-4 border border-slate-200 rounded-2xl hover:border-blue-200 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-slate-50 text-slate-600 rounded-xl"><Smartphone size={24} /></div>
                    <div>
                      <h3 className="font-bold text-slate-800">SMS Alerts</h3>
                      <p className="text-sm text-slate-500">Receive text messages for server outages.</p>
                    </div>
                  </div>
                  <button 
                    onClick={() => setSmsAlerts(!smsAlerts)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${smsAlerts ? 'bg-blue-600' : 'bg-slate-200'}`}
                  >
                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${smsAlerts ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
              </div>
              
              <div className="p-6 bg-slate-50/80 border-t border-slate-100 flex justify-end">
                <button onClick={handleSaveMock} className="flex items-center gap-2 bg-slate-800 text-white px-6 py-2.5 rounded-xl font-bold hover:bg-slate-900 transition-colors">
                  Save Preferences
                </button>
              </div>
            </div>
          )}

          {/* TAB: Data Management */}
          {activeTab === 'data' && (
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden animate-in fade-in duration-300">
              <div className="p-6 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
                <h2 className="text-lg font-bold text-slate-800">Data Retention & Storage</h2>
                <p className="text-sm text-slate-500">Manage how long IoT telemetry data is kept in the database.</p>
              </div>
              
              <div className="p-6 space-y-6">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-2 flex items-center gap-2">
                    <Clock size={16} className="text-slate-400" />
                    Telemetry Retention Period
                  </label>
                  <select 
                    value={retention}
                    onChange={(e) => setRetention(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-xl p-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none"
                  >
                    <option value="30">30 Days</option>
                    <option value="90">90 Days</option>
                    <option value="365">1 Year (Requires Cold Storage)</option>
                  </select>
                </div>
                
                <div className="p-4 bg-red-50 border border-red-100 rounded-2xl flex items-start gap-4">
                  <div className="p-2 bg-white text-red-600 rounded-lg shadow-sm"><Trash2 size={20} /></div>
                  <div>
                    <h3 className="font-bold text-red-800 text-sm">Purge Old Telemetry</h3>
                    <p className="text-xs text-red-600 mt-1 mb-3">Permanently delete data older than your retention policy immediately. This cannot be undone.</p>
                    <button className="bg-red-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-sm hover:bg-red-700 transition-colors">
                      Run Purge Now
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-6 bg-slate-50/80 border-t border-slate-100 flex justify-end">
                <button onClick={handleSaveMock} className="flex items-center gap-2 bg-slate-800 text-white px-6 py-2.5 rounded-xl font-bold hover:bg-slate-900 transition-colors">
                  Update Policy
                </button>
              </div>
            </div>
          )}

          {/* TAB: System & Security */}
          {activeTab === 'system' && (
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden animate-in fade-in duration-300">
              <div className="p-6 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
                <h2 className="text-lg font-bold text-slate-800">System Mode</h2>
                <p className="text-sm text-slate-500">Control global application states.</p>
              </div>
              
              <div className="p-6">
                <div className={`p-6 border rounded-2xl transition-all ${maintenanceMode ? 'bg-amber-50 border-amber-200' : 'bg-white border-slate-200 hover:border-slate-300'}`}>
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-4">
                      <div className={`p-3 rounded-xl ${maintenanceMode ? 'bg-amber-100 text-amber-600' : 'bg-slate-100 text-slate-600'}`}>
                        <Power size={24} />
                      </div>
                      <div>
                        <h3 className={`font-bold ${maintenanceMode ? 'text-amber-800' : 'text-slate-800'}`}>Maintenance Mode</h3>
                        <p className={`text-sm mt-1 ${maintenanceMode ? 'text-amber-700' : 'text-slate-500'}`}>
                          {maintenanceMode 
                            ? "System is currently offline for operators. Only admins can log in." 
                            : "System is running normally."}
                        </p>
                      </div>
                    </div>
                    <button 
                      onClick={() => setMaintenanceMode(!maintenanceMode)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${maintenanceMode ? 'bg-amber-500' : 'bg-slate-200'}`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${maintenanceMode ? 'translate-x-6' : 'translate-x-1'}`} />
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-6 bg-slate-50/80 border-t border-slate-100 flex justify-end">
                <button onClick={handleSaveMock} className="flex items-center gap-2 bg-slate-800 text-white px-6 py-2.5 rounded-xl font-bold hover:bg-slate-900 transition-colors">
                  Apply Changes
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
