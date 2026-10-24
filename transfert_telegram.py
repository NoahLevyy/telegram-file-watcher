"""
Assistant Telegram pour Windows.

- VersMonTel   : tout fichier déposé dans le dossier VersMonTel part sur Telegram.
- DepuisMonTel : tout fichier/photo/vidéo envoyé au bot arrive dans le dossier DepuisMonTel.
                 Un lien envoyé au bot s'ouvre dans le navigateur ; un autre texte
                 est copié dans le presse-papier du PC.
- Télécommande : /capture, /verrouiller, /veille, /eteindre, /volume... (voir /aide).

Le bot n'obéit qu'au chat défini par TELEGRAM_CHAT_ID.
"""
import asyncio
import ctypes
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Dossier du script : tous les chemins sont ancrés ici (utile au démarrage automatique).
BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# --- CONFIGURATION (.env) ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WATCH_DIRECTORY = Path(os.getenv("WATCH_DIRECTORY") or BASE_DIR / "VersMonTel")
INBOX_DIRECTORY = Path(os.getenv("INBOX_DIRECTORY") or BASE_DIR / "DepuisMonTel")
if not WATCH_DIRECTORY.is_absolute():
    WATCH_DIRECTORY = (BASE_DIR / WATCH_DIRECTORY).resolve()
if not INBOX_DIRECTORY.is_absolute():
    INBOX_DIRECTORY = (BASE_DIR / INBOX_DIRECTORY).resolve()

if not TOKEN or not CHAT_ID:
    raise SystemExit(
        "Configuration manquante : définissez TELEGRAM_TOKEN et TELEGRAM_CHAT_ID "
        "dans le fichier .env (voir .env.example)."
    )
CHAT_ID = int(CHAT_ID)

# Une commande reçue plus de 2 min après son envoi (PC éteint à ce moment-là)
# est ignorée : évite qu'un vieux /eteindre éteigne le PC dès qu'on l'allume.
MAX_AGE_SECONDS = 120
SINGLE_INSTANCE_PORT = 47821
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# --- JOURNAL (utile car en arrière-plan rien ne s'affiche) ---
log = logging.getLogger("assistant")
log.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
_fh = RotatingFileHandler(BASE_DIR / "assistant.log", maxBytes=1_000_000, backupCount=1, encoding="utf-8")
_fh.setFormatter(_fmt)
log.addHandler(_fh)
if sys.stdout is not None:  # fenêtre visible (pas pythonw)
    _sh = logging.StreamHandler(sys.stdout)
    _sh.setFormatter(_fmt)
    log.addHandler(_sh)
logging.getLogger("httpx").setLevel(logging.WARNING)

IS_WINDOWS = os.name == "nt"
if IS_WINDOWS:
    try:  # capture d'écran nette sur les écrans haute résolution
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# =====================================================================
#  Outils Windows
# =====================================================================

def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, creationflags=NO_WINDOW)


def press_key(vk: int, times: int = 1) -> None:
    for _ in range(times):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP
        time.sleep(0.01)


