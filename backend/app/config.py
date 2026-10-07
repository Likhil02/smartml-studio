import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(os.getenv("SMARTML_HOME", ROOT))            # override to relocate data (e.g. /tmp/smartml on Render)
STORAGE = BASE / "storage" / "projects"
DB_PATH = BASE / "data" / "smartml.db"
SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_data"

def _flag(name, default="0"): return os.getenv(name, default).strip().lower() in ("1", "true", "yes")

DEMO_MODE = _flag("DEMO_MODE")                           # True on Render Free
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_FILE_MB = 8
MIN_RES = 32
IMG_SIZE = int(os.getenv("IMG_SIZE", "128" if DEMO_MODE else "160"))   # MobileNetV2: 96/128/160/192/224

# Demo-mode limits (free CPU tier). Local/large-scale mode is unrestricted by these.
MAX_DEMO_EPOCHS = int(os.getenv("MAX_DEMO_EPOCHS", "15"))
MAX_DEMO_BATCH = int(os.getenv("MAX_DEMO_BATCH", "64"))
MAX_DEMO_IMAGES = int(os.getenv("MAX_DEMO_IMAGES", "300"))
DEMO_DEFAULTS = {"epochs": 5, "batch_size": 16, "learning_rate": 0.001, "patience": 3, "early_stopping": True, "augmentation": True}

LOCAL_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173"]

def cors_origins():
    """FRONTEND_URL (comma-separated) restricts CORS to the deployed site; without it only local dev origins are allowed."""
    urls = [u.strip().rstrip("/") for u in os.getenv("FRONTEND_URL", "").split(",") if u.strip()]
    return urls or LOCAL_ORIGINS

def public_config():
    d = {"demo_mode": DEMO_MODE, "mode": "Demo training" if DEMO_MODE else "Large-scale / local training", "img_size": IMG_SIZE,
         "defaults": {k: v for k, v in DEMO_DEFAULTS.items()} if DEMO_MODE else {"epochs": 10, "batch_size": 32, "learning_rate": 0.001, "patience": 5, "early_stopping": True, "augmentation": True}}
    if DEMO_MODE: d.update(max_epochs=MAX_DEMO_EPOCHS, max_batch_size=MAX_DEMO_BATCH, max_images=MAX_DEMO_IMAGES)
    return d
