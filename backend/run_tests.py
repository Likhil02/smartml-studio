"""Executable checks that run without TensorFlow/FastAPI where possible."""
import sys, io, tempfile, json
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
from app import config
tmp = Path(tempfile.mkdtemp()); config.DB_PATH = tmp / "t.db"; config.STORAGE = tmp / "p"
from app import db; db.DB_PATH = config.DB_PATH; db.STORAGE = config.STORAGE
import app.services.storage as st; st.STORAGE = config.STORAGE
from app.services import dataset as ds, health, excel_analyzer as xa, evaluate, overfit
db.init_db(); ok = lambda m: print("PASS", m)

pid = db.ex("INSERT INTO projects(name) VALUES('t')"); cids = [db.ex("INSERT INTO classes(project_id,name) VALUES(?,?)", (pid, n)) for n in ("a", "b")]
rng = np.random.default_rng(0)
def img(v, w=96):
    b = io.BytesIO(); Image.fromarray((rng.random((w, w, 3)) * 80 + v).astype("uint8")).save(b, "PNG"); return b.getvalue()
for i, cid in enumerate(cids):
    for k in range(12): ds.save_image(pid, cid, f"x{k}.png", img(50 + 100 * i))
for bad, data in (("x.exe", b"MZ"), ("x.png", b"notimage"), ("../../e.png", img(10, 16))):
    try: ds.save_image(pid, cids[0], bad, data); raise SystemExit("FAIL validation " + bad)
    except ValueError: pass
ok("dataset upload + validation (type/corrupt/small)")
h = health.analyze(pid); assert h["total_images"] == 24 and 0 <= h["score"] <= 100 and h["balance"] == 1.0; ok(f"health analyzer score={h['score']}")
classes, sp = ds.split_dataset(pid); assert len(sp["train"]) + len(sp["val"]) + len(sp["test"]) == 24 and {i for _, i in sp["test"]} == {0, 1}; ok(f"stratified split { {k: len(v) for k, v in sp.items()} }")
m = evaluate.metrics_from_labels(np.array([0, 0, 1, 1]), np.array([0, 1, 1, 1]), ["a", "b"]); assert abs(m["accuracy"] - .75) < 1e-9 and m["confusion_matrix"] == [[1, 1], [0, 2]]; ok("evaluation metrics + confusion matrix")
assert not overfit.detect([{"epoch": i, "acc": .8, "val_acc": .79, "loss": .5, "val_loss": .5} for i in range(6)])["overfitting"]
assert overfit.detect([{"epoch": i, "acc": .99, "val_acc": .6, "loss": .1 - i * .01, "val_loss": .5 + i * .1} for i in range(6)])["overfitting"]; ok("overfitting rules (no false positive, true positive)")
xl = sys.argv[1] if len(sys.argv) > 1 else None
if xl:
    d = xa.parse_workbook(xl); s = xa.summarize(d["rows"]); assert len(d["rows"]) > 0 and d["notes"]; ok(f"excel: {len(d['rows'])} rows, sheets={d['sheets']}, notes={len(d['notes'])}")
try: xa.parse_workbook(b"junk"); raise SystemExit("FAIL")
except ValueError: ok("invalid workbook rejected")
try: import tensorflow; ok("tensorflow importable")
except ImportError: print("SKIP tensorflow not installed here (training/predict not executed)")
try: import fastapi; ok("fastapi importable")
except ImportError: print("SKIP fastapi not installed here (API not executed)")
