import json, io
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from . import db
from .config import STORAGE, SAMPLE_DIR, DEMO_MODE, MAX_DEMO_IMAGES, cors_origins, public_config
from .services import dataset as ds, health, ml, excel_analyzer as xa
from .services.storage import safe_name, project_dir, class_dir, remove_tree, inside

app = FastAPI(title="Smart ML Studio")
app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"])

@app.get("/api/health")
def health_check(): return {"status": "ok"}

@app.get("/api/config")
def app_config(): return public_config()

@app.on_event("startup")
def _s(): db.init_db()

def need_project(pid):
    p = db.q1("SELECT * FROM projects WHERE id=?", (pid,))
    if not p: raise HTTPException(404, "Project not found")
    return p

class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=80); description: str = Field("", max_length=500)
class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
class TrainIn(BaseModel):
    epochs: int = 5; batch_size: int = 16; learning_rate: float = 0.001; augmentation: bool = True
    early_stopping: bool = True; patience: int = 3; seed: int = 42; train_ratio: float = 0.7

@app.get("/api/projects")
def list_projects():
    return db.q("""SELECT p.*, (SELECT COUNT(*) FROM classes c WHERE c.project_id=p.id) classes,
        (SELECT COUNT(*) FROM images i JOIN classes c ON c.id=i.class_id WHERE c.project_id=p.id) images,
        (SELECT COUNT(*) FROM model_versions m WHERE m.project_id=p.id) versions FROM projects p ORDER BY id DESC""")

@app.post("/api/projects")
def create_project(b: ProjectIn):
    pid = db.ex("INSERT INTO projects(name,description) VALUES(?,?)", (b.name.strip(), b.description)); project_dir(pid); return need_project(pid)

@app.get("/api/projects/{pid}")
def get_project(pid: int):
    p = need_project(pid); p["classes"] = [{"id": c["id"], "name": c["name"], "images": c["images"]} for c in ds.class_images(pid)]; return p

@app.delete("/api/projects/{pid}")
def del_project(pid: int):
    need_project(pid); db.ex("DELETE FROM projects WHERE id=?", (pid,)); remove_tree(STORAGE / str(pid)); return {"ok": True}

@app.post("/api/projects/{pid}/classes")
def add_class(pid: int, b: ClassIn):
    need_project(pid)
    try: cid = db.ex("INSERT INTO classes(project_id,name) VALUES(?,?)", (pid, b.name.strip()))
    except Exception: raise HTTPException(409, "A class with this name already exists")
    class_dir(pid, cid); return {"id": cid, "name": b.name.strip()}

@app.put("/api/classes/{cid}")
def rename_class(cid: int, b: ClassIn):
    try: db.ex("UPDATE classes SET name=? WHERE id=?", (b.name.strip(), cid))
    except Exception: raise HTTPException(409, "A class with this name already exists")
    return {"id": cid, "name": b.name.strip()}

@app.delete("/api/classes/{cid}")
def del_class(cid: int):
    c = db.q1("SELECT * FROM classes WHERE id=?", (cid,))
    if not c: raise HTTPException(404, "Class not found")
    remove_tree(class_dir(c["project_id"], cid)); db.ex("DELETE FROM classes WHERE id=?", (cid,)); return {"ok": True}

@app.post("/api/classes/{cid}/images")
async def upload_images(cid: int, files: list[UploadFile] = File(...)):
    c = db.q1("SELECT * FROM classes WHERE id=?", (cid,))
    if not c: raise HTTPException(404, "Class not found")
    saved, errors = 0, []
    room = None
    if DEMO_MODE:
        room = MAX_DEMO_IMAGES - db.q1("SELECT COUNT(*) n FROM images i JOIN classes c ON c.id=i.class_id WHERE c.project_id=?", (c["project_id"],))["n"]
    for f in files:
        if room is not None and room <= 0:
            errors.append(f"Demo limit reached ({MAX_DEMO_IMAGES} images per project); '{safe_name(f.filename)}' skipped"); continue
        try: ds.save_image(c["project_id"], cid, f.filename, await f.read()); saved += 1; room = None if room is None else room - 1
        except ValueError as e: errors.append(str(e))
    return {"saved": saved, "errors": errors}

