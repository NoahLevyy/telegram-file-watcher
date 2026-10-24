@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   Mise a jour de l'assistant Telegram
echo ============================================================
echo.
echo [1/3] Arret de la version en cours...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*mon-assistant*lanceur.vbs*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*mon-assistant*transfert_telegram.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo      Attente que les fichiers se liberent (antivirus)...
timeout /t 5 >nul

echo [2/3] Installation des dependances...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo      Echec, nouvel essai dans 8 secondes...
  timeout /t 8 >nul
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)
if errorlevel 1 (
  echo.
  echo [X] Installation toujours en echec. Relance ce fichier dans un instant.
  echo.
  pause
  exit /b 1
)

echo [3/3] Relance en arriere-plan (avec relance auto en cas de plantage)...
start "" wscript.exe "%~dp0lanceur.vbs"
echo.
echo [OK] C'est reparti ! Tu dois recevoir "est allume" sur Telegram.
echo      En cas de souci : ouvre le fichier assistant.log
echo.
pause
