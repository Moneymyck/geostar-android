#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEOSTAR ADMIN — Application de gestion des licences
====================================================
Gestion complète des codes d'activation GEOSTAR :
- Création de codes avec tarifs
- Synchronisation automatique avec GitHub
- QR codes (visuel + interactif)
- Statistiques et revenus
- Multi-admins avec logs
- Export CSV
"""

# --- IMPORTS STANDARDS ---
import json
import os
import re
import random
import hashlib
import base64
import csv
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# --- KIVY ---
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line

# ============================================================
# CONFIGURATION
# ============================================================

ADMIN_VERSION = "1.0"

# Couleurs disponibles pour les tarifs
COULEURS_TARIF = {
    "Bleu":   [0.2, 0.5, 0.8, 1],
    "Vert":   [0.1, 0.65, 0.3, 1],
    "Or":     [0.7, 0.5, 0.0, 1],
    "Violet": [0.5, 0.2, 0.7, 1],
    "Orange": [0.8, 0.45, 0.1, 1],
    "Rouge":  [0.75, 0.2, 0.2, 1],
    "Cyan":   [0.1, 0.65, 0.7, 1],
    "Rose":   [0.75, 0.25, 0.5, 1],
}

# Tarifs par defaut (si aucun fichier local)
TARIFS_DEFAUT = {
    "1 mois": {"duree_jours": 30,    "prix": 5.0,  "monnaie": "EUR", "couleur": [0.2, 0.5, 0.8, 1]},
    "1 an":   {"duree_jours": 365,   "prix": 30.0, "monnaie": "EUR", "couleur": [0.1, 0.65, 0.3, 1]},
    "À vie":  {"duree_jours": 18250, "prix": 0.0,  "monnaie": "EUR", "couleur": [0.7, 0.5, 0.0, 1]},
}


def load_tarifs():
    """Charge les tarifs depuis fichier local ou retourne les defauts."""
    import os
    base = os.path.expanduser("~")
    if platform == "android":
        try:
            from android.storage import app_storage_path
            base = app_storage_path()
        except Exception:
            pass
    path = os.path.join(base, "geostar_tarifs.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data:
                return data
    except Exception:
        pass
    return dict(TARIFS_DEFAUT)


def save_tarifs(tarifs):
    """Sauvegarde les tarifs dans le fichier local."""
    import os
    base = os.path.expanduser("~")
    if platform == "android":
        try:
            from android.storage import app_storage_path
            base = app_storage_path()
        except Exception:
            pass
    path = os.path.join(base, "geostar_tarifs.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tarifs, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


# TARIFS global — charge au demarrage, modifiable depuis Parametres
TARIFS = load_tarifs()


# Caractères pour générer les codes (sans I, O, 0, 1 pour éviter confusion)
CHARS_CODE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_REGEX = re.compile(r"^GEO-[A-Z0-9]{4}$")

# Couleurs de l'interface
C_BG       = (0.08, 0.08, 0.10, 1)
C_PANEL    = (0.12, 0.14, 0.18, 1)
C_GOLD     = (1.0,  0.80, 0.10, 1)
C_GREEN    = (0.1,  0.75, 0.3,  1)
C_RED      = (0.85, 0.2,  0.2,  1)
C_ORANGE   = (0.95, 0.55, 0.1,  1)
C_BLUE     = (0.2,  0.5,  0.9,  1)
C_GREY     = (0.35, 0.35, 0.40, 1)
C_TEXT     = (1.0,  1.0,  1.0,  1)
C_SUBTEXT  = (0.7,  0.7,  0.75, 1)

# ============================================================
# STOCKAGE LOCAL
# ============================================================

def _data_path():
    if platform == "android":
        try:
            from android.storage import app_storage_path
            return app_storage_path()
        except Exception:
            pass
    return os.path.expanduser("~")


def _file(name):
    return os.path.join(_data_path(), name)


def load_json(name, default=None):
    try:
        with open(_file(name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def save_json(name, data):
    try:
        with open(_file(name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


# ============================================================
# GESTION DES ADMINS
# ============================================================

def hash_password(pwd):
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


def load_admins():
    return load_json("geostar_admins.json", {"admins": [], "logs": []})


def save_admins(data):
    return save_json("geostar_admins.json", data)


def admin_exists():
    d = load_admins()
    return len(d.get("admins", [])) > 0


def create_admin(username, password):
    d = load_admins()
    admins = d.get("admins", [])
    for a in admins:
        if a["username"] == username:
            return False, "Utilisateur déjà existant"
    admins.append({
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "role": "admin"
    })
    d["admins"] = admins
    save_admins(d)
    return True, "Admin créé"


def verify_admin(username, password):
    d = load_admins()
    for a in d.get("admins", []):
        if a["username"] == username and a["password_hash"] == hash_password(password):
            return True
    return False


def log_action(username, action, detail=""):
    d = load_admins()
    logs = d.get("logs", [])
    logs.insert(0, {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "admin": username,
        "action": action,
        "detail": detail
    })
    d["logs"] = logs[:200]  # garder les 200 derniers logs
    save_admins(d)


# ============================================================
# GESTION DES CODES
# ============================================================

def load_codes():
    return load_json("codes_geostar.json", {
        "codes_valides": {},
        "codes_bloques": [],
        "derniere_maj": datetime.now().strftime("%Y-%m-%d")
    })


def save_codes(data):
    data["derniere_maj"] = datetime.now().strftime("%Y-%m-%d")
    return save_json("codes_geostar.json", data)


def generer_code(codes_existants):
    for _ in range(1000):
        suffix = "".join(random.choices(CHARS_CODE, k=4))
        code = f"GEO-{suffix}"
        if code not in codes_existants:
            return code
    return None


def get_code_status(code, data):
    """Retourne le statut d'un code : 'actif', 'bloque', 'expire'"""
    bloques = data.get("codes_bloques", [])
    valides = data.get("codes_valides", {})

    if code in bloques:
        return "bloque"
    if code not in valides:
        return "inconnu"

    info = valides[code]
    expire_str = info.get("expire", "")
    if expire_str:
        try:
            if datetime.now() > datetime.strptime(expire_str, "%Y-%m-%d"):
                return "expire"
        except Exception:
            pass
    return "actif"


def jours_restants(expire_str):
    if not expire_str:
        return None
    try:
        d = datetime.strptime(expire_str, "%Y-%m-%d")
        delta = (d - datetime.now()).days
        return delta
    except Exception:
        return None


# ============================================================
# SYNCHRONISATION GITHUB
# ============================================================

def load_settings():
    return load_json("geostar_admin_settings.json", {
        "github_token": "",
        "github_owner": "Moneymyck",
        "github_repo": "geostar-android",
        "github_branch": "main",
        "github_file": "codes_geostar.json"
    })


def save_settings(data):
    return save_json("geostar_admin_settings.json", data)


def github_push(callback=None):
    """Pousse codes_geostar.json sur GitHub via l'API."""
    settings = load_settings()
    token = settings.get("github_token", "")
    owner = settings.get("github_owner", "")
    repo = settings.get("github_repo", "")
    branch = settings.get("github_branch", "main")
    filename = settings.get("github_file", "codes_geostar.json")

    if not token or not owner or not repo:
        if callback:
            callback(False, "Token GitHub non configuré")
        return

    data = load_codes()
    content_str = json.dumps(data, ensure_ascii=False, indent=2)
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{filename}"

    try:
        # 1. Obtenir le SHA actuel du fichier (nécessaire pour le mettre à jour)
        req = urllib.request.Request(
            api_url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "GEOSTAR-Admin/1.0"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                current = json.loads(r.read().decode("utf-8"))
                sha = current.get("sha", "")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                sha = ""  # Fichier inexistant, on va le créer
            else:
                raise

        # 2. Préparer le payload
        payload = {
            "message": f"GEOSTAR Admin — mise à jour codes {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "content": content_b64,
            "branch": branch
        }
        if sha:
            payload["sha"] = sha

        # 3. Envoyer
        data_bytes = json.dumps(payload).encode("utf-8")
        req2 = urllib.request.Request(
            api_url,
            data=data_bytes,
            method="PUT",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
                "User-Agent": "GEOSTAR-Admin/1.0"
            }
        )
        with urllib.request.urlopen(req2, timeout=15) as r:
            r.read()

        if callback:
            callback(True, "Synchronisé avec GitHub OK")

    except Exception as e:
        if callback:
            callback(False, f"Erreur GitHub : {str(e)[:80]}")


# ============================================================
# QR CODE (pur Python, sans dépendance)
# ============================================================

def generate_qr_matrix(text):
    """Génère une matrice QR simple (version 1, mode alphanumérique)."""
    # On utilise une approche simplifiée basée sur les modules Kivy Canvas
    # Pour un vrai QR code, on génère une représentation binaire
    # et on l'affiche comme grille de pixels colorés

    # Encodage alphanumérique simplifié
    # On génère juste un code-barres 2D visuel basé sur le hash du texte
    # (suffisant pour affichage, les vrais QR codes nécessitent une lib)
    size = 21  # taille version 1 (21x21)
    matrix = [[0] * size for _ in range(size)]

    # Patterns de détection (coins)
    def add_finder(r, c):
        for dr in range(7):
            for dc in range(7):
                if dr == 0 or dr == 6 or dc == 0 or dc == 6:
                    matrix[r + dr][c + dc] = 1
                elif 2 <= dr <= 4 and 2 <= dc <= 4:
                    matrix[r + dr][c + dc] = 1

    add_finder(0, 0)
    add_finder(0, 14)
    add_finder(14, 0)

    # Pattern de synchronisation
    for i in range(8, 13):
        matrix[6][i] = 1 if i % 2 == 0 else 0
        matrix[i][6] = 1 if i % 2 == 0 else 0

    # Données encodées depuis le hash du texte
    h = int(hashlib.md5(text.encode()).hexdigest(), 16)
    bits = format(h, "0128b")
    idx = 0
    for r in range(size):
        for c in range(size):
            if matrix[r][c] == 0 and not (r < 8 and c < 8) and not (r < 8 and c >= 14) and not (r >= 14 and c < 8):
                if idx < len(bits):
                    matrix[r][c] = int(bits[idx])
                    idx += 1

    return matrix


