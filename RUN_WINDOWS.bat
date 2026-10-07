@echo off
REM Smart ML Studio - Windows launcher. Requires Python 3.10-3.12 and Node.js 18+ on PATH.
set ROOT=%~dp0
cd /d "%ROOT%backend"
if not exist venv (
  python -m venv venv || goto :err
  call venv\Scripts\activate && python -m pip install --upgrade pip && pip install -r requirements.txt || goto :err
)
start "SmartML Backend" cmd /k "cd /d %ROOT%backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
cd /d "%ROOT%frontend"
if not exist node_modules ( call npm install || goto :err )
start "SmartML Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"
timeout /t 6 >nul
start http://localhost:5173
exit /b 0
:err
echo Setup failed. See messages above.
pause
exit /b 1
