import React, { useState, useRef, useEffect } from "react";
import { LineChart, Line, BarChart, Bar, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { api, imgUrl, apiUrl } from "./api";
import { Spinner, Empty, ErrorBox, Badge, Stat, Modal, pct, fix, useLoad } from "./ui";

export function Dashboard({ open, toast }) {
  const { data, error, loading, reload } = useLoad(api.projects, []); const [m, setM] = useState(false); const [f, setF] = useState({ name: "", description: "" });
  const create = async () => { try { const p = await api.createProject(f); setM(false); toast("Project created"); open(p.id); } catch (e) { toast(e.message, true); } };
  return <div><div className="flex justify-between mb-4"><h1 className="text-xl font-semibold">Dashboard</h1><button className="btn" onClick={() => setM(true)}>+ New Project</button></div>
    <ErrorBox error={error} />{loading ? <Spinner /> : !data?.length ? <Empty>No projects yet. Create your first project.</Empty> :
      <div className="grid md:grid-cols-3 gap-4">{data.map((p) => <div key={p.id} className="card cursor-pointer hover:border-indigo-400" onClick={() => open(p.id)}>
        <div className="font-semibold">{p.name}</div><div className="text-sm text-slate-500 mb-2">{p.description}</div>
        <div className="flex gap-2"><Badge>{p.classes} classes</Badge><Badge>{p.images} images</Badge><Badge color="indigo">{p.versions} models</Badge></div></div>)}</div>}
    {m && <Modal title="Create Project" onClose={() => setM(false)}><input className="inp mb-2" placeholder="Project name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
      <textarea className="inp mb-3" placeholder="Description" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /><button className="btn" disabled={!f.name.trim()} onClick={create}>Create</button></Modal>}</div>;
}

export function Overview({ pid, go, toast, back }) {
  const { data: p, error, loading } = useLoad(() => api.project(pid), [pid]); const { data: v } = useLoad(() => api.versions(pid), [pid]);
  if (loading) return <Spinner />; if (error) return <ErrorBox error={error} />;
  const n = p.classes.reduce((a, c) => a + c.images.length, 0); const best = v?.length ? Math.max(...v.map((x) => x.accuracy)) : null;
  const del = async () => { if (confirm("Delete this project and all its data?")) { await api.deleteProject(pid); toast("Project deleted"); back(); } };
  return <div><h1 className="text-xl font-semibold">{p.name}</h1><p className="text-slate-500 mb-4">{p.description}</p>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4"><Stat label="Classes" value={p.classes.length} /><Stat label="Images" value={n} /><Stat label="Model versions" value={v?.length ?? 0} /><Stat label="Best accuracy" value={pct(best)} /></div>
    <div className="flex gap-2 flex-wrap"><button className="btn" onClick={() => go("dataset")}>Manage dataset</button><button className="btn2" onClick={() => go("health")}>Dataset health</button><button className="btn2" onClick={() => go("train")}>Train</button><button className="btn2" onClick={del}>Delete project</button></div></div>;
}

export function Dataset({ pid, toast }) {
  const { data: p, error, loading, reload } = useLoad(() => api.project(pid), [pid]); const [name, setName] = useState(""); const [busy, setBusy] = useState(false);
  const run = async (fn, ok) => { try { await fn(); ok && toast(ok); reload(); } catch (e) { toast(e.message, true); } };
  const up = async (cid, files) => { setBusy(true); try { const r = await api.upload(cid, files); toast(`${r.saved} uploaded${r.errors.length ? `, ${r.errors.length} rejected: ${r.errors[0]}` : ""}`, r.errors.length > 0 && r.saved === 0); reload(); } catch (e) { toast(e.message, true); } setBusy(false); };
  if (loading) return <Spinner />; if (error) return <ErrorBox error={error} />;
  return <div><h1 className="text-xl font-semibold mb-3">Dataset Manager</h1>
    <div className="flex gap-2 mb-4 max-w-2xl"><input className="inp" placeholder="New class name" value={name} onChange={(e) => setName(e.target.value)} /><button className="btn" disabled={!name.trim()} onClick={() => run(async () => { await api.addClass(pid, name); setName(""); }, "Class added")}>Add class</button><button className="btn2 whitespace-nowrap" title="Synthetic shapes dataset bundled with the app" onClick={() => run(async () => { const r = await api.loadSample(pid); toast(`Loaded ${r.saved} sample images (${r.classes.join(", ")})`); }, null)}>Load sample dataset</button></div>
    {!p.classes.length && <Empty>Add at least two classes, then upload images.</Empty>}
    <div className="grid lg:grid-cols-2 gap-4">{p.classes.map((c) => <div key={c.id} className="card" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); up(c.id, e.dataTransfer.files); }}>
      <div className="flex justify-between items-center mb-2"><b>{c.name} <Badge>{c.images.length}</Badge></b><div className="flex gap-2 text-sm">
        <button className="btn2" onClick={() => { const n = prompt("Rename class", c.name); if (n) run(() => api.renameClass(c.id, n), "Renamed"); }}>Rename</button>
        <button className="btn2" onClick={() => confirm(`Delete class ${c.name}?`) && run(() => api.deleteClass(c.id), "Class deleted")}>Delete</button></div></div>
      <label className="block border-2 border-dashed rounded-lg p-3 text-center text-sm text-slate-500 cursor-pointer mb-2">{busy ? "Uploading…" : "Drop images here or click to upload"}
        <input type="file" multiple accept=".jpg,.jpeg,.png,.bmp,.webp" className="hidden" onChange={(e) => { up(c.id, e.target.files); e.target.value = ""; }} /></label>
      <div className="grid grid-cols-5 gap-1 max-h-60 overflow-auto">{c.images.map((i) => <div key={i.id} className="relative group"><img src={imgUrl(i.id)} loading="lazy" className="aspect-square object-cover rounded" />
        <button className="absolute top-0 right-0 bg-red-600 text-white text-xs px-1 rounded hidden group-hover:block" onClick={() => run(() => api.deleteImage(i.id))}>✕</button></div>)}</div></div>)}</div></div>;
}