class QRCodeWidget(BoxLayout):
    """Widget QR code — affiche le code en texte dans un cadre."""

    def __init__(self, text, size_hint_fix=None, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.padding = dp(8)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        # Afficher le code en texte dans un cadre blanc
        lbl = Label(
            text=text,
            color=(0, 0, 0, 1),
            font_size=dp(10),
            halign="center",
            bold=True
        )
        lbl.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
        self.add_widget(lbl)

    def _upd(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size


# ============================================================
# WIDGETS COMMUNS
# ============================================================

def make_btn(text, bg=C_GREY, color=C_TEXT, height=dp(48), bold=False, font_size=None):
    b = Button(
        text=text,
        size_hint_y=None,
        height=height,
        background_color=bg,
        color=color,
        bold=bold,
        font_size=font_size or dp(14)
    )
    return b


def make_label(text, color=C_TEXT, height=None, font_size=None, bold=False, halign="left"):
    kw = dict(
        text=text,
        color=color,
        bold=bold,
        halign=halign,
        markup=True
    )
    if height is not None:
        kw["size_hint_y"] = None
        kw["height"] = height
    if font_size:
        kw["font_size"] = font_size
    lbl = Label(**kw)
    lbl.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
    return lbl


def show_toast(message, duration=2.5):
    """Affiche un message temporaire en bas de l'écran."""
    box = BoxLayout(padding=dp(12))
    lbl = Label(text=message, color=C_TEXT, halign="center")
    box.add_widget(lbl)
    pop = Popup(
        content=box,
        size_hint=(0.8, None),
        height=dp(60),
        background_color=(0.1, 0.1, 0.1, 0.9),
        title="",
        separator_height=0
    )
    pop.open()
    Clock.schedule_once(lambda dt: pop.dismiss(), duration)


def confirm_dialog(title, message, on_yes):
    """Dialogue de confirmation oui/non."""
    box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
    box.add_widget(make_label(message, color=C_TEXT, height=dp(80), halign="center"))
    btns = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(50))
    b_yes = make_btn("OUI", bg=C_RED, height=dp(50))
    b_no = make_btn("ANNULER", bg=C_GREY, height=dp(50))
    btns.add_widget(b_yes)
    btns.add_widget(b_no)
    box.add_widget(btns)
    pop = Popup(title=title, content=box, size_hint=(0.85, None), height=dp(200))

    def do_yes(_):
        pop.dismiss()
        on_yes()

    b_yes.bind(on_release=do_yes)
    b_no.bind(on_release=lambda x: pop.dismiss())
    pop.open()


# ============================================================
# ÉCRAN LOGIN
# ============================================================

class LoginScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=dp(30), spacing=dp(16))

        with root.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda s, v: setattr(self._bg, "pos", v),
                  size=lambda s, v: setattr(self._bg, "size", v))

        root.add_widget(Widget(size_hint_y=0.2))

        # Titre
        root.add_widget(make_label(
            "[b]GEOSTAR ADMIN[/b]",
            color=C_GOLD,
            height=dp(50),
            font_size=dp(26),
            halign="center"
        ))
        root.add_widget(make_label(
            f"v{ADMIN_VERSION}",
            color=C_SUBTEXT,
            height=dp(24),
            halign="center"
        ))

        root.add_widget(Widget(size_hint_y=None, height=dp(30)))

        # Champ identifiant
        self.inp_user = TextInput(
            hint_text="Identifiant admin",
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            font_size=dp(16),
            background_color=(0.15, 0.17, 0.22, 1),
            foreground_color=C_TEXT,
            cursor_color=C_GOLD
        )
        root.add_widget(self.inp_user)

        # Champ mot de passe
        self.inp_pwd = TextInput(
            hint_text="Mot de passe",
            password=True,
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            font_size=dp(16),
            background_color=(0.15, 0.17, 0.22, 1),
            foreground_color=C_TEXT,
            cursor_color=C_GOLD
        )
        root.add_widget(self.inp_pwd)

        # Message d'erreur
        self.lbl_err = make_label("", color=C_RED, height=dp(30), halign="center")
        root.add_widget(self.lbl_err)

        # Bouton connexion
        b_login = make_btn("SE CONNECTER", bg=C_GOLD, color=(0, 0, 0, 1),
                           height=dp(55), bold=True, font_size=dp(16))
        b_login.bind(on_release=self.do_login)
        root.add_widget(b_login)

        # Bouton créer premier admin (visible seulement si aucun admin)
        self.b_create = make_btn("CRÉER LE PREMIER ADMIN",
                                 bg=(0.2, 0.3, 0.5, 1), height=dp(44))
        self.b_create.bind(on_release=self.show_create_admin)
        root.add_widget(self.b_create)

        root.add_widget(Widget(size_hint_y=0.3))
        self.add_widget(root)

    def on_enter(self):
        # Masquer le bouton créer si des admins existent déjà
        self.b_create.opacity = 0 if admin_exists() else 1
        self.b_create.disabled = admin_exists()

    def do_login(self, _):
        user = self.inp_user.text.strip()
        pwd = self.inp_pwd.text.strip()
        if not user or not pwd:
            self.lbl_err.text = "Remplissez les deux champs"
            return
        if verify_admin(user, pwd):
            self.lbl_err.text = ""
            App.get_running_app().current_admin = user
            log_action(user, "Connexion", "")
            self.manager.transition = SlideTransition(direction="left")
            self.manager.current = "main"
        else:
            self.lbl_err.text = "Identifiant ou mot de passe incorrect"

    def show_create_admin(self, _):
        """Popup de création du premier admin."""
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        box.add_widget(make_label("Créer le compte administrateur", color=C_GOLD,
                                  height=dp(36), halign="center"))
        inp_u = TextInput(hint_text="Identifiant", multiline=False,
                          size_hint_y=None, height=dp(48))
        inp_p = TextInput(hint_text="Mot de passe", password=True, multiline=False,
                          size_hint_y=None, height=dp(48))
        inp_p2 = TextInput(hint_text="Confirmer mot de passe", password=True,
                           multiline=False, size_hint_y=None, height=dp(48))
        lbl_e = make_label("", color=C_RED, height=dp(28), halign="center")
        b_ok = make_btn("CRÉER", bg=C_GREEN, height=dp(48), bold=True)
        for w in [inp_u, inp_p, inp_p2, lbl_e, b_ok]:
            box.add_widget(w)

        pop = Popup(title="Premier admin", content=box,
                    size_hint=(0.9, None), height=dp(360))

        def do_create(_):
            u = inp_u.text.strip()
            p = inp_p.text.strip()
            p2 = inp_p2.text.strip()
            if not u or not p:
                lbl_e.text = "Champs requis"
                return
            if p != p2:
                lbl_e.text = "Les mots de passe ne correspondent pas"
                return
            ok, msg = create_admin(u, p)
            if ok:
                pop.dismiss()
                self.b_create.opacity = 0
                self.b_create.disabled = True
                show_toast(f"Admin '{u}' créé ! Connectez-vous.")
            else:
                lbl_e.text = msg

        b_ok.bind(on_release=do_create)
        pop.open()


# ============================================================
# ÉCRAN PRINCIPAL — Liste des codes
# ============================================================

class MainScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._filtre = "tous"
        self._search = ""
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")

        with root.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda s, v: setattr(self._bg, "pos", v),
                  size=lambda s, v: setattr(self._bg, "size", v))

        # HEADER
        header = BoxLayout(size_hint_y=None, height=dp(56),
                           padding=[dp(10), dp(6)], spacing=dp(8))
        with header.canvas.before:
            Color(0.10, 0.12, 0.16, 1)
            self._hbg = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda s, v: setattr(self._hbg, "pos", v),
                    size=lambda s, v: setattr(self._hbg, "size", v))

        self.lbl_title = make_label("[b]GEOSTAR ADMIN[/b]", color=C_GOLD,
                                    height=dp(56), font_size=dp(18))
        header.add_widget(self.lbl_title)

        b_stats = make_btn("STATS", bg=(0.15, 0.20, 0.30, 1),
                           height=dp(44), font_size=dp(18))
        b_stats.size_hint_x = None
        b_stats.width = dp(70)
        b_stats.bind(on_release=lambda x: self._goto("stats"))
        header.add_widget(b_stats)

        b_cfg = make_btn("REGLAGES", bg=(0.15, 0.20, 0.30, 1),
                         height=dp(44), font_size=dp(18))
        b_cfg.size_hint_x = None
        b_cfg.width = dp(90)
        b_cfg.bind(on_release=lambda x: self._goto("settings"))
        header.add_widget(b_cfg)

        root.add_widget(header)

        # COMPTEURS
        self.row_counts = BoxLayout(size_hint_y=None, height=dp(40),
                                    padding=[dp(8), 0], spacing=dp(4))
        root.add_widget(self.row_counts)

        # FILTRES
        self._filtre_btns = {}
        filtres = BoxLayout(size_hint_y=None, height=dp(42),
                            padding=[dp(8), dp(2)], spacing=dp(6))
        for label, key, clr_on in [
            ("Tous",       "tous",    (0.2, 0.4, 0.7, 1)),
            ("Actifs",     "actif",   (0.1, 0.6, 0.3, 1)),
            ("[!] Bientot","bientot", (0.7, 0.4, 0.1, 1)),
            ("Bloques",    "bloque",  (0.7, 0.15, 0.15, 1)),
            ("Expires",    "expire",  (0.35, 0.35, 0.40, 1)),
        ]:
            tb = Button(text=label,
                        size_hint_y=None, height=dp(36),
                        font_size=dp(11),
                        background_normal="",
                        background_color=clr_on if key == "tous"
                                         else (0.18, 0.18, 0.22, 1))
            self._filtre_btns[key] = (tb, clr_on)
            tb.bind(on_release=lambda btn, k=key: self._set_filtre(k))
            filtres.add_widget(tb)
        root.add_widget(filtres)

        # RECHERCHE
        search_row = BoxLayout(size_hint_y=None, height=dp(44),
                               padding=[dp(8), dp(2)], spacing=dp(6))
        self.inp_search = TextInput(
            hint_text="🔍 Rechercher par code ou nom...",
            multiline=False,
            font_size=dp(13),
            background_color=(0.14, 0.16, 0.20, 1),
            foreground_color=C_TEXT
        )
        self.inp_search.bind(text=lambda s, v: self._on_search(v))
        search_row.add_widget(self.inp_search)
        root.add_widget(search_row)

        # LISTE des codes
        self.sv = ScrollView()
        self.grid = GridLayout(cols=1, spacing=dp(6),
                               padding=[dp(8), dp(4)], size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.sv.add_widget(self.grid)
        root.add_widget(self.sv)

        # BOUTON NOUVEAU CODE
        bar_bottom = BoxLayout(size_hint_y=None, height=dp(58),
                               padding=[dp(8), dp(6)], spacing=dp(8))
        with bar_bottom.canvas.before:
            Color(0.10, 0.12, 0.16, 1)
            self._bbbg = Rectangle(pos=bar_bottom.pos, size=bar_bottom.size)
        bar_bottom.bind(pos=lambda s, v: setattr(self._bbbg, "pos", v),
                        size=lambda s, v: setattr(self._bbbg, "size", v))

        b_new = make_btn("+ NOUVEAU CODE", bg=C_GREEN,
                         height=dp(46), bold=True, font_size=dp(15))
        b_new.bind(on_release=lambda x: self._goto("new_code"))
        bar_bottom.add_widget(b_new)

        b_notes = make_btn("NOTES", bg=(0.4, 0.2, 0.6, 1),
                           height=dp(46), font_size=dp(13))
        b_notes.size_hint_x = None
        b_notes.width = dp(80)
        b_notes.bind(on_release=lambda x: self._show_notes_attente())
        bar_bottom.add_widget(b_notes)

        b_sync = make_btn("SYNC", bg=C_BLUE, height=dp(46), font_size=dp(13))
        b_sync.size_hint_x = None
        b_sync.width = dp(90)
        b_sync.bind(on_release=lambda x: self._do_sync())
        bar_bottom.add_widget(b_sync)

        root.add_widget(bar_bottom)
        self.add_widget(root)

    def on_enter(self):
        self.refresh()

    def refresh(self):
        data = load_codes()
        codes = data.get("codes_valides", {})
        bloques = data.get("codes_bloques", [])

        # Calculer compteurs
        nb_actif = nb_expire = nb_bloque = nb_bientot = 0
        for code, info in codes.items():
            st = get_code_status(code, data)
            if st == "actif":
                jr = jours_restants(info.get("expire", ""))
                if jr is not None and jr <= 7:
                    nb_bientot += 1
                else:
                    nb_actif += 1
            elif st == "expire":
                nb_expire += 1
            elif st == "bloque":
                nb_bloque += 1

        # Afficher compteurs
        self.row_counts.clear_widgets()
        for txt, clr in [
            (f"[OK] {nb_actif} actifs", C_GREEN),
            (f"[!] {nb_bientot} bientôt", C_ORANGE),
            (f"[X] {nb_bloque} bloqués", C_RED),
            (f"[EXP] {nb_expire} expirés", C_GREY),
        ]:
            lbl = make_label(txt, color=clr, height=dp(40),
                             font_size=dp(11), halign="center")
            self.row_counts.add_widget(lbl)

        # Filtrer et chercher
        self.grid.clear_widgets()
        search = self._search.lower()

        for code, info in sorted(codes.items()):
            st = get_code_status(code, data)
            jr = jours_restants(info.get("expire", ""))
            is_bientot = (st == "actif" and jr is not None and jr <= 7)

            # Filtre statut
            if self._filtre == "actif" and (st != "actif" or is_bientot):
                continue
            if self._filtre == "bloque" and st != "bloque":
                continue
            if self._filtre == "expire" and st != "expire":
                continue
            if self._filtre == "bientot" and not is_bientot:
                continue

            # Filtre recherche
            nom = info.get("nom", "").lower()
            tel = info.get("telephone", "").lower()
            if search and search not in code.lower() and search not in nom and search not in tel:
                continue

            self.grid.add_widget(self._make_code_card(code, info, st, jr, data))

        if len(self.grid.children) == 0:
            self.grid.add_widget(make_label(
                "Aucun code trouvé", color=C_SUBTEXT,
                height=dp(60), halign="center"
            ))

    def _show_notes_attente(self):
        """Popup des notes en attente de validation."""
        # Charger les notes depuis fichier local
        import json, os
        notes_path = os.path.join(
            os.path.expanduser("~"), "geostar_notes_attente.json"
        )
        try:
            with open(notes_path, encoding="utf-8") as f:
                notes = json.load(f)
        except Exception:
            notes = []

        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))

        nb_attente = sum(1 for n in notes if n.get("statut") == "attente")
        nb_valide = sum(1 for n in notes if n.get("statut") == "valide")
        nb_rejete = sum(1 for n in notes if n.get("statut") == "rejete")

        box.add_widget(make_label(
            f"Notes en attente : {nb_attente}  |  Validees : {nb_valide}  |  Rejetees : {nb_rejete}",
            color=C_GOLD, height=dp(30), font_size=dp(11), halign="center"
        ))

        # Filtres
        filtre_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        filtre_sel = ["attente"]

        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=dp(4))
        grid.bind(minimum_height=grid.setter("height"))

        def refresh_notes(filtre="attente"):
            grid.clear_widgets()
            notes_filtrees = [n for n in notes if n.get("statut") == filtre]
            if not notes_filtrees:
                grid.add_widget(make_label(
                    "Aucune note dans cette categorie",
                    color=C_SUBTEXT, height=dp(50), halign="center"
                ))
                return

            for idx, note in enumerate(notes_filtrees):
                card = BoxLayout(orientation="vertical",
                                 size_hint_y=None, height=dp(130),
                                 padding=dp(8), spacing=dp(4))
                with card.canvas.before:
                    Color(0.14, 0.16, 0.20, 1)
                    Rectangle(pos=card.pos, size=card.size)
                card.bind(pos=lambda s, v: None, size=lambda s, v: None)

                # Infos de la note
                theme_key = note.get("theme", "?")
                auteur = note.get("auteur", "Anonyme")
                date = note.get("date", "?")
                langue = note.get("langue", "?")
                texte = note.get("texte", "")[:100] + ("..." if len(note.get("texte","")) > 100 else "")
                a_audio = bool(note.get("audio_path"))

                card.add_widget(make_label(
                    f"Theme : {theme_key}  |  Par : {auteur}  |  {date}  |  [{langue}]",
                    color=C_GOLD, height=dp(22), font_size=dp(11)
                ))
                card.add_widget(make_label(
                    texte if texte else "[Note vocale uniquement]",
                    color=C_TEXT, height=dp(40), font_size=dp(11)
                ))
                if a_audio:
                    card.add_widget(make_label(
                        "[NOTE VOCALE disponible]",
                        color=C_BLUE, height=dp(18), font_size=dp(10)
                    ))

                if filtre == "attente":
                    btn_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
                    b_ok = make_btn("VALIDER", bg=C_GREEN, height=dp(32), font_size=dp(11))
                    b_no = make_btn("REJETER", bg=C_RED, height=dp(32), font_size=dp(11))

                    def do_valider(_, n=note, i=idx):
                        notes[notes.index(n)]["statut"] = "valide"
                        try:
                            with open(notes_path, "w", encoding="utf-8") as f:
                                json.dump(notes, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass
                        log_action(App.get_running_app().current_admin or "admin",
                                   "Validation note", n.get("theme","?"))
                        show_toast("Note validee !")
                        refresh_notes("attente")

                    def do_rejeter(_, n=note, i=idx):
                        notes[notes.index(n)]["statut"] = "rejete"
                        try:
                            with open(notes_path, "w", encoding="utf-8") as f:
                                json.dump(notes, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass
                        log_action(App.get_running_app().current_admin or "admin",
                                   "Rejet note", n.get("theme","?"))
                        show_toast("Note rejetee")
                        refresh_notes("attente")

                    b_ok.bind(on_release=do_valider)
                    b_no.bind(on_release=do_rejeter)
                    btn_row.add_widget(b_ok)
                    btn_row.add_widget(b_no)
                    card.add_widget(btn_row)

                grid.add_widget(card)

        # Boutons filtre
        for label, key in [("En attente", "attente"),
                            ("Validees", "valide"),
                            ("Rejetees", "rejete")]:
            b = Button(text=label, size_hint_y=None, height=dp(32),
                       font_size=dp(11),
                       background_color=C_BLUE if key == "attente" else C_GREY)
            b.bind(on_release=lambda btn, k=key: refresh_notes(k))
            filtre_row.add_widget(b)

        box.add_widget(filtre_row)
        refresh_notes("attente")
        sv.add_widget(grid)
        box.add_widget(sv)

        b_close = make_btn("FERMER", bg=C_GREY, height=dp(44))
        box.add_widget(b_close)
        pop = Popup(title="Gestion des notes communaute",
                    content=box, size_hint=(0.97, 0.93))
        b_close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    def _make_code_card(self, code, info, status, jr, data):
        """Crée une carte pour un code."""
        # Couleur selon statut
        if status == "bloque":
            border_color = C_RED
            bg_color = (0.18, 0.10, 0.10, 1)
        elif status == "expire":
            border_color = C_GREY
            bg_color = (0.14, 0.14, 0.14, 1)
        elif jr is not None and jr <= 7:
            border_color = C_ORANGE
            bg_color = (0.18, 0.14, 0.08, 1)
        else:
            # Couleur du tarif
            tarif = info.get("tarif", "")
            if tarif in TARIFS:
                border_color = TARIFS[tarif]["couleur"]
            else:
                border_color = C_BLUE
            bg_color = (0.12, 0.15, 0.20, 1)

        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         height=dp(100), padding=dp(8), spacing=dp(4))

        with card.canvas.before:
            Color(*bg_color)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(6)])
            Color(*border_color)
            Line(rounded_rectangle=(card.x, card.y, card.width, card.height, dp(6)),
                 width=1.2)
        card.bind(
            pos=lambda s, v: s.canvas.before.clear() or self._redraw_card(s, bg_color, border_color),
            size=lambda s, v: s.canvas.before.clear() or self._redraw_card(s, bg_color, border_color)
        )

        # Ligne 1 : code + tarif
        row1 = BoxLayout(size_hint_y=None, height=dp(26))
        lbl_code = make_label(f"[b]{code}[/b]", color=C_GOLD,
                              height=dp(26), font_size=dp(14))
        row1.add_widget(lbl_code)
        tarif = info.get("tarif", "")
        if tarif:
            lbl_tarif = make_label(tarif, color=border_color,
                                   height=dp(26), font_size=dp(11))
            lbl_tarif.size_hint_x = None
            lbl_tarif.width = dp(70)
            row1.add_widget(lbl_tarif)
        card.add_widget(row1)

        # Ligne 2 : nom + téléphone
        nom = info.get("nom", "—")
        tel = info.get("telephone", "")
        row2 = make_label(
            f"{nom}  {('· ' + tel) if tel else ''}",
            color=C_TEXT, height=dp(20), font_size=dp(12)
        )
        card.add_widget(row2)

        # Ligne 3 : expiration
        expire_str = info.get("expire", "")
        if status == "bloque":
            expire_lbl = "[X] BLOQUÉ"
            expire_color = C_RED
        elif status == "expire":
            expire_lbl = f"[EXP] Expiré le {expire_str}"
            expire_color = C_GREY
        elif jr is not None:
            if jr <= 0:
                expire_lbl = "Expire aujourd'hui !"
                expire_color = C_RED
            elif jr <= 7:
                expire_lbl = f"[!] Expire dans {jr} jours ({expire_str})"
                expire_color = C_ORANGE
            else:
                expire_lbl = f"Expire le {expire_str} ({jr}j)"
                expire_color = C_GREEN
        else:
            expire_lbl = "Pas de date d'expiration"
            expire_color = C_SUBTEXT

        card.add_widget(make_label(expire_lbl, color=expire_color,
                                   height=dp(18), font_size=dp(11)))

        # Bouton ouvrir détail
        card.bind(on_touch_down=lambda s, t: self._open_detail(code, info, data)
                  if s.collide_point(*t.pos) else None)

        return card

    def _redraw_card(self, card, bg, border):
        with card.canvas.before:
            Color(*bg)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(6)])
            Color(*border)
            Line(rounded_rectangle=(card.x, card.y, card.width, card.height, dp(6)),
                 width=1.2)

    def _open_detail(self, code, info, data):
        app = App.get_running_app()
        app.detail_code = code
        app.detail_info = info
        app.detail_data = data
        self._goto("detail")

    def _goto(self, screen):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = screen

    def _set_filtre(self, f):
        self._filtre = f
        # Mettre a jour les couleurs des boutons filtres
        CLRS = {
            "tous":    (0.2, 0.4, 0.7, 1),
            "actif":   (0.1, 0.6, 0.3, 1),
            "bientot": (0.7, 0.4, 0.1, 1),
            "bloque":  (0.7, 0.15, 0.15, 1),
            "expire":  (0.35, 0.35, 0.40, 1),
        }
        for key, (btn, clr_on) in self._filtre_btns.items():
            btn.background_color = clr_on if key == f else (0.18, 0.18, 0.22, 1)
        self.refresh()

    def _on_search(self, text):
        self._search = text
        Clock.schedule_once(lambda dt: self.refresh(), 0.3)

    def _do_sync(self):
        show_toast("Synchronisation en cours...")

        def on_done(ok, msg):
            def _show(dt):
                show_toast(msg)
                if ok:
                    log_action(App.get_running_app().current_admin or "admin",
                               "Sync GitHub", "Succès")
            Clock.schedule_once(_show, 0)

        import threading
        threading.Thread(target=lambda: github_push(callback=on_done),
                         daemon=True).start()


