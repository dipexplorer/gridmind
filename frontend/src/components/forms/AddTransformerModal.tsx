"use client";

import React, { useEffect, useState } from "react";
import { X, Zap, MapPin, Info, CheckCircle, AlertCircle, Loader } from "lucide-react";
import { apiClient } from "@/lib/api";

interface Substation { id: string; name: string; code: string; }

interface Props {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

// Field helpers
const Field = ({ label, required, children, hint }: { label: string; required?: boolean; children: React.ReactNode; hint?: string }) => (
  <div>
    <label className="block text-xs font-bold text-slate-600 uppercase tracking-wider mb-1.5">
      {label} {required && <span className="text-red-500">*</span>}
    </label>
    {children}
    {hint && <p className="text-[10px] text-slate-400 mt-1">{hint}</p>}
  </div>
);

const inputCls = "w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all";

export default function AddTransformerModal({ open, onClose, onSuccess }: Props) {
  const [substations, setSubstations] = useState<Substation[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  // Form state
  const [form, setForm] = useState({
    transformer_code: "",
    rated_kva: "",
    substation_id: "",
    feeder_id: "",
    installation_type: "POLE",
    cooling_type: "ONAN",
    manufacturer: "",
    address_text: "",
    district: "",
    block: "",
    latitude: "",
    longitude: "",
    installation_date: new Date().toISOString().slice(0, 10),
    num_consumers: "0",
    consumer_category: "MIXED",
    area_criticality: "1.0",
    operational_status: "IN_SERVICE",
    is_flood_prone: false,
    is_high_lightning: false,
  });

  useEffect(() => {
    if (open) {
      apiClient.get("/substations/").then(r => setSubstations(r.data)).catch(() => {});
      setStatus("idle");
      setErrorMsg("");
    }
  }, [open]);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const setCheck = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.checked }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMsg("");

    // Validate required
    if (!form.transformer_code || !form.rated_kva || !form.latitude || !form.longitude) {
      setStatus("error");
      setErrorMsg("Please fill in all required fields: Code, Capacity, Latitude, Longitude.");
      return;
    }

    // Build WKT location string (PostGIS format: POINT(lon lat))
    const location = `POINT(${form.longitude} ${form.latitude})`;

    const payload: Record<string, any> = {
      transformer_code:  form.transformer_code.trim().toUpperCase(),
      rated_kva:         parseFloat(form.rated_kva),
      installation_type: form.installation_type,
      cooling_type:      form.cooling_type,
      manufacturer:      form.manufacturer || null,
      address_text:      form.address_text || null,
      district:          form.district || null,
      block:             form.block || null,
      location,
      installation_date: form.installation_date,
      num_consumers:     parseInt(form.num_consumers) || 0,
      consumer_category: form.consumer_category,
      area_criticality:  parseFloat(form.area_criticality),
      operational_status: form.operational_status,
      is_flood_prone:    form.is_flood_prone,
      is_high_lightning: form.is_high_lightning,
    };
    if (form.substation_id) payload.substation_id = form.substation_id;

    try {
      await apiClient.post("/transformers/", payload);
      setStatus("success");
      setTimeout(() => { onSuccess(); onClose(); }, 1500);
    } catch (err: any) {
      setStatus("error");
      const detail = err?.response?.data?.detail;
      setErrorMsg(typeof detail === "string" ? detail : "Server error. Check transformer code for duplicates.");
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-3xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-7 py-5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-md shadow-blue-500/25">
              <Zap size={20} className="text-white" />
            </div>
            <div>
              <h2 className="font-extrabold text-slate-900 text-lg leading-tight">Add New Transformer</h2>
              <p className="text-xs text-slate-500">Fill in asset details below</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-400 hover:text-slate-700">
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-7 py-6 space-y-6">

          {/* Section: Asset Identity */}
          <Section title="Asset Identity" icon={<Zap size={14} />}>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Transformer Code" required hint="e.g. TRF_GHY_101">
                <input className={inputCls} placeholder="TRF_GHY_101" value={form.transformer_code} onChange={set("transformer_code")} />
              </Field>
              <Field label="Capacity (kVA)" required>
                <input className={inputCls} type="number" min={1} placeholder="250" value={form.rated_kva} onChange={set("rated_kva")} />
              </Field>
              <Field label="Installation Type">
                <select className={inputCls} value={form.installation_type} onChange={set("installation_type")}>
                  <option>POLE</option>
                  <option>PAD</option>
                  <option>GROUND</option>
                  <option>UNKNOWN</option>
                </select>
              </Field>
              <Field label="Cooling Type">
                <select className={inputCls} value={form.cooling_type} onChange={set("cooling_type")}>
                  <option>ONAN</option>
                  <option>ONAF</option>
                  <option>OFWF</option>
                </select>
              </Field>
              <Field label="Manufacturer">
                <input className={inputCls} placeholder="e.g. BHEL, Siemens" value={form.manufacturer} onChange={set("manufacturer")} />
              </Field>
              <Field label="Installation Date" required>
                <input className={inputCls} type="date" value={form.installation_date} onChange={set("installation_date")} />
              </Field>
            </div>
          </Section>

          {/* Section: Location */}
          <Section title="GPS Location" icon={<MapPin size={14} />}>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Latitude" required hint="e.g. 26.1445 (Guwahati range: 25.8–26.5)">
                <input className={inputCls} type="number" step="any" placeholder="26.1445" value={form.latitude} onChange={set("latitude")} />
              </Field>
              <Field label="Longitude" required hint="e.g. 91.7362 (Guwahati range: 91.0–92.5)">
                <input className={inputCls} type="number" step="any" placeholder="91.7362" value={form.longitude} onChange={set("longitude")} />
              </Field>
              <Field label="Address / Location Text">
                <input className={inputCls} placeholder="Near City Centre, GHY" value={form.address_text} onChange={set("address_text")} />
              </Field>
              <Field label="District">
                <input className={inputCls} placeholder="Kamrup Metropolitan" value={form.district} onChange={set("district")} />
              </Field>
              <Field label="Block">
                <input className={inputCls} placeholder="Dispur" value={form.block} onChange={set("block")} />
              </Field>
              <Field label="Substation">
                <select className={inputCls} value={form.substation_id} onChange={set("substation_id")}>
                  <option value="">-- Select Substation --</option>
                  {substations.map(s => (
                    <option key={s.id} value={s.id}>{s.name} ({s.code})</option>
                  ))}
                </select>
              </Field>
            </div>
          </Section>

          {/* Section: Operational Info */}
          <Section title="Operational Info" icon={<Info size={14} />}>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Consumers">
                <input className={inputCls} type="number" min={0} value={form.num_consumers} onChange={set("num_consumers")} />
              </Field>
              <Field label="Consumer Category">
                <select className={inputCls} value={form.consumer_category} onChange={set("consumer_category")}>
                  <option>MIXED</option>
                  <option>RESIDENTIAL</option>
                  <option>COMMERCIAL</option>
                  <option>INDUSTRIAL</option>
                  <option>AGRICULTURAL</option>
                </select>
              </Field>
              <Field label="Operational Status">
                <select className={inputCls} value={form.operational_status} onChange={set("operational_status")}>
                  <option value="IN_SERVICE">IN_SERVICE</option>
                  <option value="OUT_OF_SERVICE">OUT_OF_SERVICE</option>
                </select>
              </Field>
            </div>
            <div className="flex items-center gap-6 mt-3">
              {[
                { key: "is_flood_prone", label: "🌊 Flood-Prone Area" },
                { key: "is_high_lightning", label: "⚡ High Lightning Risk" },
              ].map(cb => (
                <label key={cb.key} className="flex items-center gap-2 cursor-pointer select-none group">
                  <input
                    type="checkbox"
                    checked={(form as any)[cb.key]}
                    onChange={setCheck(cb.key)}
                    className="w-4 h-4 rounded accent-blue-600 cursor-pointer"
                  />
                  <span className="text-sm font-medium text-slate-600 group-hover:text-slate-800 transition-colors">{cb.label}</span>
                </label>
              ))}
            </div>
          </Section>

          {/* Status feedback */}
          {status === "error" && (
            <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-2xl p-4 text-red-700 text-sm">
              <AlertCircle size={18} className="flex-shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}
          {status === "success" && (
            <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-emerald-700 text-sm font-semibold">
              <CheckCircle size={18} />
              Transformer added successfully! Refreshing...
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-7 py-4 border-t border-slate-100 bg-slate-50/50">
          <button type="button" onClick={onClose}
            className="px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={status === "loading" || status === "success"}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/20 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {status === "loading" ? <><Loader size={16} className="animate-spin" /> Saving…</> : "Add Transformer"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <div className="text-blue-600">{icon}</div>
        <h3 className="text-sm font-extrabold text-slate-700 uppercase tracking-wider">{title}</h3>
        <div className="flex-1 h-px bg-slate-100 ml-2" />
      </div>
      {children}
    </div>
  );
}
