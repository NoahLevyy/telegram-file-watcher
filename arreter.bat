@echo off
chcp 65001 >nul
echo Arret de l'assistant Telegram...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*mon-assistant*lanceur.vbs*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*mon-assistant*transfert_telegram.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo Fait. (Il redemarrera au prochain allumage du PC.)
timeout /t 2 >nul