@app.post("/api/projects/{pid}/load-sample")
def load_sample(pid: int):
    """Copy the bundled synthetic sample dataset (backend/sample_data/<class>/*.png) into this project."""
    need_project(pid)
    if not SAMPLE_DIR.exists(): raise HTTPException(404, "Bundled sample dataset not found")
    saved = 0; names = []
    for d in sorted(p for p in SAMPLE_DIR.iterdir() if p.is_dir()):
        row = db.q1("SELECT id FROM classes WHERE project_id=? AND name=?", (pid, d.name))
        cid = row["id"] if row else db.ex("INSERT INTO classes(project_id,name) VALUES(?,?)", (pid, d.name)); names.append(d.name)
        if db.q1("SELECT 1 x FROM images WHERE class_id=? LIMIT 1", (cid,)): continue   # never duplicate images on repeat clicks
        for f in sorted(d.glob("*.png")): ds.save_image(pid, cid, f.name, f.read_bytes()); saved += 1
    return {"saved": saved, "classes": names}

@app.get("/api/images/{iid}/file")
def image_file(iid: int):
    r = db.q1("SELECT i.filename, i.class_id, c.project_id FROM images i JOIN classes c ON c.id=i.class_id WHERE i.id=?", (iid,))
    if not r: raise HTTPException(404, "Image not found")
    p = inside(STORAGE, class_dir(r["project_id"], r["class_id"]) / safe_name(r["filename"]))
    if not p.exists(): raise HTTPException(404, "File missing")
    return FileResponse(p)

@app.delete("/api/images/{iid}")
def del_image(iid: int):
    r = db.q1("SELECT i.filename, i.class_id, c.project_id FROM images i JOIN classes c ON c.id=i.class_id WHERE i.id=?", (iid,))
    if not r: raise HTTPException(404, "Image not found")
    ds.image_path(r["project_id"], r["class_id"], r["filename"]).unlink(missing_ok=True); db.ex("DELETE FROM images WHERE id=?", (iid,)); return {"ok": True}

@app.get("/api/projects/{pid}/dataset-health")
def dataset_health(pid: int): need_project(pid); return health.analyze(pid)

@app.get("/api/projects/{pid}/split")
def split_preview(pid: int, train: float = 0.7):
    need_project(pid)
    try: classes, sp = ds.split_dataset(pid, train)
    except ValueError as e: raise HTTPException(400, str(e))
    return {"train": len(sp["train"]), "val": len(sp["val"]), "test": len(sp["test"]), "classes": [c["name"] for c in classes]}

@app.post("/api/projects/{pid}/train")
def train(pid: int, b: TrainIn):
    need_project(pid)
    try: return {"run_id": ml.start_training(pid, b.model_dump())}
    except ValueError as e: raise HTTPException(400, str(e))
    except RuntimeError as e: raise HTTPException(503, str(e))

@app.get("/api/training/{rid}")
def training_status(rid: int):
    r = db.q1("SELECT * FROM training_runs WHERE id=?", (rid,))
    if not r: raise HTTPException(404, "Training run not found")
    h = db.q("SELECT epoch,acc,val_acc,loss,val_loss FROM metrics WHERE run_id=? ORDER BY epoch", (rid,))
    r["history"] = h; r["config"] = json.loads(r.pop("config_json") or "{}"); r["overfitting"] = json.loads(r.pop("overfitting_json") or "null")
    done = r["current_epoch"]; r["eta"] = round(r["elapsed"] / done * (r["total_epochs"] - done), 1) if done and r["status"] == "running" else None
    return r

@app.post("/api/training/{rid}/cancel")
def cancel(rid: int):
    if rid in ml.CANCEL: ml.CANCEL[rid].set()
    return {"ok": True}

@app.get("/api/projects/{pid}/training-runs")
def runs(pid: int): need_project(pid); return db.q("SELECT id,status,current_epoch,total_epochs,started_at FROM training_runs WHERE project_id=? ORDER BY id DESC", (pid,))

