# Smart ML Studio

MScIT final-year project: a web platform for training image classifiers in the style of Google Teachable Machine, extended with dataset-quality analysis, hyperparameter control, evaluation, overfitting detection, model versioning, experiment comparison and an Excel experiment analyzer.

## Problem statement
Teachable Machine hides dataset quality, hyperparameters and evaluation. Students cannot see *why* a model performs as it does. Smart ML Studio exposes these steps while keeping the workflow simple.

## Features
Projects and classes; multi-image upload (drag & drop, preview, delete, validation of type/size/corruption/resolution/file names); dataset health (counts, balance, dimensions, invalid/small/blurry/dark/bright images, near-duplicates via difference hash, 0-100 score and recommendations); stratified 70/15/15 split; MobileNetV2 transfer learning with configurable epochs, batch size, learning rate, augmentation, early stopping, patience and seed; live training progress and charts; cancellation (stops after the current epoch); rule-based overfitting detection; real test-set evaluation (accuracy, precision, recall, F1, confusion matrix, classification report, per-class metrics); upload and webcam prediction; model versions with comparison and `.keras` export; experiment history; Excel Experiment Analyzer; print-friendly HTML report.

## Architecture
React (Vite) -> FastAPI -> services (dataset, health, ml, evaluate, excel_analyzer) -> SQLite + local files.

```
smartml-studio/
  backend/  app/{main.py,db.py,config.py,services/}  requirements.txt  run_tests.py
  frontend/ src/{App.jsx,pages.jsx,ui.jsx,api.js}  package.json
  data/     smartml.db (auto-created)
  storage/projects/<id>/{dataset,models,reports,experiments}
```

## Quick start (Windows)
Double-click `RUN_WINDOWS.bat` (creates the venv, installs dependencies, starts both servers, opens the browser).

## Setup (Windows, no GPU, manual)
Requires Python 3.10-3.12 and Node 18+.
```
cd smartml-studio\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
New terminal:
```
cd smartml-studio\frontend
npm install
npm run dev
```
Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs. The SQLite database and storage folders are created automatically at startup.

## Usage
1. Dashboard -> New Project. 2. Dataset Manager -> add 2+ classes, upload images (5+ per class is the hard minimum; 20+ recommended). 3. Dataset Health -> review score. 4. Training -> choose hyperparameters -> Start. 5. Evaluation shows metrics on the held-out test split. 6. Live Prediction -> upload an image or start the camera (frames are captured in the browser and sent to the backend about once per second; the browser requires localhost or HTTPS for camera access). 7. Model Versions -> compare or export `.keras`. 8. Reports -> open/print.

### Excel Experiment Analyzer
Upload an `.xlsx`. The parser finds sheets whose headers contain Sample/Epoch/Batch Size/Learning Rate/Accuracy, supports two-row merged headers (Accuracy Per Epoch -> Acc / Tes Acc, Loss Per Epoch -> Loss / Tes Loss), comma decimals, `min-max` range cells (stored as min, max and midpoint) and text cells such as `Overfitting` (kept as flags, not converted to numbers). Notes are shown verbatim from the Note sheet. Averages are over the filtered rows; "best" values are by mean test accuracy per value.

## Tests
Status at packaging time: executed here = Excel parser, dataset upload validation, health analyzer, split, evaluation metrics, overfitting rules, and route functions called directly with stubbed FastAPI. NOT executed (no network in the packaging environment) = `pip install`, real FastAPI/uvicorn startup, TensorFlow training/prediction, `npm install`/`npm run build`. Run these once on your machine.

`python backend/run_tests.py <workbook.xlsx>` exercises upload validation, health analysis, stratified split, evaluation metrics, overfitting rules and the Excel parser. TensorFlow/FastAPI checks run only if those packages are installed.

## Troubleshooting
- "TensorFlow is not installed": `pip install -r requirements.txt` inside the venv; use Python 3.10-3.12.
- First training run downloads MobileNetV2 ImageNet weights (internet needed once).
- Camera blocked: allow camera permission; use `localhost`.
- Training is slow: reduce epochs, keep images few hundred per class.

## Limitations
No authentication (local use). Training runs in a background thread of the API process (one process, restart loses running jobs). Duplicate detection is O(n^2). Webcam inference is server-side per captured frame, not on-device. Best-run Excel ranking is by test accuracy; the workbook's own results are not re-validated.

## Future scope
TensorFlow.js in-browser inference, fine-tuning of upper MobileNet layers, Grad-CAM, PDF export, multi-user accounts.


## ZERO-COST DEPLOYMENT (Netlify Free + Render Free)

Intended for an MScIT demonstration, not production. Nothing here costs money; no card is required on either free plan (verify current plan terms on the providers' sites).

```
Netlify (React)  --VITE_API_URL-->  Render Free (FastAPI + TensorFlow)  -->  SQLite + temp files
```

1. **Push to GitHub.** Create a repository and push the whole `smartml-studio` folder (`.gitignore` already excludes `venv/`, `node_modules/`, `__pycache__/`, `.env`, generated storage and databases).
2. **Deploy the backend to Render Free first** (you need its URL for step 4).
   - Render dashboard -> New -> *Blueprint* -> pick the repo. `render.yaml` creates one free Web Service (`rootDir: backend`, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/api/health`, `DEMO_MODE=true`).
   - When asked for `FRONTEND_URL`, enter your Netlify URL if you already know it, otherwise a placeholder and edit it after step 3. No trailing slash needed (it is trimmed).
   - Copy the service URL, e.g. `https://smartml-studio-api.onrender.com`. Check `<url>/api/health` returns `{"status":"ok"}`.
