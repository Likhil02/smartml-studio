import re, shutil
from pathlib import Path
from ..config import STORAGE

def safe_name(name: str, default="file") -> str:
    name = re.sub(r"[^A-Za-z0-9._ -]", "", Path(name or "").name).strip(" .")
    return name[:80] or default

def project_dir(pid: int) -> Path:
    p = STORAGE / str(int(pid))
    for s in ("dataset", "models", "reports", "experiments"): (p / s).mkdir(parents=True, exist_ok=True)
    return p

def class_dir(pid: int, cid: int) -> Path:
    d = project_dir(pid) / "dataset" / str(int(cid)); d.mkdir(parents=True, exist_ok=True); return d

def inside(base: Path, target: Path) -> Path:
    t = target.resolve()
    if base.resolve() not in t.parents and t != base.resolve(): raise ValueError("Path escapes storage")
    return t

def remove_tree(p: Path):
    if p.exists(): shutil.rmtree(inside(STORAGE, p), ignore_errors=True)
