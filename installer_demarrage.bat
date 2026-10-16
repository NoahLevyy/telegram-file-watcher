@echo off
chcp 65001 >nul
setlocal
set "DIR=%~dp0"
set "TASK=TransfertTelegram"

echo ============================================================
echo   Installation du demarrage automatique : %TASK%
echo ============================================================
echo.

schtasks /Create /TN "%TASK%" /SC ONLOGON /RL LIMITED /F /TR "\"%DIR%.venv\Scripts\pythonw.exe\" \"%DIR%transfert_telegram.py\""

if errorlevel 1 (
  echo.
  echo [X] Echec de la creation de la tache.
  echo     Relancez ce fichier en tant qu'administrateur :
  echo     clic droit sur installer_demarrage.bat ^> Executer en tant qu'administrateur.
  echo.
  pause
  exit /b 1
)

echo.
echo [OK] Tache creee : le surveillant demarrera a chaque ouverture de session.
echo      Lancement immediat en arriere-plan...
start "" "%DIR%.venv\Scripts\pythonw.exe" "%DIR%transfert_telegram.py"
echo.
echo Termine ! Deposez un fichier dans le dossier "VersMonTel" pour tester.
echo (Si rien n'arrive sur Telegram : verifiez que .env contient bien
echo  TELEGRAM_TOKEN et TELEGRAM_CHAT_ID.)
echo.
pause