def _decode(data):
    try: return ds_load(data)
    except Exception: raise HTTPException(400, "Could not read image")

def ds_load(data):
    import numpy as np; from PIL import Image
    from .config import IMG_SIZE
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGB").resize((IMG_SIZE, IMG_SIZE)), dtype=np.float32)

@app.post("/api/projects/{pid}/predict")
async def predict(pid: int, file: UploadFile = File(...), version: int | None = Form(None)):
    need_project(pid); arr = _decode(await file.read())
    try: return ml.predict(pid, arr, version)
    except FileNotFoundError as e: raise HTTPException(404, str(e))
    except RuntimeError as e: raise HTTPException(503, str(e))

@app.post("/api/projects/{pid}/evaluate")
def evaluate(pid: int, version: int | None = None):
    need_project(pid)
    try: model, names, mv = ml.load_version(pid, version)
    except FileNotFoundError as e: raise HTTPException(404, str(e))
    from .services.evaluate import evaluate_model
    _, sp = ds.split_dataset(pid); return {**evaluate_model(model, sp["test"], names), "version": mv["version"]}

def _version(v):
    v["dataset"] = json.loads(v.pop("dataset_json") or "{}"); v["evaluation"] = json.loads(v.pop("eval_json") or "{}"); return v

@app.get("/api/projects/{pid}/model-versions")
def versions(pid: int): need_project(pid); return [_version(v) for v in db.q("SELECT * FROM model_versions WHERE project_id=? ORDER BY version DESC", (pid,))]

@app.get("/api/projects/{pid}/model-versions/{ver}/export")
def export_model(pid: int, ver: int):
    mv = db.q1("SELECT model_path FROM model_versions WHERE project_id=? AND version=?", (pid, ver))
    if not mv: raise HTTPException(404, "Model version not found")
    return FileResponse(inside(STORAGE, __import__("pathlib").Path(mv["model_path"])), filename=f"smartml_p{pid}_v{ver}.keras")

@app.get("/api/projects/{pid}/experiments")
def experiments(pid: int):
    need_project(pid)
    return db.q("""SELECT m.version, m.run_id, m.epochs, m.batch_size, m.learning_rate, m.accuracy, m.f1, m.created_at, m.dataset_json,
        (SELECT val_acc FROM metrics WHERE run_id=m.run_id ORDER BY epoch DESC LIMIT 1) val_acc,
        (SELECT loss FROM metrics WHERE run_id=m.run_id ORDER BY epoch DESC LIMIT 1) loss
        FROM model_versions m WHERE m.project_id=? ORDER BY m.accuracy DESC""", (pid,))

@app.post("/api/experiments/upload-excel")
async def upload_excel(file: UploadFile = File(...), project_id: int | None = Form(None)):
    if not (file.filename or "").lower().endswith(".xlsx"): raise HTTPException(400, "Only .xlsx workbooks are supported")
    data = await file.read()
    if len(data) > 15 * 1024 * 1024: raise HTTPException(400, "Workbook larger than 15 MB")
    try: parsed = xa.parse_workbook(data)
    except ValueError as e: raise HTTPException(400, str(e))
    eid = db.ex("INSERT INTO experiments(project_id,source,payload_json) VALUES(?,?,?)", (project_id, safe_name(file.filename), json.dumps(parsed)))
    return {"experiment_id": eid, **_excel_view(parsed)}

def _excel_view(parsed, **f):
    rows = xa.filter_rows(parsed["rows"], **f)
    opts = {k: sorted({r[k] for r in parsed["rows"]}) for k in ("sample", "epoch", "batch_size", "learning_rate")}
    return {"sheets": parsed["sheets"], "notes": parsed["notes"], "warnings": parsed["warnings"], "options": opts, "rows": rows,
            "summary": xa.summarize(rows) if rows else None, "charts": xa.chart_series(rows)}

