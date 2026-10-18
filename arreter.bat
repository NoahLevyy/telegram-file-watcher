@echo off
chcp 65001 >nul
echo Arret de l'assistant Telegram...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*transfert_telegram.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Fait.
timeout /t 2 >nul
