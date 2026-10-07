"""TensorFlow/Keras transfer learning (MobileNetV2). TensorFlow is imported lazily so the API starts without it."""
import json, time, threading
from pathlib import Path
import numpy as np
from ..config import IMG_SIZE, DEMO_MODE, MAX_DEMO_EPOCHS, MAX_DEMO_BATCH
from .. import db
from .dataset import split_dataset, load_array
from .storage import project_dir
from .overfit import detect

CANCEL = {}
ACTIVE = set()   # run ids currently training in this process

def _tf():
    try:
        import tensorflow as tf; return tf
    except ImportError:
        raise RuntimeError("TensorFlow is not installed. Run: pip install -r backend/requirements.txt")

def validate_config(c):
    errs = []
    if not 1 <= c.get("epochs", 0) <= 500: errs.append("epochs must be 1-500")
    if not 1 <= c.get("batch_size", 0) <= 1024: errs.append("batch_size must be 1-1024")
    if not 0 < c.get("learning_rate", 0) <= 1: errs.append("learning_rate must be in (0, 1]")
    if not 0.5 <= c.get("train_ratio", 0.7) <= 0.9: errs.append("train_ratio must be 0.5-0.9")
    if DEMO_MODE:
        if c.get("epochs", 0) > MAX_DEMO_EPOCHS: errs.append(f"Demo mode allows at most {MAX_DEMO_EPOCHS} epochs (run locally for large-scale training)")
        if c.get("batch_size", 0) > MAX_DEMO_BATCH: errs.append(f"Demo mode allows batch size up to {MAX_DEMO_BATCH}")
    if errs: raise ValueError("; ".join(errs))

def augment_layers(tf):
    # mild only: faces are not flipped vertically / rotated heavily
    return tf.keras.Sequential([tf.keras.layers.RandomFlip("horizontal"), tf.keras.layers.RandomRotation(0.05), tf.keras.layers.RandomZoom(0.1), tf.keras.layers.RandomBrightness(0.1)])

def _arrays(items):
    X = np.stack([load_array(p) for p, _ in items]); y = np.array([i for _, i in items]); return X, y

def start_training(pid, cfg):
    validate_config(cfg); _tf()
    if DEMO_MODE and ACTIVE: raise ValueError("Another training run is in progress. The free demo server trains one model at a time.")
    classes, sp = split_dataset(pid, cfg.get("train_ratio", 0.7), seed=cfg.get("seed", 42))
    rid = db.ex("INSERT INTO training_runs(project_id,status,config_json,total_epochs) VALUES(?,?,?,?)", (pid, "running", json.dumps(cfg), cfg["epochs"]))
    db.ex("INSERT INTO datasets(project_id,train_count,val_count,test_count,split_json) VALUES(?,?,?,?,?)",
          (pid, len(sp["train"]), len(sp["val"]), len(sp["test"]), json.dumps({"classes": [c["name"] for c in classes]})))
    CANCEL[rid] = threading.Event(); ACTIVE.add(rid)
    threading.Thread(target=_train, args=(rid, pid, cfg, classes, sp), daemon=True).start(); return rid

