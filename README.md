# Assistant Telegram pour Windows (PC ⇄ téléphone)

Petit utilitaire Python qui relie ton PC à ton téléphone via un bot Telegram :

- **VersMonTel** : chaque fichier déposé dans le dossier `VersMonTel` part
  automatiquement sur Telegram (avec l'heure en légende).
- **DepuisMonTel** : chaque fichier, photo, vidéo ou vocal envoyé au bot arrive
  dans le dossier `DepuisMonTel` du PC. Un **lien** envoyé au bot s'ouvre dans
  le navigateur ; un autre **texte** est copié dans le presse-papier du PC.
- **Télécommande** : contrôle le PC depuis Telegram.

| Commande | Effet |
|---|---|
| `/capture` | capture d'écran envoyée sur le téléphone |
| `/webcam` | photo prise avec la webcam |
| `/verrouiller` | verrouille la session Windows |
| `/veille` | met le PC en veille |
| `/eteindre [min]` | éteint dans 1 min (ou dans `min` minutes) |
| `/redemarrer [min]` | redémarre dans 1 min |
| `/annuler` | annule une extinction / un redémarrage prévu |
| `/volume 30` | règle le volume (0–100) |
| `/muet` | coupe / remet le son |
| `/batterie` | niveau de batterie |
| `/infos` | RAM, disque, durée depuis l'allumage, batterie |
| `/ip` | IP locale et IP publique |
| `/get nom` | envoie un fichier du PC (DepuisMonTel, VersMonTel, Bureau, Téléchargements, Documents ou chemin complet) |
| `/clip` | envoie le contenu du presse-papier du PC |
| `/popup texte` | affiche un message à l'écran du PC |
| `/aide` | liste des commandes |

Notifications automatiques :
- à chaque **allumage** du PC (ouverture de session) : « 🟢 … est allumé » avec batterie et IP ;
- à chaque **déverrouillage** (retour sur le PC après l'écran de verrouillage) : « 🔓 … déverrouillé ».

Sécurité : le bot **n'obéit qu'au chat défini par `TELEGRAM_CHAT_ID`**. Les
commandes reçues plus de 2 minutes après leur envoi (PC éteint à ce moment-là)
sont ignorées, pour qu'un vieux `/eteindre` n'éteigne pas le PC au démarrage.

Limites de l'API Telegram pour les bots : 20 Mo max pour un fichier reçu
du téléphone, 50 Mo max pour un fichier envoyé par le PC.

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
il part automatiquement sur Telegram. Envoie `/aide` au bot pour la télécommande.

Une seule instance peut tourner à la fois. Le journal est écrit dans
`assistant.log` (pratique quand le script tourne en arrière-plan).

## Remarques

- Surveillance non récursive (dossier de premier niveau uniquement).
- Une pause de 2 s laisse le temps aux gros fichiers de finir d'être écrits.

## Démarrage automatique (Windows, sans droits admin)

- **Installer** : double-clique sur `installer_demarrage.bat`. Il ajoute un petit
  lanceur dans le dossier Démarrage de Windows : le bot démarre **à chaque
  ouverture de session**, sans fenêtre, et `lanceur.vbs` le **relance tout seul
  s'il s'arrête** (plantage, coupure réseau…).
- **Désinstaller** : double-clique sur `desinstaller_demarrage.bat`.

Prérequis : `TELEGRAM_TOKEN` et `TELEGRAM_CHAT_ID` renseignés dans `.env`.

## Mise à jour / arrêt

- `mettre_a_jour.bat` : arrête la version en cours, installe les dépendances
  et relance l'assistant en arrière-plan (à lancer après un `git pull`).
- `arreter.bat` : arrête l'assistant.
