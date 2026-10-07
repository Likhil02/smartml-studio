"""Deployment-config checks. Run: python test_deploy.py  (FastAPI-dependent checks run only when fastapi is installed)."""
import os, sys, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(Path(__file__).parent))
ok = lambda m: print("PASS", m)
def need(c, m):
    if not c: raise SystemExit("FAIL " + m)
    ok(m)
import tomllib
t = tomllib.loads((ROOT / "netlify.toml").read_text())
need(t["build"]["command"] == "npm run build" and t["build"]["publish"] == "dist" and t["build"]["base"] == "frontend", "netlify.toml build/publish/base")
need(any(r["from"] == "/*" and r["to"] == "/index.html" and r["status"] == 200 for r in t["redirects"]), "netlify SPA fallback redirect")
try:
    import yaml; y = yaml.safe_load((ROOT / "render.yaml").read_text()); svc = y["services"]; ok("render.yaml parses (PyYAML)")
except ImportError:
    txt = (ROOT / "render.yaml").read_text(); svc = [{"startCommand": re.search(r"startCommand: (.+)", txt)[1], "plan": re.search(r"plan: (\w+)", txt)[1], "healthCheckPath": re.search(r"healthCheckPath: (\S+)", txt)[1]}]; ok("render.yaml read by regex (PyYAML not installed)")
need(len(svc) == 1 and svc[0]["plan"] == "free", "render.yaml: single free web service")
need("--host 0.0.0.0" in svc[0]["startCommand"] and "$PORT" in svc[0]["startCommand"], "render start command binds 0.0.0.0:$PORT")
need(svc[0]["healthCheckPath"] == "/api/health", "render health check path")
gi = (ROOT / ".gitignore").read_text()
for e in ("venv/", "node_modules/", "__pycache__/", "*.pyc", ".env", "storage/projects/*"): need(e in gi.split("\n"), f".gitignore has {e}")
need("VITE_API_URL" in (ROOT / "frontend/.env.example").read_text(), "frontend/.env.example")
need("import.meta.env.VITE_API_URL" in (ROOT / "frontend/src/api.js").read_text(), "frontend reads VITE_API_URL")
fe = "".join(p.read_text() for p in (ROOT / "frontend/src").glob("*.js*"))
need(not re.search(r"fetch\(\s*[\"'`]https?:", fe) and "fetch(API + url" in fe, "frontend fetch() uses VITE_API_URL prefix, no hard-coded host")
from app import config
os.environ.pop("FRONTEND_URL", None); need(config.cors_origins() == config.LOCAL_ORIGINS and "*" not in config.cors_origins(), "CORS default = local dev origins, no wildcard")
os.environ["FRONTEND_URL"] = "https://demo.netlify.app/, https://b.netlify.app"; need(config.cors_origins() == ["https://demo.netlify.app", "https://b.netlify.app"], "CORS from FRONTEND_URL (trailing slash trimmed)")
need(len(list((ROOT / "backend/sample_data").glob("*/*.png"))) == 72, "bundled sample dataset: 72 images")
try:
    from fastapi.testclient import TestClient; import app.main as m
    c = TestClient(m.app); r = c.get("/api/health"); need(r.status_code == 200 and r.json() == {"status": "ok"}, "GET /api/health via TestClient")
    r = c.options("/api/health", headers={"Origin": "https://demo.netlify.app", "Access-Control-Request-Method": "GET"}); print("CORS preflight allow-origin:", r.headers.get("access-control-allow-origin"))
except ImportError: print("SKIP fastapi/httpx not installed: TestClient checks not run")