3. **Deploy the frontend to Netlify Free.** Add new site -> Import from Git -> pick the repo. `netlify.toml` supplies base `frontend`, build `npm run build`, publish `dist` and the SPA fallback. Before the first deploy, Site configuration -> Environment variables -> add `VITE_API_URL` = the Render URL.
4. **Add `VITE_API_URL` to Netlify** (above) and redeploy if you added it after the first build (Vite bakes it in at build time).
5. **Add `FRONTEND_URL` to Render** (Environment tab) = your Netlify URL, e.g. `https://smartml-demo.netlify.app`, then let Render redeploy. This is what CORS allows; the backend never uses `*`.
6. **Open the public Netlify URL.** Create a project -> Dataset Manager -> *Load sample dataset* -> Training (defaults are demo-sized) -> Evaluation -> Live Prediction.

### Demo mode vs large-scale training
`DEMO_MODE=true` (set by `render.yaml`) caps training for the free CPU: max 15 epochs, batch <= 64, 300 images per project, one training run at a time, 128px images; defaults are 5 epochs / batch 16 / early stopping on. The Training page shows a banner stating the mode. Locally `DEMO_MODE` is unset: no caps, 160px images, so use that for large-scale training. Training is always real TensorFlow/Keras MobileNetV2 transfer learning; nothing is simulated.

The bundled sample dataset (`backend/sample_data`, regenerate with `python make_sample_data.py`) is **synthetic coloured shapes** (circles/squares/triangles) so the demo can train without photos. Replace it with your own images for real use.

### Known free-tier behaviour
- Render Free **sleeps after ~15 minutes of inactivity**; the first request can take about a minute. The UI shows a "backend starting" banner and retries automatically. Open the site a few minutes before your viva.
- The **filesystem is ephemeral**: projects, uploaded images, models and the SQLite database are lost on every restart, redeploy or sleep/wake cycle. Re-create the project and click *Load sample dataset* (seconds).
- Free instances have about 512 MB RAM and a shared CPU. TensorFlow plus MobileNetV2 may run out of memory or train slowly; if training fails with a memory error, use a smaller `IMG_SIZE` (96) or run the backend locally for the viva and keep the Netlify site as the UI preview.
- Model export downloads should be taken immediately after training.
- The Excel analyzer works on any uploaded workbook and keeps results only for the session lifetime of the instance.
- Webcam needs HTTPS (Netlify provides it) and the user's permission; frames are sent to the backend roughly once per second.