export function Health({ pid }) {
  const hasPid = pid != null && pid !== "" && !Number.isNaN(Number(pid));
  const { data: h, error, loading } = useLoad(() => hasPid ? api.datasetHealth(pid) : Promise.resolve(null), [pid]); const { data: sp } = useLoad(() => hasPid ? api.split(pid, 0.7).catch(() => null) : Promise.resolve(null), [pid]);
  if (!hasPid) return <Empty>Select or create a project first.</Empty>;
  if (loading) return <Spinner />; if (error) return <ErrorBox error={error} />;
  const bar = Object.entries(h.per_class).map(([name, count]) => ({ name, count }));
  return <div><h1 className="text-xl font-semibold mb-3">Dataset Health</h1>
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4"><Stat label="Health score" value={`${h.score}/100`} sub={h.grade} /><Stat label="Images" value={h.total_images} /><Stat label="Balance ratio" value={h.balance} /><Stat label="Avg size" value={`${h.avg_width}×${h.avg_height}`} sub={`${h.avg_file_kb} KB`} />{sp && <Stat label="Split tr/val/test" value={`${sp.train}/${sp.val}/${sp.test}`} />}</div>
    <div className="grid md:grid-cols-2 gap-4"><div className="card"><b>Images per class</b><ResponsiveContainer height={220}><BarChart data={bar}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#6366f1" /></BarChart></ResponsiveContainer></div>
      <div className="card"><b>Findings</b><ul className="text-sm mt-2 space-y-1">{[["Invalid", h.invalid], ["Very small", h.small], ["Blurry", h.blurry], ["Dark", h.dark], ["Bright", h.bright], ["Duplicate pairs", h.duplicates]].map(([k, v]) => <li key={k} className="flex justify-between"><span>{k}</span><Badge color={v.length ? "amber" : "emerald"}>{v.length}</Badge></li>)}</ul>
        <b className="block mt-3">Recommendations</b><ul className="list-disc ml-5 text-sm">{h.recommendations.map((r, i) => <li key={i}>{r}</li>)}</ul></div></div></div>;
}

