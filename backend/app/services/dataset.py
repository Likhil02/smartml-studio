import io, uuid, random
from pathlib import Path
import numpy as np
from PIL import Image, UnidentifiedImageError
from ..config import ALLOWED_EXT, MAX_FILE_MB, MIN_RES, IMG_SIZE
from .storage import safe_name, class_dir, project_dir
from .. import db

def save_image(pid, cid, filename, data: bytes):
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXT: raise ValueError(f"'{safe_name(filename)}': unsupported type '{ext}'. Allowed: {sorted(ALLOWED_EXT)}")
    if len(data) > MAX_FILE_MB * 1024 * 1024: raise ValueError(f"'{safe_name(filename)}': larger than {MAX_FILE_MB} MB")
    try:
        im = Image.open(io.BytesIO(data)); im.verify(); im = Image.open(io.BytesIO(data)); w, h = im.size
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValueError(f"'{safe_name(filename)}': corrupted or not an image")
    if min(w, h) < MIN_RES: raise ValueError(f"'{safe_name(filename)}': resolution {w}x{h} below minimum {MIN_RES}px")
    stored = f"{uuid.uuid4().hex[:8]}_{safe_name(filename)}"
    (class_dir(pid, cid) / stored).write_bytes(data)
    return db.ex("INSERT INTO images(class_id,filename,width,height,size_bytes) VALUES(?,?,?,?,?)", (cid, stored, w, h, len(data)))

def image_path(pid, cid, filename): return class_dir(pid, cid) / safe_name(filename)

def load_array(path, size=IMG_SIZE):
    im = Image.open(path).convert("RGB").resize((size, size))
    return np.asarray(im, dtype=np.float32)

def class_images(pid):
    out = []
    for c in db.q("SELECT * FROM classes WHERE project_id=? ORDER BY id", (pid,)):
        out.append({**c, "images": db.q("SELECT * FROM images WHERE class_id=? ORDER BY id", (c["id"],))})
    return out

def split_dataset(pid, train=0.7, seed=42):
    """Stratified per-class split. Returns (classes, {'train':[(path,idx)],...})."""
    classes = class_images(pid); val = (1 - train) / 2   # val and test share the remainder equally
    if len(classes) < 2: raise ValueError("At least 2 classes are required")
    rng = random.Random(seed); sp = {"train": [], "val": [], "test": []}
    for idx, c in enumerate(classes):
        if len(c["images"]) < 5: raise ValueError(f"Class '{c['name']}' has {len(c['images'])} images; need at least 5")
        items = [(str(class_dir(pid, c["id"]) / i["filename"]), idx) for i in c["images"]]
        rng.shuffle(items); n = len(items)
        nv = nt = max(1, round(n * val))
        sp["test"] += items[:nt]; sp["val"] += items[nt:nt + nv]; sp["train"] += items[nt + nv:]
    return classes, sp
