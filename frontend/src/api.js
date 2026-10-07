// Production: VITE_API_URL = Render backend URL. Local dev: empty -> Vite proxy forwards /api to 127.0.0.1:8000.
export const API = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");
export const apiUrl = (p) => API + p;
async function req(url, opts = {}) {
  // Safety net: never send a request whose path contains a missing id (e.g. /projects/undefined/...)
  if (/\/(undefined|null|NaN)(\/|$|\?)/.test(url) || /\/\//.test(url.replace(/^https?:\/\//, ""))) throw new Error("No project selected");
  let r; try { r = await fetch(API + url, opts); } catch { throw new Error(`Cannot reach the backend (${API || "local proxy -> http://127.0.0.1:8000"}). It may be starting up (free hosting sleeps) or not running.`); }
  if (!r.ok) { let m = r.statusText; try { const j = await r.json(); m = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch {} throw new Error(m); }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r;
}
const J = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const api = {
  ping: () => req("/api/health"), config: () => req("/api/config"), loadSample: (id) => req(`/api/projects/${id}/load-sample`, { method: "POST" }),
  projects: () => req("/api/projects"), createProject: (b) => req("/api/projects", J("POST", b)),
  project: (id) => req(`/api/projects/${id}`), deleteProject: (id) => req(`/api/projects/${id}`, { method: "DELETE" }),
  addClass: (id, name) => req(`/api/projects/${id}/classes`, J("POST", { name })), renameClass: (id, name) => req(`/api/classes/${id}`, J("PUT", { name })),
  deleteClass: (id) => req(`/api/classes/${id}`, { method: "DELETE" }),
  upload: (cid, files) => { const f = new FormData(); [...files].forEach((x) => f.append("files", x)); return req(`/api/classes/${cid}/images`, { method: "POST", body: f }); },
  deleteImage: (id) => req(`/api/images/${id}`, { method: "DELETE" }),
  datasetHealth: (id) => req(`/api/projects/${id}/dataset-health`), split: (id, t) => req(`/api/projects/${id}/split?train=${t}`),
  train: (id, cfg) => req(`/api/projects/${id}/train`, J("POST", cfg)), status: (rid) => req(`/api/training/${rid}`),
  cancel: (rid) => req(`/api/training/${rid}/cancel`, { method: "POST" }), runs: (id) => req(`/api/projects/${id}/training-runs`),
  predict: (id, file) => { const f = new FormData(); f.append("file", file); return req(`/api/projects/${id}/predict`, { method: "POST", body: f }); },
  evaluate: (id) => req(`/api/projects/${id}/evaluate`, { method: "POST" }),
  versions: (id) => req(`/api/projects/${id}/model-versions`), experiments: (id) => req(`/api/projects/${id}/experiments`),
  excelUpload: (file) => { const f = new FormData(); f.append("file", file); return req("/api/experiments/upload-excel", { method: "POST", body: f }); },
  excelGet: (eid, q = "") => req(`/api/experiments/excel/${eid}?${q}`), excelLatest: () => req("/api/experiments/excel-latest"),
};
export const imgUrl = (id) => `${API}/api/images/${id}/file`;
