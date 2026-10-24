@echo off
chcp 65001 >nul
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
echo Suppression du demarrage automatique...
if exist "%STARTUP%\Assistant Telegram.vbs" del "%STARTUP%\Assistant Telegram.vbs"
schtasks /Delete /TN "TransfertTelegram" /F >nul 2>&1
echo Arret du bot...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*mon-assistant*lanceur.vbs*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*mon-assistant*transfert_telegram.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo.
echo Fait. Le bot ne demarrera plus automatiquement.
echo.
pause