# ============================================================
# ÉCRAN NOUVEAU CODE
# ============================================================

class NewCodeScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tarif_sel = "1 mois"
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))

        with root.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda s, v: setattr(self._bg, "pos", v),
                  size=lambda s, v: setattr(self._bg, "size", v))

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        b_back = make_btn("< Retour", bg=(0.2, 0.2, 0.25, 1), height=dp(44))
        b_back.size_hint_x = None
        b_back.width = dp(50)
        b_back.bind(on_release=self._go_back)
        hdr.add_widget(b_back)
        hdr.add_widget(make_label("[b]NOUVEAU CODE[/b]", color=C_GOLD,
                                  height=dp(48), font_size=dp(18)))
        root.add_widget(hdr)

        sv = ScrollView()
        inner = BoxLayout(orientation="vertical", spacing=dp(12),
                          padding=[0, dp(4)], size_hint_y=None)
        inner.bind(minimum_height=inner.setter("height"))

        # Tarif
        inner.add_widget(make_label("TARIF", color=C_GOLD,
                                    height=dp(28), font_size=dp(13), bold=True))
        tarif_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        self.tarif_btns = {}
        for t, info in TARIFS.items():
            tb = ToggleButton(
                text=f"{t}\n{info['prix']:.0f}€",
                group="tarif",
                size_hint_y=None, height=dp(50),
                font_size=dp(11),
                background_normal="",
                background_down="",
                background_color=info["couleur"]
            )
            if t == "1 mois":
                tb.state = "down"
            tb.bind(on_press=lambda b, tarif=t: self._sel_tarif(tarif))
            self.tarif_btns[t] = tb
            tarif_row.add_widget(tb)
        inner.add_widget(tarif_row)

        # Champs
        for label, attr in [
            ("NOM DU CLIENT", "inp_nom"),
            ("TÉLÉPHONE / WHATSAPP", "inp_tel"),
            ("EMAIL (optionnel)", "inp_email"),
            ("NOTES (optionnel)", "inp_notes"),
        ]:
            inner.add_widget(make_label(label, color=C_SUBTEXT,
                                        height=dp(24), font_size=dp(11)))
            inp = TextInput(
                multiline=False,
                size_hint_y=None,
                height=dp(48),
                font_size=dp(14),
                background_color=(0.14, 0.16, 0.20, 1),
                foreground_color=C_TEXT
            )
            setattr(self, attr, inp)
            inner.add_widget(inp)

        # Nombre de codes
        inner.add_widget(make_label("NOMBRE DE CODES À GÉNÉRER",
                                    color=C_SUBTEXT, height=dp(24), font_size=dp(11)))
        self.inp_nb = TextInput(
            text="1", multiline=False,
            size_hint_y=None, height=dp(48),
            font_size=dp(14),
            background_color=(0.14, 0.16, 0.20, 1),
            foreground_color=C_TEXT
        )
        inner.add_widget(self.inp_nb)

        # Message erreur
        self.lbl_err = make_label("", color=C_RED, height=dp(28), halign="center")
        inner.add_widget(self.lbl_err)

        sv.add_widget(inner)
        root.add_widget(sv)

        # Boutons
        btn_row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10))
        b_gen = make_btn("GÉNÉRER", bg=C_GREEN, height=dp(50), bold=True, font_size=dp(15))
        b_gen.bind(on_release=self._do_generate)
        b_sync = make_btn("GÉNÉRER + SYNC", bg=C_BLUE, height=dp(50), font_size=dp(13))
        b_sync.bind(on_release=lambda x: self._do_generate(x, sync=True))
        btn_row.add_widget(b_gen)
        btn_row.add_widget(b_sync)
        root.add_widget(btn_row)

        self.add_widget(root)

    def on_enter(self):
        # Réinitialiser les champs
        for attr in ["inp_nom", "inp_tel", "inp_email", "inp_notes"]:
            getattr(self, attr).text = ""
        self.inp_nb.text = "1"
        self.lbl_err.text = ""

    def _sel_tarif(self, t):
        self._tarif_sel = t

    def _go_back(self, _):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "main"

    def _do_generate(self, _, sync=False):
        nom = self.inp_nom.text.strip()
        tel = self.inp_tel.text.strip()
        email = self.inp_email.text.strip()
        notes = self.inp_notes.text.strip()

        try:
            nb = int(self.inp_nb.text.strip())
            if nb < 1 or nb > 50:
                raise ValueError
        except ValueError:
            self.lbl_err.text = "Nombre invalide (1 à 50)"
            return

        tarif = self._tarif_sel
        duree = TARIFS[tarif]["duree_jours"]
        prix = TARIFS[tarif]["prix"]
        expire = (datetime.now() + timedelta(days=duree)).strftime("%Y-%m-%d")

        data = load_codes()
        codes_existants = set(data["codes_valides"].keys())
        nouveaux = []

        for i in range(nb):
            code = generer_code(codes_existants)
            if not code:
                self.lbl_err.text = "Impossible de générer un code unique"
                return
            codes_existants.add(code)
            data["codes_valides"][code] = {
                "expire": expire,
                "nom": nom or f"Client {i+1}" if nb > 1 else nom,
                "telephone": tel,
                "email": email,
                "notes": notes,
                "tarif": tarif,
                "prix": prix,
                "cree_le": datetime.now().strftime("%Y-%m-%d"),
                "cree_par": App.get_running_app().current_admin or "admin"
            }
            nouveaux.append(code)

        save_codes(data)
        log_action(App.get_running_app().current_admin or "admin",
                   "Génération", f"{nb} code(s) — {tarif} — {nom}")

        # Afficher résultat
        self._show_result(nouveaux, expire, sync)

    def _show_result(self, codes, expire, sync):
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        box.add_widget(make_label(
            f"[b]{len(codes)} code(s) généré(s) ![/b]",
            color=C_GREEN, height=dp(36), halign="center", font_size=dp(16)
        ))
        box.add_widget(make_label(
            f"Expire le : {expire}",
            color=C_SUBTEXT, height=dp(28), halign="center"
        ))

        sv = ScrollView(size_hint_y=None, height=dp(120))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4), padding=dp(4))
        grid.bind(minimum_height=grid.setter("height"))
        for c in codes:
            lbl = make_label(f"[b]{c}[/b]", color=C_GOLD,
                             height=dp(32), font_size=dp(16), halign="center")
            grid.add_widget(lbl)
        sv.add_widget(grid)
        box.add_widget(sv)

        if sync:
            box.add_widget(make_label("Synchronisation GitHub en cours...",
                                      color=C_BLUE, height=dp(28), halign="center"))

        btn_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))

        pop = Popup(title="OK Codes générés", content=box,
                    size_hint=(0.92, None), height=dp(360),
                    auto_dismiss=False)

        b_ok = make_btn("OK", bg=C_GREEN, height=dp(44), bold=True)
        btn_row.add_widget(b_ok)
        box.add_widget(btn_row)

        def do_ok(_):
            pop.dismiss()
            self.manager.transition = SlideTransition(direction="right")
            self.manager.current = "main"

        b_ok.bind(on_release=do_ok)
        pop.open()

        if sync:
            def on_sync(ok, msg):
                def _show(dt):
                    show_toast(msg)
                Clock.schedule_once(_show, 0)
            import threading
            threading.Thread(target=lambda: github_push(callback=on_sync),
                             daemon=True).start()