VK_VOLUME_MUTE, VK_VOLUME_DOWN, VK_VOLUME_UP = 0xAD, 0xAE, 0xAF


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def battery_text() -> str:
    s = SYSTEM_POWER_STATUS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
        return "🔋 Batterie : inconnue"
    pct = s.BatteryLifePercent & 0xFF
    if (s.BatteryFlag & 0xFF) == 128 or pct == 255:
        return "🔌 Pas de batterie (PC fixe ou batterie absente)"
    secteur = "en charge 🔌" if s.ACLineStatus == 1 else "sur batterie"
    txt = f"🔋 Batterie : {pct} % ({secteur})"
    if s.ACLineStatus != 1 and s.BatteryLifeTime not in (0xFFFFFFFF, -1):
        h, m = divmod(s.BatteryLifeTime // 60, 60)
        txt += f", environ {h} h {m:02d} restantes"
    return txt


def system_text() -> str:
    mem = MEMORYSTATUSEX()
    mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
    used = (mem.ullTotalPhys - mem.ullAvailPhys) / 2**30
    total = mem.ullTotalPhys / 2**30
    disk = shutil.disk_usage(Path.home().anchor)
    up = ctypes.windll.kernel32.GetTickCount64() // 1000
    d, rem = divmod(up, 86400)
    h, m = divmod(rem // 60, 60)
    uptime = (f"{d} j " if d else "") + f"{h} h {m:02d}"
    return (
        f"💻 {socket.gethostname()}\n"
        f"🧠 RAM : {used:.1f} / {total:.1f} Go ({mem.dwMemoryLoad} %)\n"
        f"💾 Disque {Path.home().anchor} : {disk.free / 2**30:.0f} Go libres sur {disk.total / 2**30:.0f} Go\n"
        f"⏱️ Allumé depuis {uptime}\n"
        f"{battery_text()}"
    )


def local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # n'envoie rien, sert juste à trouver l'interface
        return s.getsockname()[0]
    except OSError:
        return "inconnue"
    finally:
        s.close()


def set_clipboard(text: str) -> None:
    subprocess.run(["clip"], input=text.encode("utf-16"), check=True, creationflags=NO_WINDOW)


def get_clipboard() -> str:
    r = run(["powershell", "-NoProfile", "-Command",
             "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Clipboard -Raw"])
    return r.stdout.decode("utf-8", errors="replace").strip()


def screenshot_png() -> bytes:
    import mss
    import mss.tools
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[0])  # tous les écrans
        return mss.tools.to_png(shot.rgb, shot.size)


def webcam_jpeg() -> bytes:
    """Prend une photo avec la webcam et la renvoie en JPEG."""
    import cv2
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # CAP_DSHOW : démarrage plus rapide sur Windows
    if not cam.isOpened():
        cam.release()
        raise RuntimeError("Aucune webcam détectée (ou déjà utilisée par une autre application).")
    try:
        # Les premières images sont noires/sombres le temps que le capteur s'ajuste.
        frame = None
        for _ in range(10):
            ok, f = cam.read()
            if ok:
                frame = f
            time.sleep(0.05)
        if frame is None:
            raise RuntimeError("La webcam n'a renvoyé aucune image.")
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            raise RuntimeError("Échec de l'encodage de l'image.")
        return buf.tobytes()
    finally:
        cam.release()


def popup(text: str) -> None:
    # MB_ICONINFORMATION | MB_SYSTEMMODAL | MB_SETFOREGROUND
    threading.Thread(
        target=ctypes.windll.user32.MessageBoxW,
        args=(None, text, "Message depuis ton téléphone", 0x40 | 0x1000 | 0x10000),
        daemon=True,
    ).start()


def search_dirs() -> list[Path]:
    home = Path.home()
    candidates = [INBOX_DIRECTORY, WATCH_DIRECTORY,
                  home / "Desktop", home / "Downloads", home / "Documents",
                  home / "OneDrive" / "Desktop", home / "OneDrive" / "Bureau",
                  home / "OneDrive" / "Documents"]
    return [d for d in candidates if d.is_dir()]


def find_files(name: str) -> list[Path]:
    p = Path(name.strip('"'))
    if p.is_absolute():
        return [p] if p.is_file() else []
    name_l = name.lower()
    exact, partial = [], []
    for d in search_dirs():
        try:
            for f in d.iterdir():
                if f.is_file():
                    if f.name.lower() == name_l:
                        exact.append(f)
                    elif name_l in f.name.lower():
                        partial.append(f)
        except OSError:
            continue
    return exact or partial


def unique_path(folder: Path, filename: str) -> Path:
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename) or "fichier"
    target = folder / filename
    stem, suffix, i = target.stem, target.suffix, 1
    while target.exists():
        target = folder / f"{stem} ({i}){suffix}"
        i += 1
    return target


# =====================================================================
#  Commandes Telegram
# =====================================================================

AIDE = """🤖 *Télécommande du PC*

📸 /capture : capture d'écran
📷 /webcam : photo prise avec la webcam
🔒 /verrouiller : verrouille la session
😴 /veille : met le PC en veille
⏻ /eteindre : éteint dans 1 min (/eteindre 10 = dans 10 min)
🔄 /redemarrer : redémarre dans 1 min
❌ /annuler : annule l'extinction/le redémarrage
🔊 /volume 30 : règle le volume (0 à 100)
🔇 /muet : coupe/remet le son
🔋 /batterie : niveau de batterie
💻 /infos : RAM, disque, allumé depuis…
🌐 /ip : adresses IP
📁 /get nom : récupère un fichier du PC
📋 /clip : récupère le presse-papier du PC
💬 /popup texte : affiche un message sur l'écran

📥 *DepuisMonTel*
Envoie un fichier, une photo ou une vidéo : il arrive dans le dossier DepuisMonTel.
Envoie un lien : il s'ouvre sur le PC.
Envoie un autre texte : il est copié dans le presse-papier du PC."""

