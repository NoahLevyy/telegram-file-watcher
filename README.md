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