# ============================================================
# ÉCRAN DÉTAIL CODE
# ============================================================

class DetailScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        self.root_box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))

        with self.root_box.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(pos=self.root_box.pos, size=self.root_box.size)
        self.root_box.bind(
            pos=lambda s, v: setattr(self._bg, "pos", v),
            size=lambda s, v: setattr(self._bg, "size", v)
        )

        self.add_widget(self.root_box)

    def on_enter(self):
        self.root_box.clear_widgets()
        app = App.get_running_app()
        code = app.detail_code
        info = app.detail_info
        data = app.detail_data
        self._render(code, info, data)

    def _render(self, code, info, data):
        box = self.root_box
        status = get_code_status(code, data)
        jr = jours_restants(info.get("expire", ""))

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        b_back = make_btn("< Retour", bg=(0.2, 0.2, 0.25, 1), height=dp(44))
        b_back.size_hint_x = None
        b_back.width = dp(50)
        b_back.bind(on_release=self._go_back)
        hdr.add_widget(b_back)
        hdr.add_widget(make_label(f"[b]{code}[/b]", color=C_GOLD,
                                  height=dp(48), font_size=dp(18)))
        box.add_widget(hdr)

        sv = ScrollView()
        inner = BoxLayout(orientation="vertical", spacing=dp(10),
                          size_hint_y=None, padding=[0, dp(4)])
        inner.bind(minimum_height=inner.setter("height"))

        # Infos
        for label, val in [
            ("Nom", info.get("nom", "—")),
            ("Téléphone", info.get("telephone", "—")),
            ("Email", info.get("email", "—")),
            ("Tarif", info.get("tarif", "—")),
            ("Prix payé", f"{info.get('prix', 0):.0f} €"),
            ("Créé le", info.get("cree_le", "—")),
            ("Créé par", info.get("cree_par", "—")),
            ("Expire le", info.get("expire", "—")),
            ("Notes", info.get("notes", "—")),
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
            lbl_l = make_label(label, color=C_SUBTEXT,
                               height=dp(36), font_size=dp(12))
            lbl_l.size_hint_x = None
            lbl_l.width = dp(100)
            row.add_widget(lbl_l)
            row.add_widget(make_label(str(val), color=C_TEXT,
                                      height=dp(36), font_size=dp(13)))
            inner.add_widget(row)

        # Statut
        if status == "bloque":
            st_color, st_text = C_RED, "[X] BLOQUÉ"
        elif status == "expire":
            st_color, st_text = C_GREY, "[EXP] EXPIRÉ"
        elif jr is not None and jr <= 7:
            st_color, st_text = C_ORANGE, f"[!] Expire dans {jr} jours"
        else:
            st_color, st_text = C_GREEN, f"[OK] Actif — {jr}j restants" if jr else "[OK] Actif"

        inner.add_widget(make_label(f"[b]Statut : {st_text}[/b]",
                                    color=st_color, height=dp(36),
                                    font_size=dp(14), halign="center"))

        # QR CODES
        inner.add_widget(make_label("[b]QR CODE[/b]", color=C_GOLD,
                                    height=dp(30), font_size=dp(13), bold=True))

        qr_row = BoxLayout(size_hint_y=None, height=dp(160), spacing=dp(10))

        # QR visuel (juste le code)
        qr_box1 = BoxLayout(orientation="vertical", spacing=dp(4))
        qr1 = QRCodeWidget(text=code, size_hint=(1, None), height=dp(130))
        qr_box1.add_widget(qr1)
        qr_box1.add_widget(make_label("Visuel", color=C_SUBTEXT,
                                      height=dp(20), font_size=dp(10),
                                      halign="center"))
        qr_row.add_widget(qr_box1)

        # QR interactif (URL scheme)
        qr_url = f"geostar://activate/{code}"
        qr_box2 = BoxLayout(orientation="vertical", spacing=dp(4))
        qr2 = QRCodeWidget(text=qr_url, size_hint=(1, None), height=dp(130))
        qr_box2.add_widget(qr2)
        qr_box2.add_widget(make_label("Interactif", color=C_SUBTEXT,
                                      height=dp(20), font_size=dp(10),
                                      halign="center"))
        qr_row.add_widget(qr_box2)

        inner.add_widget(qr_row)
        inner.add_widget(make_label(
            "Le QR interactif remplira automatiquement\nle code dans GEOSTAR (si activé)",
            color=C_SUBTEXT, height=dp(40), font_size=dp(10), halign="center"
        ))

        sv.add_widget(inner)
        box.add_widget(sv)

        # ACTIONS
        box.add_widget(make_label("[b]ACTIONS[/b]", color=C_GOLD,
                                  height=dp(28), font_size=dp(13), bold=True))
        actions = GridLayout(cols=2, spacing=dp(8),
                             size_hint_y=None, height=dp(120))

        if status == "bloque":
            b_bloc = make_btn("OK DÉBLOQUER", bg=C_GREEN, height=dp(52))
            b_bloc.bind(on_release=lambda x: self._toggle_bloc(code, data, False))
        else:
            b_bloc = make_btn("[X] BLOQUER", bg=C_RED, height=dp(52))
            b_bloc.bind(on_release=lambda x: self._toggle_bloc(code, data, True))

        b_prolong = make_btn("[EXP] PROLONGER", bg=C_BLUE, height=dp(52))
        b_prolong.bind(on_release=lambda x: self._show_prolonger(code, data))

        b_modif = make_btn("EDIT MODIFIER", bg=(0.3, 0.3, 0.5, 1), height=dp(52))
        b_modif.bind(on_release=lambda x: self._show_modifier(code, info, data))

        b_del = make_btn("DEL SUPPRIMER", bg=(0.5, 0.15, 0.15, 1), height=dp(52))
        b_del.bind(on_release=lambda x: self._confirm_delete(code, data))

        for b in [b_bloc, b_prolong, b_modif, b_del]:
            actions.add_widget(b)

        box.add_widget(actions)

    def _go_back(self, _):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "main"

    def _toggle_bloc(self, code, data, bloquer):
        bloques = data.get("codes_bloques", [])
        if bloquer and code not in bloques:
            bloques.append(code)
        elif not bloquer and code in bloques:
            bloques.remove(code)
        data["codes_bloques"] = bloques
        save_codes(data)
        action = "Blocage" if bloquer else "Déblocage"
        log_action(App.get_running_app().current_admin or "admin", action, code)
        show_toast(f"Code {code} {'bloqué' if bloquer else 'débloqué'}")

        def _sync_and_refresh(dt):
            def on_sync(ok, msg):
                def _show(dt2):
                    show_toast(msg)
                    App.get_running_app().detail_data = load_codes()
                    self.on_enter()
                Clock.schedule_once(_show, 0)
            import threading
            threading.Thread(target=lambda: github_push(callback=on_sync),
                             daemon=True).start()
        Clock.schedule_once(_sync_and_refresh, 0.5)

    def _show_prolonger(self, code, data):
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        box.add_widget(make_label("Durée supplémentaire à partir d'aujourd'hui :",
                                  color=C_TEXT, height=dp(40)))
        tarif_grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        tarif_grid.bind(minimum_height=tarif_grid.setter("height"))

        pop = Popup(title=f"Prolonger {code}", content=box,
                    size_hint=(0.88, None), height=dp(360))

        for tarif, info in TARIFS.items():
            b = make_btn(
                f"{tarif}  —  {info['prix']:.0f}€",
                bg=info["couleur"], height=dp(52), font_size=dp(14)
            )

            def do_prolong(_, t=tarif):
                duree = TARIFS[t]["duree_jours"]
                new_exp = (datetime.now() + timedelta(days=duree)).strftime("%Y-%m-%d")
                data["codes_valides"][code]["expire"] = new_exp
                save_codes(data)
                log_action(App.get_running_app().current_admin or "admin",
                           "Prolongation", f"{code} — {t}")
                pop.dismiss()
                show_toast(f"Prolongé jusqu'au {new_exp}")
                import threading
                threading.Thread(target=lambda: github_push(
                    callback=lambda ok, msg: Clock.schedule_once(
                        lambda dt: show_toast(msg), 0)), daemon=True).start()
                App.get_running_app().detail_data = load_codes()
                self.on_enter()

            b.bind(on_release=do_prolong)
            tarif_grid.add_widget(b)

        sv = ScrollView()
        sv.add_widget(tarif_grid)
        box.add_widget(sv)
        b_cancel = make_btn("ANNULER", bg=C_GREY, height=dp(44))
        b_cancel.bind(on_release=lambda x: pop.dismiss())
        box.add_widget(b_cancel)
        pop.open()

    def _show_modifier(self, code, info, data):
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        fields = {}
        for label, key in [("Nom", "nom"), ("Téléphone", "telephone"),
                            ("Email", "email"), ("Notes", "notes")]:
            box.add_widget(make_label(label, color=C_SUBTEXT,
                                      height=dp(24), font_size=dp(11)))
            inp = TextInput(
                text=info.get(key, ""),
                multiline=False, size_hint_y=None, height=dp(44),
                background_color=(0.14, 0.16, 0.20, 1),
                foreground_color=C_TEXT
            )
            fields[key] = inp
            box.add_widget(inp)

        pop = Popup(title=f"Modifier {code}", content=box,
                    size_hint=(0.9, None), height=dp(420))
        b_save = make_btn("ENREGISTRER", bg=C_GREEN, height=dp(48), bold=True)

        def do_save(_):
            for key, inp in fields.items():
                data["codes_valides"][code][key] = inp.text.strip()
            save_codes(data)
            log_action(App.get_running_app().current_admin or "admin",
                       "Modification", code)
            pop.dismiss()
            show_toast("Informations mises à jour")
            App.get_running_app().detail_info = data["codes_valides"][code]
            App.get_running_app().detail_data = data
            self.on_enter()

        b_save.bind(on_release=do_save)
        box.add_widget(b_save)
        pop.open()

    def _confirm_delete(self, code, data):
        def do_del():
            if code in data.get("codes_valides", {}):
                del data["codes_valides"][code]
            bloques = data.get("codes_bloques", [])
            if code in bloques:
                bloques.remove(code)
            save_codes(data)
            log_action(App.get_running_app().current_admin or "admin",
                       "Suppression", code)
            show_toast(f"Code {code} supprimé")
            import threading
            threading.Thread(target=lambda: github_push(
                callback=lambda ok, msg: Clock.schedule_once(
                    lambda dt: show_toast(msg), 0)), daemon=True).start()
            self.manager.transition = SlideTransition(direction="right")
            self.manager.current = "main"

        confirm_dialog(f"Supprimer {code}", "Cette action est irréversible.", do_del)


# ============================================================
# ÉCRAN STATISTIQUES
# ============================================================

class StatsScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        with root.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda s, v: setattr(self._bg, "pos", v),
                  size=lambda s, v: setattr(self._bg, "size", v))

        hdr = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        b_back = make_btn("< Retour", bg=(0.2, 0.2, 0.25, 1), height=dp(44))
        b_back.size_hint_x = None
        b_back.width = dp(50)
        b_back.bind(on_release=self._go_back)
        hdr.add_widget(b_back)
        hdr.add_widget(make_label("[b]STATISTIQUES[/b]", color=C_GOLD,
                                  height=dp(48), font_size=dp(18)))
        root.add_widget(hdr)

        self.sv = ScrollView()
        self.inner = BoxLayout(orientation="vertical", spacing=dp(12),
                               size_hint_y=None, padding=[0, dp(4)])
        self.inner.bind(minimum_height=self.inner.setter("height"))
        self.sv.add_widget(self.inner)
        root.add_widget(self.sv)

        b_export = make_btn("[EXPORT] EXPORTER CSV", bg=C_BLUE,
                            height=dp(48), font_size=dp(14))
        b_export.size_hint_y = None
        b_export.bind(on_release=self._do_export)
        root.add_widget(b_export)

        self.add_widget(root)

    def on_enter(self):
        self.inner.clear_widgets()
        data = load_codes()
        codes = data.get("codes_valides", {})

        # Totaux
        total = len(codes)
        actifs = sum(1 for c in codes if get_code_status(c, data) == "actif")
        expires = sum(1 for c in codes if get_code_status(c, data) == "expire")
        bloques = len(data.get("codes_bloques", []))

        self.inner.add_widget(make_label(
            "[b]RÉSUMÉ GÉNÉRAL[/b]", color=C_GOLD,
            height=dp(32), font_size=dp(14), bold=True
        ))

        for txt, val, clr in [
            ("Total des codes", str(total), C_TEXT),
            ("Codes actifs", str(actifs), C_GREEN),
            ("Codes expirés", str(expires), C_GREY),
            ("Codes bloqués", str(bloques), C_RED),
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(34))
            row.add_widget(make_label(txt, color=C_SUBTEXT,
                                      height=dp(34), font_size=dp(13)))
            row.add_widget(make_label(f"[b]{val}[/b]", color=clr,
                                      height=dp(34), font_size=dp(15),
                                      halign="right"))
            self.inner.add_widget(row)

        # Revenus par tarif
        self.inner.add_widget(Widget(size_hint_y=None, height=dp(10)))
        self.inner.add_widget(make_label(
            "[b]REVENUS PAR TARIF[/b]", color=C_GOLD,
            height=dp(32), font_size=dp(14), bold=True
        ))

        tarif_stats = {}
        total_revenus = 0.0
        for code, info in codes.items():
            t = info.get("tarif", "Autre")
            p = float(info.get("prix", 0))
            if t not in tarif_stats:
                tarif_stats[t] = {"count": 0, "revenus": 0.0}
            tarif_stats[t]["count"] += 1
            tarif_stats[t]["revenus"] += p
            total_revenus += p

        for t, s in sorted(tarif_stats.items()):
            clr = TARIFS.get(t, {}).get("couleur", C_SUBTEXT)
            row = BoxLayout(size_hint_y=None, height=dp(36))
            row.add_widget(make_label(
                f"{t} ({s['count']} codes)", color=clr,
                height=dp(36), font_size=dp(12)
            ))
            row.add_widget(make_label(
                f"[b]{s['revenus']:.0f}€[/b]", color=clr,
                height=dp(36), font_size=dp(14), halign="right"
            ))
            self.inner.add_widget(row)

        # Total revenus
        self.inner.add_widget(make_label(
            f"[b]TOTAL REVENUS : {total_revenus:.0f}€[/b]",
            color=C_GOLD, height=dp(40), font_size=dp(16), halign="center"
        ))

        # Codes expirant bientôt
        bientot = [(c, i) for c, i in codes.items()
                   if get_code_status(c, data) == "actif"
                   and jours_restants(i.get("expire", "")) is not None
                   and jours_restants(i.get("expire", "")) <= 7]

        if bientot:
            self.inner.add_widget(Widget(size_hint_y=None, height=dp(10)))
            self.inner.add_widget(make_label(
                f"[b][!] {len(bientot)} CODE(S) EXPIRENT DANS 7 JOURS[/b]",
                color=C_ORANGE, height=dp(32), font_size=dp(13), bold=True
            ))
            for code, info in bientot:
                jr = jours_restants(info.get("expire", ""))
                self.inner.add_widget(make_label(
                    f"  {code}  —  {info.get('nom', '—')}  —  {jr}j",
                    color=C_ORANGE, height=dp(28), font_size=dp(12)
                ))

    def _go_back(self, _):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "main"

    def _do_export(self, _):
        data = load_codes()
        codes = data.get("codes_valides", {})
        path = _file("export_geostar.csv")
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Code", "Nom", "Téléphone", "Email",
                            "Tarif", "Prix(€)", "Créé le", "Expire le",
                            "Statut", "Notes"])
                for code, info in codes.items():
                    w.writerow([
                        code,
                        info.get("nom", ""),
                        info.get("telephone", ""),
                        info.get("email", ""),
                        info.get("tarif", ""),
                        info.get("prix", ""),
                        info.get("cree_le", ""),
                        info.get("expire", ""),
                        get_code_status(code, data),
                        info.get("notes", "")
                    ])
            show_toast(f"Exporté : {path}")
        except Exception as e:
            show_toast(f"Erreur export : {e}")