const Opt = (arr) => arr.map((x) => <option key={x}>{x}</option>);
export function Train({ pid, toast }) {
  const [cfg, setCfg] = useState({ epochs: 5, batch_size: 16, learning_rate: 0.001, augmentation: true, early_stopping: true, patience: 3, seed: 42, train_ratio: 0.7 });
  const [pc, setPc] = useState(null); useEffect(() => { api.config().then((c) => { setPc(c); setCfg((x) => ({ ...x, ...c.defaults })); }).catch(() => {}); }, []);
  const fl = (k, arr) => arr.filter((p) => !pc?.demo_mode || !(pc[k === "epochs" ? "max_epochs" : "max_batch_size"]) || p <= pc[k === "epochs" ? "max_epochs" : "max_batch_size"]);
  const [rid, setRid] = useState(null); const [st, setSt] = useState(null);
  const set = (k, v) => setCfg({ ...cfg, [k]: v });
  useEffect(() => { if (!rid) return; const f = () => api.status(rid).then(setSt).catch((e) => toast(e.message, true)); f(); const i = setInterval(() => { f(); }, 1500); return () => clearInterval(i); }, [rid]);
  useEffect(() => { if (st && st.status !== "running") setRid(null); }, [st?.status]);
  const start = async () => { try { setSt(null); const r = await api.train(pid, cfg); setRid(r.run_id); toast("Training started"); } catch (e) { toast(e.message, true); } };
  const num = (k, presets) => <div><select className="inp mb-1" value={presets.includes(cfg[k]) ? cfg[k] : "custom"} onChange={(e) => e.target.value !== "custom" && set(k, Number(e.target.value))}>{Opt(presets)}<option value="custom">Custom…</option></select><input className="inp" type="number" step="any" value={cfg[k]} onChange={(e) => set(k, Number(e.target.value))} /></div>;
  const running = st?.status === "running";
  return <div><h1 className="text-xl font-semibold mb-3">Training</h1>
    {pc && <div className={`mb-3 text-sm p-3 rounded-lg border ${pc.demo_mode ? "bg-amber-50 border-amber-200 text-amber-900" : "bg-emerald-50 border-emerald-200 text-emerald-900"}`}><b>{pc.mode}</b> · image size {pc.img_size}px. {pc.demo_mode ? `Free-tier CPU server: max ${pc.max_epochs} epochs, batch ≤ ${pc.max_batch_size}, ${pc.max_images} images per project, one training run at a time. Data is temporary. For large-scale training run the project locally.` : "No demo limits: use larger epochs, batch sizes and datasets (CPU speed depends on your machine)."}</div>}
    <div className="card grid md:grid-cols-4 gap-3 mb-4">
      <label className="text-sm">Model<select className="inp" disabled><option>MobileNetV2 (transfer learning)</option></select></label>
      <label className="text-sm">Epochs{num("epochs", fl("epochs", [5, 10, 25, 50, 100]))}</label><label className="text-sm">Batch size{num("batch_size", fl("batch_size", [16, 32, 64, 128, 256, 512]))}</label>
      <label className="text-sm">Learning rate{num("learning_rate", [0.1, 0.01, 0.001, 0.0001, 0.00001])}</label>
      <label className="text-sm">Patience<input className="inp" type="number" value={cfg.patience} onChange={(e) => set("patience", Number(e.target.value))} /></label>
      <label className="text-sm">Random seed<input className="inp" type="number" value={cfg.seed} onChange={(e) => set("seed", Number(e.target.value))} /></label>
      <label className="text-sm">Train ratio (rest split val/test)<input className="inp" type="number" step="0.05" min="0.5" max="0.9" value={cfg.train_ratio} onChange={(e) => set("train_ratio", Number(e.target.value))} /></label>
      <div className="text-sm space-y-1 pt-5"><label className="block"><input type="checkbox" checked={cfg.augmentation} onChange={(e) => set("augmentation", e.target.checked)} /> Augmentation</label><label className="block"><input type="checkbox" checked={cfg.early_stopping} onChange={(e) => set("early_stopping", e.target.checked)} /> Early stopping</label></div>
      <div className="md:col-span-4 flex gap-2"><button className="btn" disabled={running} onClick={start}>Start training</button>{running && <button className="btn2" onClick={() => api.cancel(rid).then(() => toast("Cancelling after current epoch"))}>Cancel</button>}</div></div>
    {st && <div><div className="card mb-4"><div className="flex justify-between"><b>Run #{st.id} <Badge color={st.status === "completed" ? "emerald" : st.status === "failed" ? "red" : "indigo"}>{st.status}</Badge></b><span className="text-sm">Epoch {st.current_epoch}/{st.total_epochs} · {fix(st.elapsed, 0)}s{st.eta != null && ` · ETA ${fix(st.eta, 0)}s`}</span></div>
      <div className="h-2 bg-slate-200 rounded mt-2"><div className="h-2 bg-indigo-600 rounded" style={{ width: `${(st.current_epoch / st.total_epochs) * 100}%` }} /></div><ErrorBox error={st.error} />
      {st.overfitting && <div className={`mt-3 text-sm p-2 rounded ${st.overfitting.overfitting ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-800"}`}>{st.overfitting.warnings.join(" ")}</div>}</div>
      <div className="grid md:grid-cols-2 gap-4">{[["Accuracy vs Epoch", "acc", "val_acc"], ["Loss vs Epoch", "loss", "val_loss"]].map(([t, a, b]) => <div key={t} className="card"><b>{t}</b><ResponsiveContainer height={240}><LineChart data={st.history}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="epoch" /><YAxis /><Tooltip /><Legend /><Line dataKey={a} name="train" stroke="#6366f1" dot={false} /><Line dataKey={b} name="validation" stroke="#f59e0b" dot={false} /></LineChart></ResponsiveContainer></div>)}</div></div>}</div>;
}

