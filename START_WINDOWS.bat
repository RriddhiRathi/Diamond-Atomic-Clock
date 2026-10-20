@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run: follow README.md to install Python and create the virtual environment.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
