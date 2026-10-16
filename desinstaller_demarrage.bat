@echo off
chcp 65001 >nul
set "TASK=TransfertTelegram"
echo Suppression du demarrage automatique (%TASK%)...
schtasks /Delete /TN "%TASK%" /F
echo.
echo Fait. Le script ne demarrera plus automatiquement.
echo (Une instance deja lancee s'arretera au prochain redemarrage du PC.)
echo.
pause