export function Evaluation({ pid }) {
  const { data: v, error, loading } = useLoad(() => api.versions(pid), [pid]);
  if (loading) return <Spinner />; if (error) return <ErrorBox error={error} />; if (!v.length) return <Empty>No trained model yet. Train one first.</Empty>;
  const e = v[0].evaluation; const mx = Math.max(1, ...e.confusion_matrix.flat());
  return <div><h1 className="text-xl font-semibold mb-3">Model Evaluation <Badge color="indigo">v{v[0].version}</Badge></h1>
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4"><Stat label="Accuracy" value={pct(e.accuracy)} /><Stat label="Precision (weighted)" value={pct(e.precision)} /><Stat label="Recall (weighted)" value={pct(e.recall)} /><Stat label="F1 (weighted)" value={pct(e.f1)} /><Stat label="Test samples" value={e.test_samples} /></div>
    <div className="grid md:grid-cols-2 gap-4"><div className="card overflow-auto"><b>Confusion matrix (rows=actual, cols=predicted)</b><table className="mt-2 text-sm"><thead><tr><th></th>{e.classes.map((c) => <th key={c} className="px-2">{c}</th>)}</tr></thead><tbody>{e.confusion_matrix.map((r, i) => <tr key={i}><th className="pr-2 text-right">{e.classes[i]}</th>{r.map((c, j) => <td key={j} className="w-14 h-10 text-center border" style={{ background: `rgba(99,102,241,${c / mx})`, color: c / mx > 0.5 ? "#fff" : "#000" }}>{c}</td>)}</tr>)}</tbody></table></div>
      <div className="card overflow-auto"><b>Per-class metrics</b><table className="w-full text-sm mt-2"><thead><tr className="text-left"><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead><tbody>{e.per_class.map((c) => <tr key={c.class}><td>{c.class}</td><td>{fix(c.precision)}</td><td>{fix(c.recall)}</td><td>{fix(c.f1)}</td><td>{c.support}</td></tr>)}</tbody></table></div></div>
    <div className="card mt-4"><b>Classification report</b><pre className="text-xs mt-2 overflow-auto">{e.report}</pre></div></div>;
}