# ============================================================
# ÉCRAN PARAMÈTRES
# ============================================================

class SettingsScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        with root.canvas.before:
            Color(*C_BG)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda s, v: setattr(self._bg, "pos", v),
                  size=lambda s, v: setattr(self._bg, "size", v))

        hdr = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        b_back = make_btn("< Retour", bg=(0.2, 0.2, 0.25, 1), height=dp(44))
        b_back.size_hint_x = None
        b_back.width = dp(50)
        b_back.bind(on_release=self._go_back)
        hdr.add_widget(b_back)
        hdr.add_widget(make_label("[b]PARAMÈTRES[/b]", color=C_GOLD,
                                  height=dp(48), font_size=dp(18)))
        root.add_widget(hdr)

        sv = ScrollView()
        inner = BoxLayout(orientation="vertical", spacing=dp(14),
                          size_hint_y=None, padding=[0, dp(4)])
        inner.bind(minimum_height=inner.setter("height"))

        # GitHub
        inner.add_widget(make_label("[b]GITHUB[/b]", color=C_GOLD,
                                    height=dp(32), font_size=dp(14), bold=True))

        settings = load_settings()
        self.fields = {}
        for label, key, hint, is_pwd in [
            ("Token GitHub", "github_token", "ghp_...", True),
            ("Propriétaire", "github_owner", "ex: Moneymyck", False),
            ("Dépôt", "github_repo", "ex: geostar-android", False),
            ("Branche", "github_branch", "ex: main", False),
            ("Fichier", "github_file", "ex: codes_geostar.json", False),
        ]:
            inner.add_widget(make_label(label, color=C_SUBTEXT,
                                        height=dp(24), font_size=dp(11)))
            inp = TextInput(
                text=settings.get(key, ""),
                hint_text=hint,
                password=is_pwd,
                multiline=False,
                size_hint_y=None, height=dp(46),
                background_color=(0.14, 0.16, 0.20, 1),
                foreground_color=C_TEXT
            )
            self.fields[key] = inp
            inner.add_widget(inp)

        b_save_gh = make_btn("ENREGISTRER GITHUB", bg=C_BLUE,
                             height=dp(48), bold=True)
        b_save_gh.bind(on_release=self._save_github)
        inner.add_widget(b_save_gh)

        b_test = make_btn("TESTER LA CONNEXION", bg=(0.2, 0.35, 0.55, 1),
                          height=dp(44))
        b_test.bind(on_release=self._test_github)
        inner.add_widget(b_test)

        # Séparateur
        inner.add_widget(Widget(size_hint_y=None, height=dp(8)))

        # Mon compte
        inner.add_widget(make_label("[b]MON COMPTE[/b]", color=C_GOLD,
                                    height=dp(32), font_size=dp(14), bold=True))

        b_mon_compte = make_btn("MODIFIER MON COMPTE", bg=C_ORANGE,
                                height=dp(48), font_size=dp(14))
        b_mon_compte.bind(on_release=self._show_mon_compte)
        inner.add_widget(b_mon_compte)

        b_secours = make_btn("ACCES DE SECOURS PAR EMAIL", bg=(0.3, 0.3, 0.55, 1),
                             height=dp(44), font_size=dp(13))
        b_secours.bind(on_release=self._show_acces_secours)
        inner.add_widget(b_secours)

        # ---- GESTION DES TARIFS ----
        inner.add_widget(Widget(size_hint_y=None, height=dp(8)))
        inner.add_widget(make_label("[b]TARIFS[/b]", color=C_GOLD,
                                    height=dp(32), font_size=dp(14), bold=True))

        b_gerer_tarifs = make_btn("[CFG] GÉRER LES TARIFS", bg=(0.25, 0.35, 0.55, 1),
                                  height=dp(46), font_size=dp(14))
        b_gerer_tarifs.bind(on_release=lambda x: self._show_gestion_tarifs())
        inner.add_widget(b_gerer_tarifs)

        # Logs
        inner.add_widget(Widget(size_hint_y=None, height=dp(8)))
        inner.add_widget(make_label("[b]DERNIÈRES ACTIONS[/b]", color=C_GOLD,
                                    height=dp(32), font_size=dp(14), bold=True))

        d = load_admins()
        logs = d.get("logs", [])[:10]
        for log in logs:
            inner.add_widget(make_label(
                f"{log['date']}  [{log['admin']}]  {log['action']}  {log.get('detail', '')}",
                color=C_SUBTEXT, height=dp(26), font_size=dp(10)
            ))

        # Déconnexion
        inner.add_widget(Widget(size_hint_y=None, height=dp(10)))
        b_logout = make_btn("SE DÉCONNECTER", bg=C_RED, height=dp(48), bold=True)
        b_logout.bind(on_release=self._logout)
        inner.add_widget(b_logout)

        sv.add_widget(inner)
        root.add_widget(sv)
        self.add_widget(root)

    def _go_back(self, _):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "main"

    def _save_github(self, _):
        settings = {k: inp.text.strip() for k, inp in self.fields.items()}
        save_settings(settings)
        show_toast("Paramètres GitHub enregistrés")

    def _test_github(self, _):
        show_toast("Test en cours...")

        def on_test(ok, msg):
            Clock.schedule_once(lambda dt: show_toast(msg), 0)

        import threading
        threading.Thread(target=lambda: github_push(callback=on_test),
                         daemon=True).start()

    def _show_mon_compte(self, _):
        """Popup pour modifier identifiant et mot de passe."""
        admin = App.get_running_app().current_admin or ""
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(make_label(
            f"Compte : {admin}", color=C_GOLD,
            height=dp(30), halign="center", font_size=dp(14)
        ))

        # Changer identifiant
        box.add_widget(make_label("CHANGER IDENTIFIANT",
                                  color=C_SUBTEXT, height=dp(24), font_size=dp(11)))
        inp_new_user = TextInput(
            hint_text="Nouvel identifiant",
            multiline=False, size_hint_y=None, height=dp(46),
            background_color=(0.14, 0.16, 0.20, 1), foreground_color=C_TEXT
        )
        box.add_widget(inp_new_user)

        # Separateur
        box.add_widget(Widget(size_hint_y=None, height=dp(6)))

        # Changer mot de passe
        box.add_widget(make_label("CHANGER MOT DE PASSE",
                                  color=C_SUBTEXT, height=dp(24), font_size=dp(11)))
        inp_old = TextInput(
            hint_text="Mot de passe actuel",
            password=True, multiline=False, size_hint_y=None, height=dp(46),
            background_color=(0.14, 0.16, 0.20, 1), foreground_color=C_TEXT
        )
        inp_new = TextInput(
            hint_text="Nouveau mot de passe",
            password=True, multiline=False, size_hint_y=None, height=dp(46),
            background_color=(0.14, 0.16, 0.20, 1), foreground_color=C_TEXT
        )
        inp_new2 = TextInput(
            hint_text="Confirmer nouveau mot de passe",
            password=True, multiline=False, size_hint_y=None, height=dp(46),
            background_color=(0.14, 0.16, 0.20, 1), foreground_color=C_TEXT
        )
        for w in [inp_old, inp_new, inp_new2]:
            box.add_widget(w)

        lbl_err = make_label("", color=C_RED, height=dp(28), halign="center")
        box.add_widget(lbl_err)

        b_save = make_btn("ENREGISTRER", bg=C_GREEN, height=dp(48), bold=True)
        box.add_widget(b_save)

        pop = Popup(title="Mon compte", content=box,
                    size_hint=(0.92, None), height=dp(560))

        def do_save(_):
            new_user = inp_new_user.text.strip()
            old_pwd = inp_old.text.strip()
            new_pwd = inp_new.text.strip()
            new_pwd2 = inp_new2.text.strip()

            # Validation
            if not old_pwd:
                lbl_err.text = "Mot de passe actuel requis"
                return
            if not verify_admin(admin, old_pwd):
                lbl_err.text = "Mot de passe actuel incorrect"
                return

            d = load_admins()
            changed = False

            # Changer identifiant si rempli
            if new_user and new_user != admin:
                # Verifier que l identifiant n existe pas deja
                for a in d["admins"]:
                    if a["username"] == new_user:
                        lbl_err.text = "Cet identifiant est deja utilise"
                        return
                for a in d["admins"]:
                    if a["username"] == admin:
                        a["username"] = new_user
                        break
                App.get_running_app().current_admin = new_user
                log_action(admin, "Changement identifiant", new_user)
                changed = True

            # Changer mot de passe si rempli
            if new_pwd:
                if new_pwd != new_pwd2:
                    lbl_err.text = "Les mots de passe ne correspondent pas"
                    return
                if len(new_pwd) < 4:
                    lbl_err.text = "Mot de passe trop court (4 caracteres minimum)"
                    return
                current_user = App.get_running_app().current_admin
                for a in d["admins"]:
                    if a["username"] == current_user:
                        a["password_hash"] = hash_password(new_pwd)
                        break
                log_action(current_user, "Changement mot de passe", "")
                changed = True

            if changed:
                save_admins(d)
                pop.dismiss()
                show_toast("Compte mis a jour avec succes !")
            else:
                lbl_err.text = "Aucune modification detectee"

        b_save.bind(on_release=do_save)
        pop.open()

    def _show_acces_secours(self, _):
        """Popup pour configurer email de secours et reinitialiser via email."""
        admin = App.get_running_app().current_admin or ""
        d = load_admins()
        email_actuel = ""
        for a in d["admins"]:
            if a["username"] == admin:
                email_actuel = a.get("email_secours", "")
                break

        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(make_label(
            "Acces de secours", color=C_GOLD,
            height=dp(30), halign="center", font_size=dp(15)
        ))
        box.add_widget(make_label(
            "En cas d'oubli, reinitialisez via votre email de secours.",
            color=C_SUBTEXT, height=dp(50), halign="center", font_size=dp(11)
        ))

        # Email actuel
        if email_actuel:
            box.add_widget(make_label(
                f"Email enregistre : {email_actuel}",
                color=C_GREEN, height=dp(28), font_size=dp(12), halign="center"
            ))

        box.add_widget(make_label("Votre email de secours :",
                                  color=C_SUBTEXT, height=dp(24), font_size=dp(11)))
        inp_email = TextInput(
            text=email_actuel,
            hint_text="exemple@gmail.com",
            multiline=False, size_hint_y=None, height=dp(48),
            background_color=(0.14, 0.16, 0.20, 1), foreground_color=C_TEXT
        )
        box.add_widget(inp_email)

        lbl_err = make_label("", color=C_RED, height=dp(28), halign="center")
        box.add_widget(lbl_err)

        b_save = make_btn("ENREGISTRER EMAIL", bg=C_GREEN, height=dp(48), bold=True)

        pop = Popup(title="Acces de secours", content=box,
                    size_hint=(0.9, None), height=dp(450))

        def do_save(_):
            email = inp_email.text.strip().lower()
            if not email or "@" not in email:
                lbl_err.text = "Email invalide"
                return
            d2 = load_admins()
            for a in d2["admins"]:
                if a["username"] == admin:
                    a["email_secours"] = email
                    break
            save_admins(d2)
            log_action(admin, "Email secours", email)
            pop.dismiss()
            show_toast(f"Email de secours enregistre : {email}")

        b_save.bind(on_release=do_save)
        box.add_widget(b_save)

        # Bouton reinitialisation
        box.add_widget(Widget(size_hint_y=None, height=dp(6)))
        b_reset = make_btn("REINITIALISER MOT DE PASSE", bg=(0.5, 0.2, 0.1, 1),
                           height=dp(44), font_size=dp(12))

        def do_reset(_):
            email_sec = inp_email.text.strip()
            if not email_sec or "@" not in email_sec:
                lbl_err.text = "Entrez votre email de secours"
                return
            # Verifier que c est bien l email enregistre
            d3 = load_admins()
            email_ok = False
            for a in d3["admins"]:
                if a["username"] == admin and a.get("email_secours", "") == email_sec:
                    email_ok = True
                    # Generer un nouveau mot de passe temporaire
                    import random, string
                    tmp_pwd = "".join(random.choices(string.ascii_letters + string.digits, k=8))
                    a["password_hash"] = hash_password(tmp_pwd)
                    save_admins(d3)
                    pop.dismiss()
                    # Afficher le nouveau mot de passe temporaire
                    show_toast(f"Nouveau mot de passe temporaire : {tmp_pwd}")
                    # Popup avec le mot de passe
                    b = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
                    b.add_widget(make_label(
                        "Nouveau mot de passe temporaire :",
                        color=C_TEXT, height=dp(30), halign="center"
                    ))
                    b.add_widget(make_label(
                        f"[b]{tmp_pwd}[/b]",
                        color=C_GOLD, height=dp(50),
                        font_size=dp(22), halign="center"
                    ))
                    b.add_widget(make_label(
                        "Notez ce code. Changez-le dans Mon Compte des que possible.",
                        color=C_SUBTEXT, height=dp(50), halign="center", font_size=dp(11)
                    ))
                    b_ok2 = make_btn("OK", bg=C_GREEN, height=dp(48), bold=True)
                    b.add_widget(b_ok2)
                    p2 = Popup(title="Mot de passe temporaire", content=b,
                               size_hint=(0.88, None), height=dp(280),
                               auto_dismiss=False)
                    b_ok2.bind(on_release=lambda x: p2.dismiss())
                    p2.open()
                    break

            if not email_ok:
                lbl_err.text = "Email de secours incorrect"

        b_reset.bind(on_release=do_reset)
        box.add_widget(b_reset)
        pop.open()

    def _show_add_admin(self):
        """Popup pour ajouter un nouvel admin."""
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(make_label("Nouvel administrateur", color=C_GOLD,
                                  height=dp(32), halign="center"))
        inp_u = TextInput(hint_text="Identifiant", multiline=False,
                          size_hint_y=None, height=dp(46),
                          background_color=(0.14, 0.16, 0.20, 1),
                          foreground_color=C_TEXT)
        inp_p = TextInput(hint_text="Mot de passe", password=True,
                          multiline=False, size_hint_y=None, height=dp(46),
                          background_color=(0.14, 0.16, 0.20, 1),
                          foreground_color=C_TEXT)
        inp_p2 = TextInput(hint_text="Confirmer mot de passe", password=True,
                           multiline=False, size_hint_y=None, height=dp(46),
                           background_color=(0.14, 0.16, 0.20, 1),
                           foreground_color=C_TEXT)
        lbl_e = make_label("", color=C_RED, height=dp(28), halign="center")
        b_ok = make_btn("CREER", bg=C_GREEN, height=dp(48), bold=True)
        for w in [inp_u, inp_p, inp_p2, lbl_e, b_ok]:
            box.add_widget(w)
        pop = Popup(title="Ajouter un admin", content=box,
                    size_hint=(0.9, None), height=dp(380))
        def do_create(_):
            u = inp_u.text.strip()
            p = inp_p.text.strip()
            p2 = inp_p2.text.strip()
            if not u or not p:
                lbl_e.text = "Champs requis"
                return
            if p != p2:
                lbl_e.text = "Mots de passe differents"
                return
            ok, msg = create_admin(u, p)
            if ok:
                log_action(App.get_running_app().current_admin or "admin",
                           "Ajout admin", u)
                pop.dismiss()
                show_toast(f"Admin '{u}' cree avec succes")
            else:
                lbl_e.text = msg
        b_ok.bind(on_release=do_create)
        pop.open()

    def _show_list_admins(self):
        """Popup listant tous les admins."""
        d = load_admins()
        admins = d.get("admins", [])
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        box.add_widget(make_label(
            f"{len(admins)} administrateur(s)", color=C_GOLD,
            height=dp(32), halign="center"
        ))
        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=dp(4))
        grid.bind(minimum_height=grid.setter("height"))
        current = App.get_running_app().current_admin or ""
        for a in admins:
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            is_me = (a["username"] == current)
            clr = C_GOLD if is_me else C_TEXT
            lbl = make_label(
                f"{'[vous] ' if is_me else ''}{a['username']}  —  cree le {a.get('created_at', '?')}",
                color=clr, height=dp(44), font_size=dp(12)
            )
            row.add_widget(lbl)
            if not is_me:
                b_del = make_btn("Suppr", bg=C_RED, height=dp(36))
                b_del.size_hint_x = None
                b_del.width = dp(70)
                def do_del(_, username=a["username"]):
                    def really_del():
                        d2 = load_admins()
                        d2["admins"] = [x for x in d2["admins"] if x["username"] != username]
                        save_admins(d2)
                        log_action(current, "Suppression admin", username)
                        show_toast(f"Admin '{username}' supprime")
                    confirm_dialog(f"Supprimer {username}", "Cette action est irreversible.", really_del)
                b_del.bind(on_release=do_del)
                row.add_widget(b_del)
            grid.add_widget(row)
        sv.add_widget(grid)
        box.add_widget(sv)
        b_close = make_btn("FERMER", bg=C_GREY, height=dp(44))
        box.add_widget(b_close)
        pop = Popup(title="Liste des admins", content=box,
                    size_hint=(0.9, 0.8))
        b_close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    def _show_gestion_tarifs(self):
        """Popup de gestion complète des tarifs."""
        global TARIFS

        def _build_popup():
            tarifs_courants = load_tarifs()
            outer = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
            outer.add_widget(make_label(
                "[b]Gérer les tarifs[/b]",
                color=C_GOLD, height=dp(30), font_size=dp(15), halign="center"
            ))

            sv = ScrollView(size_hint_y=1)
            grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=[0, dp(4)])
            grid.bind(minimum_height=grid.setter("height"))

            def refresh_list():
                grid.clear_widgets()
                tc = load_tarifs()
                for nom, info in tc.items():
                    row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
                    clr = tuple(info.get("couleur", [0.4, 0.4, 0.4, 1]))
                    lbl = make_label(
                        f"[b]{nom}[/b]  —  {info.get('prix', 0):.0f}€  —  {info.get('duree_jours', 0)}j",
                        color=clr, height=dp(48), font_size=dp(12)
                    )
                    b_edit = make_btn("EDIT", bg=(0.25, 0.35, 0.55, 1), height=dp(40))
                    b_edit.size_hint_x = None
                    b_edit.width = dp(42)
                    b_edit.bind(on_release=lambda x, n=nom: _edit_tarif(n))
                    b_del = make_btn("X", bg=C_RED, height=dp(40))
                    b_del.size_hint_x = None
                    b_del.width = dp(42)
                    b_del.bind(on_release=lambda x, n=nom: _delete_tarif(n))
                    row.add_widget(lbl)
                    row.add_widget(b_edit)
                    row.add_widget(b_del)
                    grid.add_widget(row)

            def _edit_tarif(nom_existant=None):
                """Popup d'édition/création d'un tarif."""
                tc = load_tarifs()
                info_ex = tc.get(nom_existant, {}) if nom_existant else {}

                ebox = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
                titre = "Modifier tarif" if nom_existant else "Nouveau tarif"

                # Champs
                inp_nom = TextInput(
                    text=nom_existant or "",
                    hint_text="Nom du tarif (ex: 3 mois)",
                    multiline=False, size_hint_y=None, height=dp(44),
                    background_color=(0.14, 0.16, 0.20, 1), foreground_color=C_TEXT
                )
                inp_prix = TextInput(
                    text=str(info_ex.get("prix", "")),
                    hint_text="Prix en € (ex: 15)",
                    multiline=False, size_hint_y=None, height=dp(44),
                    background_color=(0.14, 0.16, 0.20, 1), foreground_color=C_TEXT
                )
                inp_jours = TextInput(
                    text=str(info_ex.get("duree_jours", "")),
                    hint_text="Durée en jours (ex: 90)",
                    multiline=False, size_hint_y=None, height=dp(44),
                    background_color=(0.14, 0.16, 0.20, 1), foreground_color=C_TEXT
                )

                for w in [
                    make_label("Nom du tarif", color=C_SUBTEXT, height=dp(22), font_size=dp(11)),
                    inp_nom,
                    make_label("Prix (€)", color=C_SUBTEXT, height=dp(22), font_size=dp(11)),
                    inp_prix,
                    make_label("Durée (jours)", color=C_SUBTEXT, height=dp(22), font_size=dp(11)),
                    inp_jours,
                    make_label("Couleur", color=C_SUBTEXT, height=dp(22), font_size=dp(11)),
                ]:
                    ebox.add_widget(w)

                # Sélecteur de couleur
                couleur_sel = [list(info_ex.get("couleur", COULEURS_TARIF["Bleu"]))]
                couleur_row = GridLayout(cols=4, spacing=dp(4),
                                         size_hint_y=None, height=dp(80))
                for nom_c, clr in COULEURS_TARIF.items():
                    bc = Button(
                        text=nom_c,
                        size_hint_y=None, height=dp(36),
                        background_color=tuple(clr),
                        font_size=dp(10)
                    )
                    bc.bind(on_release=lambda b, c=clr: couleur_sel.__setitem__(0, list(c)))
                    couleur_row.add_widget(bc)
                ebox.add_widget(couleur_row)

                lbl_err = make_label("", color=C_RED, height=dp(24), halign="center")
                ebox.add_widget(lbl_err)

                epop = Popup(title=titre, content=ebox,
                             size_hint=(0.92, None), height=dp(520))

                b_save = make_btn("ENREGISTRER", bg=C_GREEN, height=dp(46), bold=True)

                def do_save(_):
                    n = inp_nom.text.strip()
                    if not n:
                        lbl_err.text = "Nom requis"
                        return
                    try:
                        prix = float(inp_prix.text.strip().replace(",", "."))
                        jours = int(inp_jours.text.strip())
                        if jours < 1:
                            raise ValueError
                    except ValueError:
                        lbl_err.text = "Prix et jours invalides"
                        return

                    tc2 = load_tarifs()
                    # Si renommage : supprimer l'ancien
                    if nom_existant and nom_existant != n and nom_existant in tc2:
                        del tc2[nom_existant]
                    tc2[n] = {
                        "duree_jours": jours,
                        "prix": prix,
                        "monnaie": "EUR",
                        "couleur": couleur_sel[0]
                    }
                    save_tarifs(tc2)
                    global TARIFS
                    TARIFS = tc2
                    log_action(App.get_running_app().current_admin or "admin",
                               "Tarif", f"{'Modif' if nom_existant else 'Ajout'} {n}")
                    epop.dismiss()
                    refresh_list()
                    show_toast(f"Tarif '{n}' enregistré")

                b_save.bind(on_release=do_save)
                ebox.add_widget(b_save)
                epop.open()

            def _delete_tarif(nom):
                def do_del():
                    tc = load_tarifs()
                    if nom in tc:
                        del tc[nom]
                    save_tarifs(tc)
                    global TARIFS
                    TARIFS = tc
                    log_action(App.get_running_app().current_admin or "admin",
                               "Tarif", f"Suppression {nom}")
                    refresh_list()
                    show_toast(f"Tarif '{nom}' supprimé")
                confirm_dialog(f"Supprimer '{nom}'",
                               "Ce tarif sera supprimé de l\'interface.",
                               do_del)

            refresh_list()
            sv.add_widget(grid)
            outer.add_widget(sv)

            btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
            b_add = make_btn("+ AJOUTER UN TARIF", bg=C_GREEN, height=dp(46), bold=True)
            b_add.bind(on_release=lambda x: _edit_tarif())
            b_close = make_btn("FERMER", bg=C_GREY, height=dp(46))
            btn_row.add_widget(b_add)
            btn_row.add_widget(b_close)
            outer.add_widget(btn_row)

            pop = Popup(title="Gestion des tarifs", content=outer,
                        size_hint=(0.95, 0.90), auto_dismiss=False)
            b_close.bind(on_release=lambda x: pop.dismiss())
            pop.open()

        _build_popup()

    def _logout(self, _):
        App.get_running_app().current_admin = None
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "login"


# ============================================================
# APPLICATION PRINCIPALE
# ============================================================

class GeostarAdminApp(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_admin = None
        self.detail_code = None
        self.detail_info = None
        self.detail_data = None

    def build(self):
        try:
            Window.clearcolor = C_BG
        except Exception:
            pass

        try:
            sm = ScreenManager()
            sm.add_widget(LoginScreen(name="login"))
            sm.add_widget(MainScreen(name="main"))
            sm.add_widget(NewCodeScreen(name="new_code"))
            sm.add_widget(DetailScreen(name="detail"))
            sm.add_widget(StatsScreen(name="stats"))
            sm.add_widget(SettingsScreen(name="settings"))
            sm.current = "login"
            return sm
        except Exception as e:
            # Afficher l erreur sur un ecran minimal si crash
            from kivy.uix.label import Label
            from kivy.uix.boxlayout import BoxLayout
            box = BoxLayout(orientation="vertical", padding=20)
            box.add_widget(Label(
                text=f"Erreur de demarrage :\n{str(e)}",
                color=(1, 0.3, 0.3, 1),
                halign="center"
            ))
            return box

    def get_application_name(self):
        return "GEOSTAR Admin"


if __name__ == "__main__":
    GeostarAdminApp().run()