@app.get("/api/experiments/excel/{eid}")
def excel_get(eid: int, sample: int | None = None, epoch: int | None = None, batch_size: int | None = None, learning_rate: float | None = None):
    r = db.q1("SELECT payload_json FROM experiments WHERE id=?", (eid,))
    if not r: raise HTTPException(404, "Experiment workbook not found")
    return _excel_view(json.loads(r["payload_json"]), sample=sample, epoch=epoch, batch_size=batch_size, learning_rate=learning_rate)

@app.get("/api/experiments/excel-latest")
def excel_latest(project_id: int | None = None):
    r = db.q1("SELECT id FROM experiments ORDER BY id DESC LIMIT 1")
    return {"experiment_id": r["id"] if r else None}

@app.get("/api/projects/{pid}/report", response_class=HTMLResponse)
def report(pid: int):
    p = need_project(pid); h = health.analyze(pid); vs = [_version(v) for v in db.q("SELECT * FROM model_versions WHERE project_id=? ORDER BY version DESC", (pid,))]
    x = db.q1("SELECT payload_json FROM experiments ORDER BY id DESC LIMIT 1"); esum = xa.summarize(json.loads(x["payload_json"])["rows"]) if x else None
    best = max(vs, key=lambda v: v["accuracy"]) if vs else None
    tr = db.q1("SELECT * FROM training_runs WHERE project_id=? ORDER BY id DESC LIMIT 1", (pid,))
    e = lambda s: __import__("html").escape(str(s))
    out = [f"<html><head><meta charset='utf-8'><title>{e(p['name'])} report</title><style>body{{font-family:Segoe UI,Arial;max-width:900px;margin:30px auto}}table{{border-collapse:collapse}}td,th{{border:1px solid #999;padding:4px 8px}}h2{{border-bottom:2px solid #444}}@media print{{button{{display:none}}}}</style></head><body><button onclick='print()'>Print</button>",
           f"<h1>Smart ML Studio — {e(p['name'])}</h1><p>{e(p['description'])}</p><h2>Dataset</h2><p>{h['total_images']} images, {h['classes']} classes: {e(h['per_class'])}</p><h2>Dataset health</h2><p>Score {h['score']}/100</p><ul>{''.join(f'<li>{e(r)}</li>' for r in h['recommendations'])}</ul>"]
    if tr: out.append(f"<h2>Latest training run</h2><pre>{e(tr['config_json'])}</pre><p>Status: {e(tr['status'])}, epochs run: {tr['current_epoch']}</p>")
    if best:
        ev = best["evaluation"]; cm = ev.get("confusion_matrix", []); names = ev.get("classes", [])
        out.append(f"<h2>Best model: v{best['version']}</h2><p>Accuracy {best['accuracy']:.4f} · Precision {best['precision']:.4f} · Recall {best['recall']:.4f} · F1 {best['f1']:.4f}</p><h3>Confusion matrix</h3><table><tr><th></th>{''.join(f'<th>{e(n)}</th>' for n in names)}</tr>"
                   + "".join(f"<tr><th>{e(names[i])}</th>{''.join(f'<td>{c}</td>' for c in row)}</tr>" for i, row in enumerate(cm)) + f"</table><pre>{e(ev.get('report',''))}</pre>")
        out.append("<h2>Experiment comparison</h2><table><tr><th>Ver</th><th>Epochs</th><th>Batch</th><th>LR</th><th>Acc</th><th>F1</th></tr>" + "".join(f"<tr><td>{v['version']}</td><td>{v['epochs']}</td><td>{v['batch_size']}</td><td>{v['learning_rate']}</td><td>{v['accuracy']:.4f}</td><td>{v['f1']:.4f}</td></tr>" for v in vs) + "</table>")
    else: out.append("<h2>Evaluation</h2><p>No trained model yet.</p>")
    if esum: out.append(f"<h2>Excel experiment insights</h2><p>{esum['count']} experiments. Avg test accuracy {esum['avg_test_acc']:.3f}. Best LR {esum['best_learning_rate']['value']}, best batch {esum['best_batch_size']['value']}, best epoch {esum['best_epoch']['value']}.</p>")
    return "".join(out) + "</body></html>"
