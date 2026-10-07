"""Production/local entry point: python run.py  (listens on 0.0.0.0:$PORT, default 8000)."""
import os, uvicorn
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