MENU = [
    ("aide", "Liste des commandes"),
    ("capture", "Capture d'écran"),
    ("webcam", "Photo webcam"),
    ("verrouiller", "Verrouiller la session"),
    ("veille", "Mettre en veille"),
    ("eteindre", "Éteindre (minutes en option)"),
    ("redemarrer", "Redémarrer"),
    ("annuler", "Annuler extinction/redémarrage"),
    ("volume", "Régler le volume (0-100)"),
    ("muet", "Couper/remettre le son"),
    ("batterie", "Niveau de batterie"),
    ("infos", "Infos système"),
    ("ip", "Adresses IP"),
    ("get", "Récupérer un fichier"),
    ("clip", "Récupérer le presse-papier"),
    ("popup", "Afficher un message à l'écran"),
]


def too_old(update: Update) -> bool:
    msg = update.effective_message
    return (datetime.now(timezone.utc) - msg.date).total_seconds() > MAX_AGE_SECONDS


async def guard(update: Update) -> bool:
    """True si la commande doit être ignorée (envoyée quand le PC était éteint)."""
    if too_old(update):
        await update.effective_message.reply_text(
            "⏳ Commande ignorée : envoyée quand le PC était éteint ou hors ligne.")
        return True
    log.info("Commande : %s", update.effective_message.text)
    return False


async def cmd_aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(AIDE, parse_mode="Markdown")


async def cmd_capture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    png = await asyncio.to_thread(screenshot_png)
    await update.effective_message.reply_document(
        document=png, filename=f"capture_{datetime.now():%Y-%m-%d_%H-%M-%S}.png")


async def cmd_webcam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    try:
        jpg = await asyncio.to_thread(webcam_jpeg)
    except Exception as e:
        await update.effective_message.reply_text(f"📷 {e}")
        return
    await update.effective_message.reply_photo(
        photo=jpg, caption=f"📷 Webcam — {datetime.now():%H:%M:%S}")


async def cmd_verrouiller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    ctypes.windll.user32.LockWorkStation()
    await update.effective_message.reply_text("🔒 PC verrouillé.")