def _train(rid, pid, cfg, classes, sp):
    t0 = time.time()
    try:
        tf = _tf(); tf.keras.utils.set_random_seed(cfg.get("seed", 42))
        Xtr, ytr = _arrays(sp["train"]); Xva, yva = _arrays(sp["val"]); n = len(classes)
        base = tf.keras.applications.MobileNetV2(input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False, weights="imagenet"); base.trainable = False
        inp = tf.keras.Input((IMG_SIZE, IMG_SIZE, 3)); x = inp
        if cfg.get("augmentation", True): x = augment_layers(tf)(x)
        x = tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1.0)(x)   # MobileNetV2 expects [-1, 1]
        x = base(x, training=False); x = tf.keras.layers.GlobalAveragePooling2D()(x); x = tf.keras.layers.Dropout(0.2)(x)
        out = tf.keras.layers.Dense(n, activation="softmax")(x); model = tf.keras.Model(inp, out)
        model.compile(optimizer=tf.keras.optimizers.Adam(cfg["learning_rate"]), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
        hist = []

        class CB(tf.keras.callbacks.Callback):
            def on_epoch_end(s, ep, logs=None):
                h = {"epoch": ep + 1, "acc": float(logs["accuracy"]), "val_acc": float(logs["val_accuracy"]), "loss": float(logs["loss"]), "val_loss": float(logs["val_loss"])}
                hist.append(h); db.ex("INSERT INTO metrics(run_id,epoch,acc,val_acc,loss,val_loss) VALUES(?,?,?,?,?,?)", (rid, h["epoch"], h["acc"], h["val_acc"], h["loss"], h["val_loss"]))
                db.ex("UPDATE training_runs SET current_epoch=?, elapsed=? WHERE id=?", (ep + 1, time.time() - t0, rid))
                if CANCEL[rid].is_set(): s.model.stop_training = True
        cbs = [CB()]
        if cfg.get("early_stopping", True): cbs.append(tf.keras.callbacks.EarlyStopping(patience=cfg.get("patience", 5), restore_best_weights=True, monitor="val_loss"))
        model.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=cfg["epochs"], batch_size=cfg["batch_size"], callbacks=cbs, verbose=0)
        if CANCEL[rid].is_set(): db.ex("UPDATE training_runs SET status='cancelled', finished_at=CURRENT_TIMESTAMP WHERE id=?", (rid,)); return
        from .evaluate import evaluate_model
        names = [c["name"] for c in classes]; ev = evaluate_model(model, sp["test"], names)
        ver = (db.q1("SELECT COALESCE(MAX(version),0)+1 v FROM model_versions WHERE project_id=?", (pid,)))["v"]
        mdir = project_dir(pid) / "models" / f"v{ver}"; mdir.mkdir(parents=True, exist_ok=True)
        model.save(mdir / "model.keras"); (mdir / "classes.json").write_text(json.dumps(names))
        db.ex("""INSERT INTO model_versions(project_id,run_id,version,dataset_json,epochs,batch_size,learning_rate,accuracy,precision,recall,f1,eval_json,model_path)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (pid, rid, ver, json.dumps({"train": len(sp["train"]), "val": len(sp["val"]), "test": len(sp["test"]), "classes": names}),
                 len(hist), cfg["batch_size"], cfg["learning_rate"], ev["accuracy"], ev["precision"], ev["recall"], ev["f1"], json.dumps(ev), str(mdir / "model.keras")))
        db.ex("UPDATE training_runs SET status='completed', overfitting_json=?, finished_at=CURRENT_TIMESTAMP, elapsed=? WHERE id=?", (json.dumps(detect(hist)), time.time() - t0, rid))
    except Exception as e:
        db.ex("UPDATE training_runs SET status='failed', error=?, finished_at=CURRENT_TIMESTAMP WHERE id=?", (str(e)[:500], rid))
    finally:
        ACTIVE.discard(rid)

_cache = {}
def load_version(pid, version=None):
    mv = db.q1("SELECT * FROM model_versions WHERE project_id=? ORDER BY version DESC LIMIT 1", (pid,)) if version is None else db.q1("SELECT * FROM model_versions WHERE project_id=? AND version=?", (pid, version))
    if not mv or not Path(mv["model_path"]).exists(): raise FileNotFoundError("No trained model found for this project. Train a model first.")
    if mv["model_path"] not in _cache: _cache[mv["model_path"]] = _tf().keras.models.load_model(mv["model_path"])
    return _cache[mv["model_path"]], json.loads(mv["dataset_json"])["classes"], mv

def predict(pid, arr, version=None):
    model, names, mv = load_version(pid, version)
    p = model.predict(arr[None, ...], verbose=0)[0]; i = int(p.argmax())
    return {"predicted": names[i], "confidence": float(p[i]), "probabilities": {n: float(v) for n, v in zip(names, p)}, "model_version": mv["version"]}