export function Live({ pid, toast }) {
  const [res, setRes] = useState(null); const [img, setImg] = useState(null); const [cam, setCam] = useState(false); const vid = useRef(); const stream = useRef(); const timer = useRef(); const busy = useRef(false);
  const show = (r) => setRes(r); const fail = (e) => { toast(e.message, true); stop(); };
  const onFile = async (f) => { if (!f) return; setImg(URL.createObjectURL(f)); try { show(await api.predict(pid, f)); } catch (e) { toast(e.message, true); } };
  const grab = () => new Promise((ok) => { const c = document.createElement("canvas"); const v = vid.current; c.width = v.videoWidth; c.height = v.videoHeight; c.getContext("2d").drawImage(v, 0, 0); c.toBlob(ok, "image/jpeg", 0.9); });
  const start = async () => { try { stream.current = await navigator.mediaDevices.getUserMedia({ video: true }); vid.current.srcObject = stream.current; await vid.current.play(); setCam(true);
    timer.current = setInterval(async () => { if (busy.current) return; busy.current = true; try { show(await api.predict(pid, await grab())); } catch (e) { fail(e); } busy.current = false; }, 1000); } catch (e) { toast("Camera unavailable: " + e.message, true); } };
  const stop = () => { clearInterval(timer.current); stream.current?.getTracks().forEach((t) => t.stop()); setCam(false); };
  useEffect(() => stop, []);
  const probs = res ? Object.entries(res.probabilities).map(([name, p]) => ({ name, p })).sort((a, b) => b.p - a.p) : [];
  return <div><h1 className="text-xl font-semibold mb-3">Live Prediction</h1><div className="grid md:grid-cols-2 gap-4"><div className="card"><b>Input</b>
    <video ref={vid} muted playsInline className={`w-full rounded mt-2 ${cam ? "" : "hidden"}`} />{!cam && img && <img src={img} className="w-full rounded mt-2" />}
    <div className="flex gap-2 mt-2"><button className="btn" onClick={start} disabled={cam}>Start camera</button><button className="btn2" onClick={stop} disabled={!cam}>Stop camera</button><label className="btn2 cursor-pointer">Upload image<input type="file" accept="image/*" className="hidden" onChange={(e) => onFile(e.target.files[0])} /></label></div>
    <p className="text-xs text-slate-500 mt-2">Webcam frames are captured in the browser and sent to the backend about once per second.</p></div>
    <div className="card"><b>Prediction</b>{!res ? <p className="text-slate-500 mt-2">No prediction yet.</p> : <div className="mt-2"><div className="text-3xl font-semibold">{res.predicted}</div><div className="text-slate-500">Confidence {pct(res.confidence)} · model v{res.model_version}</div>
      <div className="mt-3 space-y-2">{probs.map((x) => <div key={x.name}><div className="flex justify-between text-sm"><span>{x.name}</span><span>{pct(x.p)}</span></div><div className="h-2 bg-slate-200 rounded"><div className="h-2 bg-indigo-600 rounded" style={{ width: pct(x.p) }} /></div></div>)}</div></div>}</div></div></div>;
}