async def cmd_veille(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    await update.effective_message.reply_text("😴 Mise en veille… (je ne répondrai plus jusqu'au réveil)")
    await asyncio.sleep(2)
    ctypes.windll.powrprof.SetSuspendState(0, 1, 0)


def _minutes(context: ContextTypes.DEFAULT_TYPE, default: int = 1) -> int:
    try:
        return max(0, int(context.args[0])) if context.args else default
    except ValueError:
        return default


async def cmd_eteindre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    m = _minutes(context)
    r = run(["shutdown", "/s", "/t", str(m * 60)])
    if r.returncode == 0:
        await update.effective_message.reply_text(
            f"⏻ Extinction dans {m} min. /annuler pour l'arrêter.")
    else:
        await update.effective_message.reply_text("❌ Impossible (une extinction est peut-être déjà prévue : /annuler).")


async def cmd_redemarrer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    m = _minutes(context)
    r = run(["shutdown", "/r", "/t", str(m * 60)])
    if r.returncode == 0:
        await update.effective_message.reply_text(
            f"🔄 Redémarrage dans {m} min. /annuler pour l'arrêter.")
    else:
        await update.effective_message.reply_text("❌ Impossible (déjà prévu ? /annuler).")


async def cmd_annuler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    r = run(["shutdown", "/a"])
    txt = "✅ Extinction/redémarrage annulé." if r.returncode == 0 else "ℹ️ Rien n'était prévu."
    await update.effective_message.reply_text(txt)


async def cmd_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    try:
        level = max(0, min(100, int(context.args[0])))
    except (IndexError, ValueError):
        await update.effective_message.reply_text("Utilisation : /volume 30 (de 0 à 100)")
        return
    # Chaque appui sur une touche volume = 2 % : on descend à 0 puis on remonte.
    def _set():
        press_key(VK_VOLUME_DOWN, 50)
        press_key(VK_VOLUME_UP, round(level / 2))
    await asyncio.to_thread(_set)
    await update.effective_message.reply_text(f"🔊 Volume réglé à {round(level / 2) * 2} %.")


async def cmd_muet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    press_key(VK_VOLUME_MUTE)
    await update.effective_message.reply_text("🔇 Son coupé / remis.")


async def cmd_batterie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    await update.effective_message.reply_text(battery_text())


async def cmd_infos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    await update.effective_message.reply_text(await asyncio.to_thread(system_text))


async def cmd_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            public = (await client.get("https://api.ipify.org")).text.strip()
    except Exception:
        public = "inconnue"
    await update.effective_message.reply_text(
        f"🏠 IP locale : {local_ip()}\n🌍 IP publique : {public}")


async def cmd_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    name = " ".join(context.args).strip()
    if not name:
        await update.effective_message.reply_text(
            "Utilisation : /get nom_du_fichier\n"
            "Je cherche dans DepuisMonTel, VersMonTel, Bureau, Téléchargements et Documents "
            "(ou donne un chemin complet).")
        return
    found = await asyncio.to_thread(find_files, name)
    if not found:
        await update.effective_message.reply_text(f"🔍 Aucun fichier trouvé pour « {name} ».")
        return
    if len(found) > 1:
        liste = "\n".join(f"• {f.name}" for f in found[:15])
        await update.effective_message.reply_text(
            f"Plusieurs fichiers correspondent, précise le nom :\n{liste}")
        return
    f = found[0]
    if f.stat().st_size > 50 * 2**20:
        await update.effective_message.reply_text("📦 Fichier trop gros pour un bot Telegram (50 Mo max).")
        return
    with open(f, "rb") as fh:
        await update.effective_message.reply_document(document=fh, filename=f.name)


async def cmd_clip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    text = await asyncio.to_thread(get_clipboard)
    if not text:
        await update.effective_message.reply_text("📋 Presse-papier vide (ou ce n'est pas du texte).")
    else:
        await update.effective_message.reply_text(text[:4000])


async def cmd_popup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await guard(update):
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.effective_message.reply_text("Utilisation : /popup ton message")
        return
    popup(text)
    await update.effective_message.reply_text("💬 Message affiché sur le PC.")


# =====================================================================
#  DepuisMonTel : fichiers, liens et texte reçus
# =====================================================================

async def on_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if msg.document:
        tg_file, name = msg.document, msg.document.file_name or f"fichier_{stamp}"
    elif msg.photo:
        tg_file, name = msg.photo[-1], f"photo_{stamp}.jpg"  # meilleure résolution
    elif msg.video:
        tg_file, name = msg.video, msg.video.file_name or f"video_{stamp}.mp4"
    elif msg.audio:
        tg_file, name = msg.audio, msg.audio.file_name or f"audio_{stamp}.mp3"
    elif msg.voice:
        tg_file, name = msg.voice, f"vocal_{stamp}.ogg"
    elif msg.video_note:
        tg_file, name = msg.video_note, f"video_ronde_{stamp}.mp4"
    else:
        return

    if (tg_file.file_size or 0) > 20 * 2**20:
        await msg.reply_text("📦 Trop gros : un bot Telegram ne peut télécharger que 20 Mo max.")
        return

    INBOX_DIRECTORY.mkdir(parents=True, exist_ok=True)
    target = unique_path(INBOX_DIRECTORY, name)
    f = await tg_file.get_file()
    await f.download_to_drive(target)
    log.info("Reçu du téléphone : %s", target.name)
    await msg.reply_text(f"📥 Enregistré sur le PC : DepuisMonTel\\{target.name}")


URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    text = msg.text or ""
    urls = URL_RE.findall(text)
    if too_old(update):
        await msg.reply_text("⏳ Reçu pendant que le PC était éteint : je n'ouvre/copie rien.")
        return
    if urls:
        for u in urls:
            webbrowser.open(u)
        log.info("Lien(s) ouvert(s) : %s", urls)
        await msg.reply_text("🌐 Ouvert sur le PC." if len(urls) == 1 else f"🌐 {len(urls)} liens ouverts sur le PC.")
    else:
        await asyncio.to_thread(set_clipboard, text)
        await msg.reply_text("📋 Copié dans le presse-papier du PC (Ctrl+V pour coller).")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error("Erreur : %s", context.error, exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(f"❌ Erreur : {context.error}")
        except Exception:
            pass


# =====================================================================
#  VersMonTel : surveillance du dossier
# =====================================================================

class VersMonTelHandler(FileSystemEventHandler):
    def __init__(self, app: Application, loop: asyncio.AbstractEventLoop):
        self.app, self.loop = app, loop

    def on_created(self, event):
        if event.is_directory:
            return
        time.sleep(2)  # laisse le temps aux gros fichiers d'être écrits
        asyncio.run_coroutine_threadsafe(self.send(Path(event.src_path)), self.loop)

    async def send(self, path: Path):
        heure = datetime.now().strftime("%H:%M:%S")
        try:
            with open(path, "rb") as f:
                await self.app.bot.send_document(chat_id=CHAT_ID, document=f,
                                                 filename=path.name, caption=f"Reçu à {heure}")
            log.info("Envoyé sur Telegram : %s", path.name)
        except Exception as e:
            log.error("Échec d'envoi de %s : %s", path.name, e)


observer = None


# =====================================================================
#  Détection verrouillage / déverrouillage de la session Windows
# =====================================================================

def session_watcher(app: Application, loop: asyncio.AbstractEventLoop):
    """
    Écoute les événements de session Windows et notifie sur Telegram au
    déverrouillage (retour sur le PC après l'écran de verrouillage).
    Tout est défini localement pour que le module reste importable hors Windows.
    """
    if not IS_WINDOWS:
        return

    LRESULT = ctypes.c_ssize_t
    HWND = ctypes.c_void_p
    UINT = ctypes.c_uint
    WPARAM = ctypes.c_size_t
    LPARAM = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)

    WM_WTSSESSION_CHANGE = 0x02B1
    WTS_SESSION_LOCK = 0x7
    WTS_SESSION_UNLOCK = 0x8
    NOTIFY_FOR_THIS_SESSION = 0
    HWND_MESSAGE = ctypes.c_void_p(-3)

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    wtsapi32 = ctypes.windll.wtsapi32

    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [HWND, UINT, WPARAM, LPARAM]
    user32.CreateWindowExW.restype = HWND
    user32.CreateWindowExW.argtypes = [ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_wchar_p,
                                       ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                       ctypes.c_int, HWND, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_void_p]
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    wtsapi32.WTSRegisterSessionNotification.restype = ctypes.c_int
    wtsapi32.WTSRegisterSessionNotification.argtypes = [HWND, ctypes.c_uint]

    async def notify_unlock():
        heure = datetime.now().strftime("%H:%M")
        try:
            await app.bot.send_message(
                CHAT_ID, f"🔓 {socket.gethostname()} déverrouillé ({heure}).")
        except Exception as e:
            log.warning("Notif déverrouillage non envoyée : %s", e)

    def wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_WTSSESSION_CHANGE:
            if wparam == WTS_SESSION_UNLOCK:
                log.info("Session déverrouillée")
                asyncio.run_coroutine_threadsafe(notify_unlock(), loop)
            elif wparam == WTS_SESSION_LOCK:
                log.info("Session verrouillée")
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    class WNDCLASS(ctypes.Structure):
        _fields_ = [("style", UINT), ("lpfnWndProc", WNDPROC),
                    ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                    ("hInstance", ctypes.c_void_p), ("hIcon", ctypes.c_void_p),
                    ("hCursor", ctypes.c_void_p), ("hbrBackground", ctypes.c_void_p),
                    ("lpszMenuName", ctypes.c_wchar_p), ("lpszClassName", ctypes.c_wchar_p)]

    class MSG(ctypes.Structure):
        _fields_ = [("hwnd", HWND), ("message", UINT), ("wParam", WPARAM),
                    ("lParam", LPARAM), ("time", ctypes.c_uint),
                    ("pt_x", ctypes.c_long), ("pt_y", ctypes.c_long)]

    proc = WNDPROC(wndproc)  # garder une référence vivante (sinon crash)
    try:
        hinst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASS()
        wc.lpfnWndProc = proc
        wc.hInstance = hinst
        wc.lpszClassName = "AssistantTelegramSessionWatcher"
        user32.RegisterClassW(ctypes.byref(wc))
        hwnd = user32.CreateWindowExW(0, wc.lpszClassName, "watcher", 0, 0, 0, 0, 0,
                                      HWND_MESSAGE, None, hinst, None)
        if not hwnd:
            log.warning("Watcher session : fenêtre non créée (err %s)", kernel32.GetLastError())
            return
        if not wtsapi32.WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_THIS_SESSION):
            log.warning("Watcher session : abonnement échoué (err %s)", kernel32.GetLastError())
            return
        log.info("Watcher session (verrouillage/déverrouillage) actif.")
        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except Exception as e:
        log.warning("Watcher session arrêté : %s", e)


