import React, { useState, useEffect } from "react";
import { api, API } from "./api";
import { Dashboard, Overview, Dataset, Health, Train, Evaluation, Live, History, Versions, Excel, Reports, About } from "./pages";
import { useToast } from "./ui";
const PROJ = [["overview", "Overview"], ["dataset", "Dataset Manager"], ["health", "Dataset Health"], ["train", "Training"], ["eval", "Evaluation"], ["live", "Live Prediction"], ["history", "Experiment History"], ["versions", "Model Versions"], ["report", "Reports"]];
export default function App() {
  const [pid, setPid] = useState(null); const [page, setPage] = useState("dashboard"); const [toast, toastEl] = useToast(); const [nav, setNav] = useState(false); const [up, setUp] = useState(null);
  useEffect(() => { let stop = false, t; const ping = () => api.ping().then(() => !stop && setUp(true)).catch(() => { if (!stop) { setUp(false); t = setTimeout(ping, 5000); } }); ping(); return () => { stop = true; clearTimeout(t); }; }, []);
  const misconfigured = import.meta.env.PROD && !API;
  const open = (id) => { setPid(id); setPage("overview"); }; const go = setPage;
  const P = { pid, toast, go };
  const view = { dashboard: <Dashboard open={open} toast={toast} />, excel: <Excel toast={toast} />, about: <About /> }[page] || (!pid ? <Dashboard open={open} toast={toast} /> : {
    overview: <Overview {...P} back={() => { setPid(null); go("dashboard"); }} />, dataset: <Dataset {...P} />, health: <Health {...P} />, train: <Train {...P} />, eval: <Evaluation {...P} />,
    live: <Live {...P} />, history: <History {...P} />, versions: <Versions {...P} />, report: <Reports {...P} /> }[page]);
  const L = ({ id, label }) => <button onClick={() => { go(id); setNav(false); }} className={`block w-full text-left px-3 py-2 rounded-lg text-sm ${page === id ? "bg-indigo-600 text-white" : "hover:bg-slate-200"}`}>{label}</button>;
  return <div className="min-h-screen md:flex">
    <aside className={`${nav ? "block" : "hidden"} md:block w-full md:w-60 bg-white border-r p-3 space-y-1`}><div className="font-bold text-indigo-700 text-lg mb-3">Smart ML Studio</div><L id="dashboard" label="Dashboard" />
      {pid && <><div className="text-xs uppercase text-slate-400 mt-3 px-3">Project #{pid}</div>{PROJ.map(([i, l]) => <L key={i} id={i} label={l} />)}</>}<div className="text-xs uppercase text-slate-400 mt-3 px-3">Tools</div><L id="excel" label="Excel Experiment Analyzer" /><L id="about" label="About / Settings" /></aside>
    <main className="flex-1"><header className="bg-white border-b px-4 py-2 flex items-center gap-3"><button className="md:hidden btn2" onClick={() => setNav(!nav)}>☰</button><span className="text-sm text-slate-500">{pid ? `Project #${pid} › ${page}` : "No project selected"}</span></header><div className="p-4">{misconfigured && <div className="mb-3 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">VITE_API_URL is not set for this build, so the app cannot find the backend. Set it in Netlify and redeploy.</div>}
      {up === false && !misconfigured && <div className="mb-3 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-sm">Backend is not responding yet. Free hosting sleeps after inactivity and can take ~1 minute to wake up; retrying automatically…</div>}{view}</div></main>{toastEl}</div>;
}