export function History({ pid }) {
  const { data, error, loading } = useLoad(() => api.experiments(pid), [pid]); const [key, setKey] = useState("accuracy"); const [q, setQ] = useState("");
  if (loading) return <Spinner />; if (error) return <ErrorBox error={error} />; if (!data.length) return <Empty>No completed experiments yet.</Empty>;
  const rows = data.filter((r) => !q || String(r.learning_rate).includes(q) || String(r.batch_size).includes(q) || String(r.epochs).includes(q)).sort((a, b) => (b[key] ?? 0) - (a[key] ?? 0)); const best = Math.max(...data.map((r) => r.accuracy));
  return <div><h1 className="text-xl font-semibold mb-3">Experiment History</h1><div className="flex gap-2 mb-3 max-w-md"><input className="inp" placeholder="Filter by epoch / batch / LR" value={q} onChange={(e) => setQ(e.target.value)} /></div>
    <div className="card overflow-auto"><table className="w-full text-sm"><thead><tr className="text-left">{[["version", "Model"], ["epochs", "Epoch"], ["batch_size", "Batch"], ["learning_rate", "LR"], ["accuracy", "Accuracy"], ["val_acc", "Val Acc"], ["loss", "Loss"], ["f1", "F1"], ["created_at", "Date"]].map(([k, l]) => <th key={k} className="cursor-pointer p-1" onClick={() => setKey(k)}>{l}{key === k && " ▼"}</th>)}</tr></thead>
      <tbody>{rows.map((r) => <tr key={r.version} className={r.accuracy === best ? "bg-emerald-50 font-medium" : ""}><td className="p-1">v{r.version}{r.accuracy === best && " ★"}</td><td>{r.epochs}</td><td>{r.batch_size}</td><td>{r.learning_rate}</td><td>{pct(r.accuracy)}</td><td>{pct(r.val_acc)}</td><td>{fix(r.loss)}</td><td>{fix(r.f1)}</td><td>{r.created_at}</td></tr>)}</tbody></table></div></div>;
}

export function Versions({ pid }) {
  const { data, error, loading } = useLoad(() => api.versions(pid), [pid]); const [sel, setSel] = useState([]);
  if (loading) return <Spinner />; if (error) return <ErrorBox error={error} />; if (!data.length) return <Empty>No model versions yet.</Empty>;
  const cmp = data.filter((v) => sel.includes(v.version)).map((v) => ({ name: `v${v.version}`, Accuracy: v.accuracy, Precision: v.precision, Recall: v.recall, F1: v.f1 }));
  return <div><h1 className="text-xl font-semibold mb-3">Model Versions</h1><div className="card overflow-auto mb-4"><table className="w-full text-sm"><thead><tr className="text-left"><th>Compare</th><th>Version</th><th>Samples</th><th>Epochs</th><th>Batch</th><th>LR</th><th>Acc</th><th>F1</th><th>Date</th><th>Export</th></tr></thead>
    <tbody>{data.map((v) => <tr key={v.version}><td><input type="checkbox" checked={sel.includes(v.version)} onChange={(e) => setSel(e.target.checked ? [...sel, v.version] : sel.filter((x) => x !== v.version))} /></td><td>v{v.version}</td><td>{v.dataset.train + v.dataset.val + v.dataset.test}</td><td>{v.epochs}</td><td>{v.batch_size}</td><td>{v.learning_rate}</td><td>{pct(v.accuracy)}</td><td>{fix(v.f1)}</td><td>{v.created_at}</td><td><a className="text-indigo-600 underline" href={apiUrl(`/api/projects/${pid}/model-versions/${v.version}/export`)}>.keras</a></td></tr>)}</tbody></table></div>
    {cmp.length > 1 && <div className="card"><b>Comparison</b><ResponsiveContainer height={260}><BarChart data={cmp}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis domain={[0, 1]} /><Tooltip /><Legend />{["Accuracy", "Precision", "Recall", "F1"].map((k, i) => <Bar key={k} dataKey={k} fill={["#6366f1", "#10b981", "#f59e0b", "#ef4444"][i]} />)}</BarChart></ResponsiveContainer></div>}</div>;
}