async def post_init(app: Application):
    global observer
    WATCH_DIRECTORY.mkdir(parents=True, exist_ok=True)
    INBOX_DIRECTORY.mkdir(parents=True, exist_ok=True)
    observer = Observer()
    observer.schedule(VersMonTelHandler(app, asyncio.get_running_loop()), str(WATCH_DIRECTORY), recursive=False)
    observer.start()
    threading.Thread(target=session_watcher, args=(app, asyncio.get_running_loop()),
                     daemon=True).start()
    try:
        await app.bot.set_my_commands([BotCommand(c, d) for c, d in MENU])
        heure = datetime.now().strftime("%H:%M")
        batt = await asyncio.to_thread(battery_text)
        await app.bot.send_message(
            CHAT_ID,
            f"🟢 *{socket.gethostname()}* est allumé ({heure}).\n"
            f"{batt}\n🏠 IP locale : {local_ip()}\n\n/aide pour les commandes.",
            parse_mode="Markdown",
        )
    except Exception as e:
        log.warning("Message de démarrage non envoyé : %s", e)
    log.info("Assistant actif. VersMonTel=%s DepuisMonTel=%s", WATCH_DIRECTORY, INBOX_DIRECTORY)


async def post_shutdown(app: Application):
    if observer:
        observer.stop()
        observer.join(timeout=5)


