# Surveillant Telegram (file watcher → Telegram)

Petit utilitaire Python : il surveille un dossier et envoie automatiquement
sur Telegram, via un bot, chaque nouveau fichier qui y apparaît (avec l'heure
de réception en légende). Pratique pour s'envoyer rapidement un fichier du PC
vers son téléphone.

## Installation

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate   |   Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

1. Crée un bot avec [@BotFather](https://t.me/BotFather) et récupère son **token**.
2. Récupère ton **chat_id** (par ex. via [@userinfobot](https://t.me/userinfobot)).
3. Copie `.env.example` en `.env` et renseigne tes valeurs :

```bash
cp .env.example .env
```

```
TELEGRAM_TOKEN=le_token_de_ton_bot
TELEGRAM_CHAT_ID=ton_chat_id
WATCH_DIRECTORY=./VersMonTel
```

> Le fichier `.env` contient des secrets : il est ignoré par git et ne doit
> jamais être publié.

## Utilisation

```bash
python transfert_telegram.py
```

Dépose un fichier dans le dossier surveillé (`./VersMonTel` par défaut) :
il part automatiquement sur Telegram.

## Remarques

- Surveillance non récursive (dossier de premier niveau uniquement).
- Une pause de 2 s laisse le temps aux gros fichiers de finir d'être écrits.

## Démarrage automatique (Windows)

Pour que le surveillant tourne en permanence sans avoir à le lancer à la main :

- **Installer** : double-cliquez sur `installer_demarrage.bat`.
  Cela crée une tâche planifiée qui démarre le script **à chaque ouverture de
  session**, en arrière-plan et **sans fenêtre** (via `pythonw.exe`), et le lance
  immédiatement.
- **Désinstaller** : double-cliquez sur `desinstaller_demarrage.bat`.

Prérequis : avoir renseigné `TELEGRAM_TOKEN` et `TELEGRAM_CHAT_ID` dans `.env`
(voir `.env.example`). Si la création de la tâche échoue, relancez le `.bat` en
tant qu'administrateur (clic droit → Exécuter en tant qu'administrateur).
