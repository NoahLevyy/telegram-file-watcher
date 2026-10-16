import os
import time
import asyncio
from datetime import datetime

from telegram import Bot
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Charge un éventuel fichier .env (facultatif)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONFIGURATION (via variables d'environnement / fichier .env) ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WATCH_DIRECTORY = os.getenv("WATCH_DIRECTORY", "./VersMonTel")

if not TOKEN or not CHAT_ID:
    raise SystemExit(
        "Configuration manquante : définissez TELEGRAM_TOKEN et TELEGRAM_CHAT_ID "
        "(dans un fichier .env ou des variables d'environnement). Voir .env.example."
    )

bot = Bot(token=TOKEN)


async def send_to_telegram(file_path):
    file_name = os.path.basename(file_path)
    # On récupère l'heure précise au moment de l'envoi
    heure = datetime.now().strftime("%H:%M:%S")

    print(f"[{heure}] 🚀 Envoi de : {file_name}")

    try:
        with open(file_path, 'rb') as f:
            # On envoie le document avec l'heure en légende sur Telegram
            await bot.send_document(chat_id=CHAT_ID, document=f, caption=f"Reçu à {heure}")
        print(f"[{heure}] ✅ Reçu sur Telegram !")
    except Exception as e:
        print(f"[{heure}] ❌ Erreur : {e}")


class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            # On laisse 2 secondes pour les gros fichiers (PDF)
            time.sleep(2)
            asyncio.run(send_to_telegram(event.src_path))


if __name__ == "__main__":
    if not os.path.exists(WATCH_DIRECTORY):
        os.makedirs(WATCH_DIRECTORY)

    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIRECTORY, recursive=False)

    # Heure de lancement du script
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