export function Excel({ toast }) {
  const [eid, setEid] = useState(null); const [d, setD] = useState(null); const [f, setF] = useState({}); const [err, setErr] = useState(null); const [busy, setBusy] = useState(false);
  const fetchView = (id, flt) => { const qs = new URLSearchParams(Object.entries(flt).filter(([, v]) => v !== "" && v != null)).toString(); return api.excelGet(id, qs).then(setD).catch((e) => setErr(e.message)); };
  useEffect(() => { api.excelLatest().then((r) => { if (r.experiment_id) { setEid(r.experiment_id); fetchView(r.experiment_id, {}); } }).catch(() => {}); }, []);
  const up = async (file) => { setBusy(true); setErr(null); try { const r = await api.excelUpload(file); setEid(r.experiment_id); setF({}); setD(r); toast("Workbook analysed"); } catch (e) { setErr(e.message); } setBusy(false); };
  const chg = (k, v) => { const n = { ...f, [k]: v }; setF(n); fetchView(eid, n); };
  const S = d?.summary; const C = d?.charts;
  const line = (t, data, xl, ds = "y", color = "#6366f1") => <div className="card" key={t}><b>{t}</b><ResponsiveContainer height={220}><LineChart data={data}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="x" scale="point" type="category" /><YAxis /><Tooltip /><Line dataKey={ds} stroke={color} /></LineChart></ResponsiveContainer></div>;
  const R = (r) => r && `Sheet ${r.sheet} · sample ${r.sample} · epoch ${r.epoch} · batch ${r.batch_size} · LR ${r.learning_rate} · test acc ${r.test_acc}`;
  return <div><h1 className="text-xl font-semibold mb-3">Excel Experiment Analyzer</h1><ErrorBox error={err} />
    <label className="btn cursor-pointer inline-block mb-4">{busy ? "Analysing…" : "Upload .xlsx workbook"}<input type="file" accept=".xlsx" className="hidden" onChange={(e) => e.target.files[0] && up(e.target.files[0])} /></label>
    {!d ? <Empty>Upload an experiment workbook (sheets with Sample / Epoch / Batch Size / Learning Rate / Accuracy columns).</Empty> : <div className="space-y-4">
      {d.warnings.map((w) => <ErrorBox key={w} error={w} />)}
      <div className="card grid md:grid-cols-4 gap-2">{["sample", "epoch", "batch_size", "learning_rate"].map((k) => <label key={k} className="text-sm">{k.replace("_", " ")}<select className="inp" value={f[k] ?? ""} onChange={(e) => chg(k, e.target.value)}><option value="">All</option>{d.options[k].map((x) => <option key={x}>{x}</option>)}</select></label>)}</div>
      {!S ? <Empty>No rows match these filters.</Empty> : <>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3"><Stat label="Experiments" value={S.count} /><Stat label="Avg accuracy" value={fix(S.avg_acc)} /><Stat label="Avg test accuracy" value={fix(S.avg_test_acc)} /><Stat label="Avg loss" value={fix(S.avg_loss)} />
          <Stat label="Best learning rate" value={S.best_learning_rate?.value} sub={`avg test acc ${fix(S.best_learning_rate?.avg_test_acc)}`} /><Stat label="Best batch size" value={S.best_batch_size?.value} sub={`avg ${fix(S.best_batch_size?.avg_test_acc)}`} /><Stat label="Best epoch" value={S.best_epoch?.value} sub={`avg ${fix(S.best_epoch?.avg_test_acc)}`} /><Stat label="Rows flagged 'Overfitting'" value={S.flagged_rows} /></div>
        <div className="grid md:grid-cols-2 gap-3"><div className="card text-sm"><b>Best experiment</b><p>{R(S.best)}</p></div><div className="card text-sm"><b>Worst experiment</b><p>{R(S.worst)}</p></div></div>
        <div className="grid md:grid-cols-2 gap-4">{line("Sample Size vs Accuracy", C.sample_vs_acc)}{line("Epoch vs Accuracy", C.epoch_vs_acc)}{line("Batch Size vs Accuracy", C.batch_vs_acc)}{line("Learning Rate vs Accuracy", C.lr_vs_acc)}{line("Epoch vs Loss", C.epoch_vs_loss, 0, "y", "#ef4444")}{line("Learning Rate vs Loss", C.lr_vs_loss, 0, "y", "#ef4444")}{line("Sample Size vs Different Image Accuracy (%)", C.sample_vs_different, 0, "y", "#10b981")}
          <div className="card"><b>Original vs Different Image Accuracy (range midpoints, %)</b><ResponsiveContainer height={220}><ScatterChart><CartesianGrid /><XAxis dataKey="original" name="Original" type="number" /><YAxis dataKey="different" name="Different" type="number" /><Tooltip /><Scatter data={C.original_vs_different} fill="#f59e0b" /></ScatterChart></ResponsiveContainer></div></div>
        {S.repeated_runs_with_variation.length > 0 && <div className="card text-sm"><b>Experimental variation</b><p>Identical settings with differing test accuracy:</p><ul className="list-disc ml-5">{S.repeated_runs_with_variation.slice(0, 10).map((v, i) => <li key={i}>sample {v.sample}, epoch {v.epoch}, batch {v.batch_size}, LR {v.learning_rate}: {v.min}–{v.max} over {v.runs} runs</li>)}</ul></div>}
        <div className="card overflow-auto max-h-96"><table className="w-full text-xs"><thead className="sticky top-0 bg-white"><tr className="text-left">{["sheet", "sample", "epoch", "batch_size", "learning_rate", "acc", "test_acc", "loss", "test_loss", "original_min", "original_max", "different_min", "different_max", "original_flag"].map((h) => <th key={h} className="p-1">{h}</th>)}</tr></thead>
          <tbody>{d.rows.slice(0, 500).map((r, i) => <tr key={i} className="border-t">{["sheet", "sample", "epoch", "batch_size", "learning_rate", "acc", "test_acc", "loss", "test_loss", "original_min", "original_max", "different_min", "different_max", "original_flag"].map((h) => <td key={h} className="p-1">{r[h] ?? ""}</td>)}</tr>)}</tbody></table></div></>}
      <div className="card"><b>Notes from workbook (original text)</b>{d.notes.length ? <ol className="list-decimal ml-5 text-sm space-y-1 mt-2">{d.notes.map((n, i) => <li key={i}>{n}</li>)}</ol> : <p className="text-sm text-slate-500">No Note sheet found.</p>}</div></div>}</div>;
}

export function Reports({ pid }) { return <div><h1 className="text-xl font-semibold mb-3">Project Report</h1><p className="text-sm text-slate-500 mb-2">Print-friendly HTML report (use the Print button inside, then “Save as PDF”).</p><a className="btn inline-block mb-3" target="_blank" href={apiUrl(`/api/projects/${pid}/report`)}>Open in new tab</a><iframe title="report" src={apiUrl(`/api/projects/${pid}/report`)} className="w-full h-[70vh] card" /></div>; }

export function About() { return <div className="card max-w-2xl"><h1 className="text-xl font-semibold mb-2">Smart ML Studio</h1><p className="text-sm">MScIT final-year project. Teachable Machine-style image classification with dataset quality analysis, hyperparameter control, evaluation, versioning and an Excel experiment analyzer.</p><p className="text-sm mt-2">Stack: React, Vite, Tailwind, Recharts · FastAPI · TensorFlow/Keras (MobileNetV2) · SQLite. Storage: <code>storage/projects/&lt;id&gt;/</code>. Database: <code>data/smartml.db</code> (created automatically). Backend API docs (when reachable): <a className="underline text-indigo-600" href={apiUrl("/docs")}>/docs</a>.</p></div>; }
