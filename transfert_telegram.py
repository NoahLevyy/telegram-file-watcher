import os
import time
import asyncio
from pathlib import Path
from datetime import datetime

from telegram import Bot
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Dossier du script : tous les chemins (.env, dossier surveillé) sont ancrés ici,
# pour que le programme fonctionne même lancé depuis ailleurs (démarrage automatique).
BASE_DIR = Path(__file__).resolve().parent

# Charge un éventuel fichier .env situé à côté du script (facultatif)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# --- CONFIGURATION (via variables d'environnement / fichier .env) ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
_watch = os.getenv("WATCH_DIRECTORY")
WATCH_DIRECTORY = _watch if _watch else str(BASE_DIR / "VersMonTel")

if not TOKEN or not CHAT_ID:
    raise SystemExit(
        "Configuration manquante : définissez TELEGRAM_TOKEN et TELEGRAM_CHAT_ID "
        "(dans un fichier .env ou des variables d'environnement). Voir .env.example."
    )

bot = Bot(token=TOKEN)


async def send_to_telegram(file_path):
    file_name = os.path.basename(file_path)
    heure = datetime.now().strftime("%H:%M:%S")
    print(f"[{heure}] 🚀 Envoi de : {file_name}")
    try:
        with open(file_path, 'rb') as f:
            await bot.send_document(chat_id=CHAT_ID, document=f, caption=f"Reçu à {heure}")
        print(f"[{heure}] ✅ Reçu sur Telegram !")
    except Exception as e:
        print(f"[{heure}] ❌ Erreur : {e}")


class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            time.sleep(2)  # laisse le temps aux gros fichiers d'être écrits
            asyncio.run(send_to_telegram(event.src_path))


if __name__ == "__main__":
    if not os.path.exists(WATCH_DIRECTORY):
        os.makedirs(WATCH_DIRECTORY)

    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIRECTORY, recursive=False)

    start_time = datetime.now().strftime("%H:%M:%S")
    print(f"[{start_time}] 📡 Surveillant Telegram actif sur {WATCH_DIRECTORY}")
    print(f"[{start_time}] Attente de fichiers...")

    observer.start()
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
