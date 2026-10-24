@echo off
chcp 65001 >nul
setlocal
set "DIR=%~dp0"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
echo ============================================================
echo   Installation du demarrage automatique (sans admin)
echo ============================================================
echo.
>"%STARTUP%\Assistant Telegram.vbs" echo CreateObject("WScript.Shell").Run "wscript.exe ""%DIR%lanceur.vbs""", 0, False
if not exist "%STARTUP%\Assistant Telegram.vbs" (
  echo [X] Impossible de creer le raccourci de demarrage.
  pause
  exit /b 1
)
echo [OK] Le bot demarrera tout seul a chaque ouverture de session,
echo      et se relancera tout seul s'il plante.
echo.
echo Arret de l'ancienne version et lancement immediat...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*mon-assistant*lanceur.vbs*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*mon-assistant*transfert_telegram.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 3 >nul
start "" wscript.exe "%DIR%lanceur.vbs"
echo.
echo Termine ! Tu dois recevoir "est allume" sur Telegram.
echo Pour tester : redemarre le PC, le message doit arriver tout seul.
echo.
pause