def main():
    # Une seule instance à la fois (sinon Telegram refuse : "Conflict").
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
    except OSError:
        log.warning("Déjà en cours d'exécution : cette nouvelle instance s'arrête.")
        print("L'assistant tourne déjà en arrière-plan. Lance arreter.bat pour l'arrêter d'abord.")
        sys.exit(3)  # code 3 = déjà lancé : le lanceur (lanceur.vbs) ne relance pas

    app = (Application.builder().token(TOKEN)
           # délais réseau généreux : évite les "Timed out" sur une photo/vidéo un peu lourde
           .read_timeout(60).write_timeout(60).media_write_timeout(120).connect_timeout(30)
           .post_init(post_init).post_shutdown(post_shutdown).build())

    me = filters.Chat(chat_id=CHAT_ID)
    commands = {
        ("aide", "help", "start"): cmd_aide,
        ("capture", "screenshot"): cmd_capture,
        ("webcam", "photo"): cmd_webcam,
        ("verrouiller", "lock"): cmd_verrouiller,
        ("veille", "sleep"): cmd_veille,
        ("eteindre", "shutdown"): cmd_eteindre,
        ("redemarrer", "restart"): cmd_redemarrer,
        ("annuler", "cancel"): cmd_annuler,
        ("volume",): cmd_volume,
        ("muet", "mute"): cmd_muet,
        ("batterie", "battery"): cmd_batterie,
        ("infos", "info"): cmd_infos,
        ("ip",): cmd_ip,
        ("get",): cmd_get,
        ("clip",): cmd_clip,
        ("popup",): cmd_popup,
    }
    for names, fn in commands.items():
        app.add_handler(CommandHandler(list(names), fn, filters=me))

    media = (filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO
             | filters.VOICE | filters.VIDEO_NOTE)
    app.add_handler(MessageHandler(me & media, on_file))
    app.add_handler(MessageHandler(me & filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    log.info("Démarrage…")
    # bootstrap_retries=-1 : réessaie indéfiniment si Internet n'est pas encore là au démarrage
    app.run_polling(bootstrap_retries=-1, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
