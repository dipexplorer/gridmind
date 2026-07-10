"use client";

import React, { useState, useEffect } from "react";
import { Settings, Save, AlertTriangle, Activity, Loader2, Info } from "lucide-react";
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

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get("/operations/settings");
      setSettings(res.data);
    } catch (e) {
      console.error("Failed to load settings:", e);
      setMessage({ text: "Failed to load system settings. Please try again.", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!settings) return;
    
    // Basic validation
    if (settings.critical_threshold <= settings.high_threshold || settings.high_threshold <= settings.medium_threshold) {
      setMessage({ text: "Invalid thresholds. Must be: Critical > High > Medium", type: 'error' });
      return;
    }

    try {
      setSaving(true);
      setMessage(null);
      await apiClient.put("/operations/settings", {
        critical_threshold: settings.critical_threshold,
        high_threshold: settings.high_threshold,
        medium_threshold: settings.medium_threshold,
      });
      setMessage({ text: "Settings saved successfully! New thresholds will apply to the next AI scan.", type: 'success' });
    } catch (e: any) {
      console.error("Failed to save:", e);
      setMessage({ text: e.response?.data?.detail || "Failed to save settings.", type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key: keyof SystemSettings, value: number) => {
    if (settings) {
      setSettings({ ...settings, [key]: value });
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="animate-spin text-blue-500" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-3">
          <Settings className="text-blue-600" size={32} />
          System Configuration
        </h1>
        <p className="text-slate-500 mt-2 font-medium">Manage AI parameters and global system behaviors.</p>
      </div>

      {message && (
        <div className={`p-4 rounded-xl flex items-center gap-3 border ${
          message.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-red-50 border-red-200 text-red-800'
        }`}>
          {message.type === 'success' ? <Activity size={20} /> : <AlertTriangle size={20} />}
          <span className="text-sm font-bold">{message.text}</span>
        </div>
      )}

      {/* AI Settings Card */}
      {settings && (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-100 bg-slate-50/50">
            <h2 className="text-lg font-bold text-slate-800">AI Risk Thresholds</h2>
            <p className="text-sm text-slate-500 mt-1">Configure at what anomaly scores the system triggers different risk categories and maintenance alerts.</p>
          </div>

          <div className="p-6 space-y-10">
            {/* Critical Slider */}
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-bold text-slate-700 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-red-500 shadow-sm shadow-red-500/50" />
                  Critical Risk Threshold
                </label>
                <span className="text-sm font-black text-red-600 bg-red-50 px-2 py-0.5 rounded-lg border border-red-100">
                  {settings.critical_threshold}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={settings.critical_threshold}
                onChange={(e) => handleChange("critical_threshold", parseInt(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-red-500"
              />
              <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
                <Info size={12} /> Scores above this will automatically generate an OPEN priority ticket.
              </p>
            </div>

            {/* High Slider */}
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-bold text-slate-700 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-orange-500 shadow-sm shadow-orange-500/50" />
                  High Risk Threshold
                </label>
                <span className="text-sm font-black text-orange-600 bg-orange-50 px-2 py-0.5 rounded-lg border border-orange-100">
                  {settings.high_threshold}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={settings.high_threshold}
                onChange={(e) => handleChange("high_threshold", parseInt(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
              />
            </div>

            {/* Medium Slider */}
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-bold text-slate-700 flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-amber-400 shadow-sm shadow-amber-400/50" />
                  Medium Risk Threshold
                </label>
                <span className="text-sm font-black text-amber-600 bg-amber-50 px-2 py-0.5 rounded-lg border border-amber-100">
                  {settings.medium_threshold}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={settings.medium_threshold}
                onChange={(e) => handleChange("medium_threshold", parseInt(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-500"
              />
            </div>
          </div>

          <div className="p-6 bg-slate-50/80 border-t border-slate-100 flex justify-end">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2.5 rounded-xl font-bold hover:bg-blue-700 transition-colors shadow-md shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
              Save Configuration
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
