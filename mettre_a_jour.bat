@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   Mise a jour de l'assistant Telegram
echo ============================================================
echo.
echo [1/3] Arret de la version en cours...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*transfert_telegram.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
timeout /t 2 >nul
echo [2/3] Installation des dependances...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo [X] Echec de l'installation des dependances.
  pause
  exit /b 1
)
echo [3/3] Relance en arriere-plan...
start "" ".venv\Scripts\pythonw.exe" "%~dp0transfert_telegram.py"
echo.
echo [OK] C'est reparti ! Tu dois recevoir "est allume" sur Telegram.
echo      Envoie /aide au bot pour voir les commandes.
echo      (En cas de souci : regarde le fichier assistant.log)
echo.
pause
