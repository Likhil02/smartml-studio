import React, { useState, useEffect, useCallback } from "react";
export const Spinner = () => <div className="p-6 text-slate-500 animate-pulse">Loading…</div>;
export const Empty = ({ children }) => <div className="card text-center text-slate-500 py-10">{children}</div>;
export const ErrorBox = ({ error }) => error ? <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 p-3 text-sm mb-3">{error}</div> : null;
export const Badge = ({ color = "slate", children }) => <span className={`px-2 py-0.5 rounded-full text-xs font-medium bg-${color}-100 text-${color}-700`}>{children}</span>;
export const Stat = ({ label, value, sub }) => <div className="card"><div className="text-xs text-slate-500">{label}</div><div className="text-2xl font-semibold">{value ?? "—"}</div>{sub && <div className="text-xs text-slate-400">{sub}</div>}</div>;
export const Modal = ({ title, onClose, children }) => <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"><div className="bg-white rounded-xl p-5 w-full max-w-md"><div className="flex justify-between mb-3"><b>{title}</b><button onClick={onClose}>✕</button></div>{children}</div></div>;
export const pct = (x) => x == null ? "—" : (x * 100).toFixed(1) + "%";
export const fix = (x, d = 3) => x == null ? "—" : Number(x).toFixed(d);
export function useToast() {
  const [t, setT] = useState(null);
  useEffect(() => { if (t) { const i = setTimeout(() => setT(null), 3500); return () => clearTimeout(i); } }, [t]);
  const el = t && <div className={`fixed bottom-4 right-4 z-50 px-4 py-2 rounded-lg text-white ${t.err ? "bg-red-600" : "bg-emerald-600"}`}>{t.msg}</div>;
  return [(msg, err) => setT({ msg, err }), el];
}
export function useLoad(fn, deps) {
  const [s, set] = useState({ data: null, error: null, loading: true });
  const reload = useCallback(() => { set((x) => ({ ...x, loading: true })); fn().then((data) => set({ data, error: null, loading: false })).catch((e) => set({ data: null, error: e.message, loading: false })); }, deps);
  useEffect(reload, [reload]);
  return { ...s, reload };
}
