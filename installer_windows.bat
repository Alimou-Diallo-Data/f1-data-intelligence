@echo off
cd /d "%~dp0"
python -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo Installation terminee. Lance maintenant lancer_dashboard.bat
pause
