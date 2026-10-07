import cv2, numpy as np
from .dataset import class_images
from .storage import class_dir

def _dhash(g):
    s = cv2.resize(g, (9, 8)); return (s[:, 1:] > s[:, :-1]).flatten()

def analyze(pid):
    classes = class_images(pid)
    per = {c["name"]: len(c["images"]) for c in classes}
    total = sum(per.values())
    res = {"total_images": total, "per_class": per, "classes": len(classes), "invalid": [], "small": [], "blurry": [], "dark": [], "bright": [], "duplicates": []}
    if total == 0: res.update(score=0, recommendations=["Dataset is empty. Add at least 2 classes with 20+ images each."], balance=None, avg_file_kb=0, avg_width=0, avg_height=0); return res
    hashes, w, h, sz = [], [], [], []
    for c in classes:
        for i in c["images"]:
            p = class_dir(pid, c["id"]) / i["filename"]; tag = f"{c['name']}/{i['filename']}"
            img = cv2.imread(str(p))
            if img is None: res["invalid"].append(tag); continue
            hh, ww = img.shape[:2]; w.append(ww); h.append(hh); sz.append(i["size_bytes"] or 0)
            if min(hh, ww) < 64: res["small"].append(tag)
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if cv2.Laplacian(g, cv2.CV_64F).var() < 50: res["blurry"].append(tag)
            m = float(g.mean())
            if m < 40: res["dark"].append(tag)
            elif m > 215: res["bright"].append(tag)
            hashes.append((tag, _dhash(g)))
    for a in range(len(hashes)):
        for b in range(a + 1, len(hashes)):
            if int((hashes[a][1] != hashes[b][1]).sum()) <= 4: res["duplicates"].append([hashes[a][0], hashes[b][0]])
    counts = list(per.values()); bal = min(counts) / max(counts) if max(counts) else 0
    res.update(balance=round(bal, 3), avg_file_kb=round(np.mean(sz) / 1024, 1) if sz else 0,
               avg_width=int(np.mean(w)) if w else 0, avg_height=int(np.mean(h)) if h else 0)
    n = max(total, 1); rec = []; score = 100.0
    if len(classes) < 2: score -= 40; rec.append("Add at least a second class; classification needs 2+ classes.")
    if min(counts) < 20: score -= 20; rec.append(f"Smallest class has {min(counts)} images; aim for 20+ per class (50+ is better).")
    if bal < 0.6: score -= 15 * (1 - bal); rec.append(f"Classes are imbalanced (ratio {bal:.2f}); add images to the smallest class.")
    for key, pen, msg in (("invalid", 30, "unreadable"), ("small", 15, "very small (<64px)"), ("blurry", 15, "blurry"), ("dark", 10, "too dark"), ("bright", 10, "over-exposed")):
        frac = len(res[key]) / n
        if res[key]: score -= pen * min(1, frac * 4); rec.append(f"{len(res[key])} image(s) are {msg}; review or delete them.")
    if res["duplicates"]: score -= 10 * min(1, len(res["duplicates"]) / n * 4); rec.append(f"{len(res['duplicates'])} duplicate/near-duplicate pair(s) found; duplicates can leak between train and test and inflate accuracy.")
    res["score"] = int(max(0, min(100, round(score)))); res["recommendations"] = rec or ["Dataset looks healthy."]
    res["grade"] = "Good" if res["score"] >= 80 else "Fair" if res["score"] >= 60 else "Poor"
    return res
