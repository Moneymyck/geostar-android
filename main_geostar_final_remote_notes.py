
# ============================================================
# GEOSTAR V10 - ANDROID / BASE iPHONE
# ============================================================
# Android : Pydroid 3 + Kivy
# iPhone : même logique, mais il faudra empaqueter avec Kivy-iOS
#          ou créer plus tard une version Swift/Flutter.
#
# NOUVEAUTES :
# - Bouton haut droite = NOTE.
# - Notes modifiables et supprimables.
# - Mémo vocal : tentative d'ouverture du micro Android.
# - Cache permanent : money_cache_solutions.json.
# - Bouton FIGURE : génère une figure aléatoire parmi les 16.
# - Couleurs par élément en cas de répétition :
#   Feu rouge : 1121, 1222, 1122, 1212
#   Vent gris : 2111, 2122, 2112, 2121
#   Eau bleu : 1111, 2222, 1112, 2212
#   Terre vert : 2211, 1221, 1211, 2221
# - Solutions : clic = menu fermé + thème affiché.
# - Navigation : glisser gauche/droite pour solution suivante/précédente.
# - Recherches personnalisées : exemple M8 M7 M3 M9.
# - Suppression des recherches personnalisées.
# - Appui long 3 secondes sur figure = déplacement libre.
# - Clic court sur figure = édition simple 1 / 2 / Q.
# ============================================================

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform
from datetime import datetime
import random, json, os, re

def _get_data_dir():
    """Retourne le dossier de données accessible en écriture sur Android et desktop."""
    try:
        from kivy.utils import platform as _p
        if _p == "android":
            try:
                from android.storage import app_storage_path
                return app_storage_path()
            except Exception:
                pass
    except Exception:
        pass
    import os
    return os.path.expanduser("~")

import os as _os_global
_DATA_DIR = _os_global.path.expanduser("~")  # sera mis à jour au démarrage
NOTES_FILE = "money_notes.json"
CACHE_FILE = "money_cache_solutions.json"
CUSTOM_FILE = "money_recherches_perso.json"

FIGURES = {
    "2222": {"bin": "0000", "africain": "Moussa", "occidental": "Populus", "sens": "Peuple, masse, foule, réception, mouvement collectif."},
    "2221": {"bin": "0001", "africain": "Youba", "occidental": "Tristitia", "sens": "Tristesse, lourdeur, descente, retard, profondeur."},
    "2212": {"bin": "0010", "africain": "Idrisse", "occidental": "Albus", "sens": "Clarté, paix, sagesse, purification, parole juste."},
    "2211": {"bin": "0011", "africain": "Nouhou", "occidental": "Fortuna Major", "sens": "Grande fortune, protection, élévation, réussite solide."},
    "2122": {"bin": "0100", "africain": "Oumar", "occidental": "Rubeus", "sens": "Feu, passion, conflit, danger, rupture, énergie brute."},
    "2121": {"bin": "0101", "africain": "Ousman", "occidental": "Acquisitio", "sens": "Gain, acquisition, croissance, récolte, profit."},
    "2112": {"bin": "0110", "africain": "Badara", "occidental": "Conjunctio", "sens": "Union, rencontre, lien, passage, médiation."},
    "2111": {"bin": "0111", "africain": "Malidjou", "occidental": "Caput Draconis", "sens": "Début, ouverture, entrée, naissance, nouvelle voie."},
    "1222": {"bin": "1000", "africain": "Adama", "occidental": "Laetitia", "sens": "Joie, élévation, expansion, satisfaction, ouverture."},
    "1221": {"bin": "1001", "africain": "Souleymane", "occidental": "Carcer", "sens": "Blocage, limite, prison, concentration, fermeture."},
    "1212": {"bin": "1010", "africain": "Inzan", "occidental": "Amissio", "sens": "Perte, détachement, abandon, libération, sortie."},
    "1211": {"bin": "1011", "africain": "Tontigui", "occidental": "Puella", "sens": "Beauté, douceur, harmonie, affection, charme."},
    "1122": {"bin": "1100", "africain": "Kalalao", "occidental": "Fortuna Minor", "sens": "Petite fortune, chance rapide, opportunité temporaire."},
    "1121": {"bin": "1101", "africain": "Sedjou", "occidental": "Puer", "sens": "Force, impulsion, courage, combat, énergie active."},
    "1112": {"bin": "1110", "africain": "Lassana", "occidental": "Cauda Draconis", "sens": "Fin, sortie, queue du dragon, fermeture de cycle."},
    "1111": {"bin": "1111", "africain": "Ibrahim", "occidental": "Via", "sens": "Route, mouvement, voyage, chemin, transformation."},
}

BIN_TO_DATA = {v["bin"]: v for v in FIGURES.values()}
BIN_TO_CODE = {v["bin"]: c for c, v in FIGURES.items()}
TOUTES_LES_FIGURES = list(FIGURES.keys())

NOM_TO_CODE = {}
for code, data in FIGURES.items():
    NOM_TO_CODE[data["africain"].lower().replace(" ", "")] = code
    NOM_TO_CODE[data["occidental"].lower().replace(" ", "")] = code

NOM_TO_CODE.update({
    "sedjo": "1121", "sedjou": "1121",
    "malidjo": "2111", "malidjou": "2111",
    "lassana": "1112", "lasana": "1112",
    "kalalao": "1122", "kalala": "1122",
    "fortunamajor": "2211", "fortunaminor": "1122",
    "caputdraconis": "2111", "caudadraconis": "1112",
})

FEU = {"1121", "1222", "1122", "1212"}
VENT = {"2111", "2122", "2112", "2121"}
EAU = {"1111", "2222", "1112", "2212"}
TERRE = {"2211", "1221", "1211", "2221"}

def read_json(path, default):
    """Lit un fichier JSON. Essaie aussi dans le dossier Android si chemin relatif."""
    import os as _os
    try:
        if _os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    # Essayer dans le dossier de l'app Android
    if not _os.path.isabs(path):
        try:
            from kivy.utils import platform as _p
            if _p == "android":
                from android.storage import app_storage_path
                alt = _os.path.join(app_storage_path(), path)
                if _os.path.exists(alt):
                    with open(alt, "r", encoding="utf-8") as f:
                        return json.load(f)
        except Exception:
            pass
    return default

def write_json(path, data):
    """Écrit un fichier JSON. Sur Android, utilise le dossier de l'app."""
    import os as _os
    # Sur Android, forcer le dossier app_storage
    write_path = path
    if not _os.path.isabs(path):
        try:
            from kivy.utils import platform as _p
            if _p == "android":
                from android.storage import app_storage_path
                write_path = _os.path.join(app_storage_path(), path)
        except Exception:
            pass
    try:
        _os.makedirs(_os.path.dirname(_os.path.abspath(write_path)), exist_ok=True)
        with open(write_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # Dernier recours : essayer le chemin original
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def _get_saved_file():
    """Retourne le chemin de geostar_saved_combos.json compatible Android."""
    import os as _os
    try:
        from kivy.utils import platform as _p
        if _p == "android":
            from android.storage import app_storage_path
            return _os.path.join(app_storage_path(), "geostar_saved_combos.json")
    except Exception:
        pass
    return _get_saved_file()


def normaliser(txt):
    return txt.strip().lower().replace(" ", "").replace("-", "")

def entree_vers_code(entree):
    e = normaliser(entree)
    if len(e) == 4 and all(c in "12" for c in e):
        return e
    if e in NOM_TO_CODE:
        return NOM_TO_CODE[e]
    raise ValueError("Figure inconnue : utilise 1121 ou Sedjou/Puer.")

def code_vers_bin(code):
    code = entree_vers_code(code)
    return "".join("1" if c == "1" else "0" for c in code)

def bin_vers_code(bits):
    return bits.replace("0", "2")

def data_fig(bits):
    return BIN_TO_DATA.get(bits, {"africain": "Quantique", "occidental": "Quantum", "sens": "Figure contenant Q."})

def element_of_bits(bits):
    if bits not in BIN_TO_CODE:
        return "quantique"
    code = BIN_TO_CODE[bits]
    if code in FEU: return "feu"
    if code in VENT: return "vent"
    if code in EAU: return "eau"
    if code in TERRE: return "terre"
    return "neutre"

def element_color(element):
    if element == "feu": return (1.0, 0.18, 0.12, 1)
    if element == "vent": return (0.60, 0.60, 0.60, 1)
    if element == "eau": return (0.15, 0.42, 1.0, 1)
    if element == "terre": return (0.20, 0.62, 0.25, 1)
    if element == "quantique": return (0.65, 0.30, 1.0, 1)
    return (1, 1, 1, 1)

def xor_bits(a, b):
    out = ""
    for x, y in zip(a, b):
        xx = x if x in "01" else "0"
        yy = y if y in "01" else "0"
        out += "1" if xx != yy else "0"
    return out

def creer_filles(meres):
    return ["".join(m[i] for m in meres) for i in range(4)]

def developper_theme(m1, m2, m3, m4):
    meres = [code_vers_bin(m1), code_vers_bin(m2), code_vers_bin(m3), code_vers_bin(m4)]
    h = {}
    for i, m in enumerate(meres, 1):
        h[i] = m
    filles = creer_filles(meres)
    for i, f in enumerate(filles, 5):
        h[i] = f
    h[9] = xor_bits(h[1], h[2])
    h[10] = xor_bits(h[3], h[4])
    h[11] = xor_bits(h[5], h[6])
    h[12] = xor_bits(h[7], h[8])
    h[13] = xor_bits(h[9], h[10])
    h[14] = xor_bits(h[11], h[12])
    h[15] = xor_bits(h[13], h[14])
    h[16] = xor_bits(h[1], h[15])
    return h

def analyser_repetitions(h):
    rep = {}
    for i, b in h.items():
        rep.setdefault(b, []).append(i)
    return {b: pos for b, pos in rep.items() if len(pos) >= 2}

def analyser_portes(h):
    defs = {
        "5-10-16": [5, 10, 16],
        "3-10-15": [3, 10, 15],
        "7-13": [7, 13],
        "7-15": [7, 15],
        "7-13-15": [7, 13, 15],
    }
    out = []
    for nom, pos in defs.items():
        vals = [h[p] for p in pos]
        if all(v == vals[0] for v in vals):
            out.append((nom, vals[0], pos))
    return out

def parse_positions(txt):
    nums = [int(x) for x in re.findall(r"\d+", txt)]
    nums = [n for n in nums if 1 <= n <= 16]
    out = []
    for n in nums:
        if n not in out:
            out.append(n)
    if len(out) < 2:
        raise ValueError("Il faut au moins deux maisons. Exemple : M8 M7 M3 M9")
    return out

def search_strict_positions(positions, target_bits=None, rare=False):
    solutions = []
    seen = set()
    for m1 in TOUTES_LES_FIGURES:
        for m2 in TOUTES_LES_FIGURES:
            for m3 in TOUTES_LES_FIGURES:
                for m4 in TOUTES_LES_FIGURES:
                    h = developper_theme(m1, m2, m3, m4)
                    vals = [h[p] for p in positions]
                    if not all(v == vals[0] for v in vals):
                        continue
                    fig = vals[0]
                    if target_bits is not None and fig != target_bits:
                        continue
                    exact_pos = [i for i in range(1, 17) if h[i] == fig]
                    if exact_pos != positions:
                        continue
                    secondary = ""
                    if rare:
                        if h[7] == h[13] and h[7] != fig:
                            secondary = "7-13 " + data_fig(h[7])["africain"]
                        elif h[7] == h[15] and h[7] != fig:
                            secondary = "7-15 " + data_fig(h[7])["africain"]
                        else:
                            continue
                    key = (m1, m2, m3, m4, tuple(positions), fig, secondary)
                    if key in seen:
                        continue
                    seen.add(key)
                    solutions.append({"m1": m1, "m2": m2, "m3": m3, "m4": m4, "positions": positions[:], "figure": fig, "secondary": secondary})
    return solutions

class FigureCard(Widget):
    def __init__(self, maison=1, bits="0000", root=None, repeated=False, **kwargs):
        super().__init__(**kwargs)
        self.maison = maison
        self.bits = bits
        self.root = root
        self.repeated = repeated
        self.drag_enabled = False
        self.dx = 0
        self.dy = 0
        self.long_event = None
        self.bind(pos=self.redraw, size=self.redraw)

    def set_bits(self, bits):
        self.bits = bits
        self.redraw()

    def enable_drag(self, dt):
        self.drag_enabled = True
        self.pos_hint = {}
        self.size_hint = (None, None)
        self.size = (self.width, self.height)
        if self.root:
            self.root.info.text = "Déplacement activé : glisse la figure."

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.drag_enabled = False
            self.dx = self.x - touch.x
            self.dy = self.y - touch.y
            touch.grab(self)
            self.long_event = Clock.schedule_once(self.enable_drag, 3.0)
            return True
        return False

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if self.drag_enabled:
                self.x = touch.x + self.dx
                self.y = touch.y + self.dy
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self.long_event:
                self.long_event.cancel()
                self.long_event = None
            if not self.drag_enabled and self.root:
                self.root.popup_edit_figure(self.maison)
            self.drag_enabled = False
            return True
        return False

    def draw_symbol(self, cx, cy, dot_r, sep, symbol):
        if symbol == "1":
            Ellipse(pos=(cx-dot_r, cy-dot_r), size=(dot_r*2, dot_r*2))
        elif symbol == "0":
            Ellipse(pos=(cx-sep-dot_r, cy-dot_r), size=(dot_r*2, dot_r*2))
            Ellipse(pos=(cx+sep-dot_r, cy-dot_r), size=(dot_r*2, dot_r*2))
        elif symbol == "Q":
            Line(circle=(cx, cy, dot_r*1.45), width=2)
            Ellipse(pos=(cx-dot_r*0.35, cy-dot_r*0.35), size=(dot_r*0.7, dot_r*0.7))
        else:
            Ellipse(pos=(cx-dot_r, cy-dot_r), size=(dot_r*2, dot_r*2))

    def redraw(self, *args):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        if w <= 5 or h <= 5:
            return
        with self.canvas:
            if self.repeated:
                Color(*element_color(element_of_bits(self.bits)))
            else:
                Color(1, 1, 1, 1)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(5)])
            Color(0, 0, 0, 1)
            top = h * 0.17
            bottom = h * 0.13
            row_gap = (h - top - bottom) / 4.0
            dot_r = min(w, h) * 0.055
            sep = w * 0.18
            for i, b in enumerate(self.bits):
                cy = y + h - top - (i+0.5)*row_gap
                cx = x + w/2
                self.draw_symbol(cx, cy, dot_r, sep, b)
            Color(0, 0, 0, 0.25)
            Line(rounded_rectangle=(x, y, w, h, dp(5)), width=1)

class MoneyRoot(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = (0.02, 0.72, 0.70, 1)
        self.h = developper_theme("2121", "2111", "1112", "1121")
        self.mother_codes = ["2121", "2111", "1112", "1121"]
        self.notes = read_json(NOTES_FILE, [])
        self.solution_cache = read_json(CACHE_FILE, {})
        self.custom_searches = read_json(CUSTOM_FILE, [])
        self.active_solutions = []
        self.active_solution_index = -1
        self.active_notes = []
        self.active_note_index = -1
        self.cards = {}
        self.labels = {}
        self.swipe_start = None
        self.build_ui()
        Clock.schedule_once(lambda dt: self.afficher_theme(self.h), 0.2)


    def build_ui(self):
        with self.canvas.before:
            Color(0.02, 0.72, 0.70, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.title = Label(text="[b]GEOSTAR[/b]\n" + datetime.now().strftime("%d/%m/%Y %H:%M:%S"), markup=True, font_size=dp(20), color=(1,1,1,1), size_hint=(0.76, None), height=dp(70), pos_hint={"x": 0.12, "top": 1})
        self.add_widget(self.title)

        note_btn = Button(text="NOTE", font_size=dp(13), bold=True, size_hint=(0.12, None), height=dp(50), pos_hint={"x":0.87, "top":0.99})
        note_btn.bind(on_release=lambda x: self.popup_notes_current())
        self.add_widget(note_btn)

        # Bouton SAVE theme (a cote de NOTE)
        save_theme_btn = Button(text="SAVE", font_size=dp(11), bold=True,
            size_hint=(0.10, None), height=dp(50),
            pos_hint={"x":0.75, "top":0.99},
            background_color=(0.1,0.5,0.25,1))
        def save_current_theme(_):
            import os as _os
            SAVED_FILE = _get_saved_file()
            ms = getattr(self, "mother_codes", None)
            if not ms or len(ms) < 4:
                self.message("Attention","Aucun theme actif.")
                return
            saved = read_json(SAVED_FILE, [])
            theme = developper_theme(*ms)
            # Detecter la figure principale
            from collections import Counter
            all_figs = [theme[i] for i in range(1,17)]
            fig_bits = Counter(all_figs).most_common(1)[0][0]
            fig_nom = FIGURES.get(fig_bits, {}).get("africain","?")
            pos_list = [i for i in range(1,17) if theme[i]==fig_bits]
            pos_str = "M"+"M".join(str(p) for p in pos_list)
            entry = {
                "figure_nom": fig_nom,
                "figure_bits": fig_bits,
                "positions_str": pos_str,
                "mode": "THEME",
                "m1": ms[0], "m2": ms[1], "m3": ms[2], "m4": ms[3]
            }
            if entry not in saved:
                saved.append(entry)
                write_json(SAVED_FILE, saved)
                self.message("Enregistre", "Theme sauvegarde dans COMBINAISONS.\nM1="+ms[0]+" M2="+ms[1]+" M3="+ms[2]+" M4="+ms[3])
            else:
                self.message("Deja enregistre","Ce theme est deja dans COMBINAISONS.")
        save_theme_btn.bind(on_release=save_current_theme)
        self.add_widget(save_theme_btn)

        notes_list_btn = Button(text="FAVORIS", font_size=dp(11), bold=True, size_hint=(0.13, None), height=dp(50), pos_hint={"x":0.01, "top":0.99}, background_color=(0.55,0.35,0.0,1))
        notes_list_btn.bind(on_release=lambda x: self.popup_notes_list())
        self.add_widget(notes_list_btn)

        self.board = FloatLayout(size_hint=(1, 0.73), pos_hint={"x": 0, "y": 0.17})
        self.board.bind(on_touch_down=self.board_touch_down, on_touch_up=self.board_touch_up)
        self.add_widget(self.board)

        self.info = Label(text="", font_size=dp(15), bold=True, color=(1,1,1,1), halign="left", valign="middle", size_hint=(1, None), height=dp(65), pos_hint={"x": 0.02, "y": 0.10})
        self.info.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        self.add_widget(self.info)



        # Boutons navigation gauche/droite
        nav_bar = BoxLayout(orientation="horizontal", spacing=dp(4), size_hint=(0.30, None), height=dp(40), pos_hint={"right":0.99, "y":0.105})
        btn_prev = Button(text="◀ Préc.", font_size=dp(11), background_color=(0.2,0.2,0.4,1))
        btn_next = Button(text="Suiv. ▶", font_size=dp(11), background_color=(0.2,0.2,0.4,1))
        def go_prev(_):
            notes = getattr(self,"active_notes",[])
            sols = getattr(self,"active_solutions",[])
            if notes and getattr(self,"active_note_index",-1) >= 0:
                self.active_note_index = (self.active_note_index - 1) % len(notes)
                self.load_note(notes[self.active_note_index])
            elif sols:
                # Initialiser l'index si besoin
                if not hasattr(self, "active_solution_index") or self.active_solution_index < 0:
                    self.active_solution_index = 0
                if hasattr(self, "solution_previous"):
                    self.solution_previous()

        def go_next(_):
            notes = getattr(self,"active_notes",[])
            sols = getattr(self,"active_solutions",[])
            if notes and getattr(self,"active_note_index",-1) >= 0:
                self.active_note_index = (self.active_note_index + 1) % len(notes)
                self.load_note(notes[self.active_note_index])
            elif sols:
                # Initialiser l'index si besoin
                if not hasattr(self, "active_solution_index") or self.active_solution_index < 0:
                    self.active_solution_index = 0
                if hasattr(self, "solution_next"):
                    self.solution_next()
        btn_prev.bind(on_release=go_prev)
        btn_next.bind(on_release=go_next)
        nav_bar.add_widget(btn_prev)
        nav_bar.add_widget(btn_next)
        self.add_widget(nav_bar)

        bar = BoxLayout(orientation="horizontal", spacing=dp(5), padding=dp(5), size_hint=(1, 0.10), pos_hint={"x": 0, "y": 0})
        self.add_widget(bar)
        for txt, fn in [("THEME", self.popup_theme), ("HASARD", self.theme_hasard), ("FIGURE", self.figure_hasard), ("SOLUTIONS", self.popup_solutions), ("TABLE", self.popup_table)]:
            b = Button(text=txt, bold=True)
            b.bind(on_release=lambda btn, f=fn: f())
            bar.add_widget(b)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def board_touch_down(self, instance, touch):
        self.swipe_start = (touch.x, touch.y)
        return False

    def board_touch_up(self, instance, touch):
        if not self.swipe_start:
            return False
        sx, sy = self.swipe_start
        dx = touch.x - sx
        dy = touch.y - sy
        if abs(dx) > dp(80) and abs(dx) > abs(dy) * 1.5:
            if dx < 0:
                self.solution_next()
            else:
                self.solution_previous()
            return True
        return False

    def maison_positions(self):
        return {
            8:(0.04,0.79,0.10,0.18), 7:(0.16,0.79,0.10,0.18), 6:(0.28,0.79,0.10,0.18), 5:(0.40,0.79,0.10,0.18),
            4:(0.52,0.79,0.10,0.18), 3:(0.64,0.79,0.10,0.18), 2:(0.76,0.79,0.10,0.18), 1:(0.88,0.79,0.10,0.18),
            12:(0.10,0.57,0.10,0.18), 11:(0.34,0.57,0.10,0.18), 10:(0.58,0.57,0.10,0.18), 9:(0.82,0.57,0.10,0.18),
            14:(0.28,0.35,0.10,0.18), 13:(0.68,0.35,0.10,0.18), 15:(0.48,0.18,0.10,0.18), 16:(0.84,0.18,0.10,0.18),
        }

    def repeated_positions(self):
        reps = analyser_repetitions(self.h)
        pos = set()
        for bits, maisons in reps.items():
            if len(maisons) >= 2:
                for m in maisons:
                    pos.add(m)
        return pos

    def add_card(self, maison, bits, rx, ry, rw, rh, repeated=False, *args, **kwargs):
        card = FigureCard(maison=maison, bits=bits, root=self, repeated=repeated, size_hint=(rw, rh), pos_hint={"x":rx, "y":ry})
        label = Label(text=f"[b]M{maison}[/b]", markup=True, color=(1,0.86,0.05,1), font_size=dp(14), size_hint=(rw,None), height=dp(22), pos_hint={"x":rx, "y":ry+rh})
        self.board.add_widget(label)
        self.board.add_widget(card)
        self.cards[maison] = card
        self.labels[maison] = label

    def afficher_theme(self, h):
        self.h = h
        self.board.clear_widgets()
        self.cards = {}
        self.labels = {}
        repeated = self.repeated_positions()
        for maison, (rx, ry, rw, rh) in self.maison_positions().items():
            self.add_card(maison, h[maison], rx, ry, rw, rh, repeated=(maison in repeated))
        self.title.text = "[b]GEOSTAR[/b]\n" + datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.mettre_infos()

    def mettre_infos(self):
        portes = analyser_portes(self.h)
        texte = " | ".join([f"{p[0]}:{data_fig(p[1])['africain']}" for p in portes]) if portes else "Aucune porte"
        actifs = sum(bits.count("1") for bits in self.h.values())
        passifs = sum(bits.count("0") for bits in self.h.values())
        nav = ""
        if self.active_solutions and self.active_solution_index >= 0:
            nav = f"\nSolution {self.active_solution_index+1}/{len(self.active_solutions)} — glisse gauche/droite"
        self.info.text = f"Actifs : {actifs} | Passifs : {passifs}\nPortes : {texte}{nav}"

    def popup_theme(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
        inputs = []
        for i, ex in enumerate(["Ousman ou 2121", "Malidjou ou 2111", "Lassana ou 1112", "Sedjou ou 1121"]):
            ti = TextInput(hint_text=f"M{i+1} : {ex}", multiline=False)
            box.add_widget(ti); inputs.append(ti)
        btn = Button(text="DEVELOPPER", size_hint=(1,None), height=dp(45)); box.add_widget(btn)
        pop = Popup(title="Entrer les 4 Mères", content=box, size_hint=(0.92,0.65))
        def go(_):
            try:
                vals = [x.text.strip() for x in inputs]
                if any(v == "" for v in vals): raise ValueError("Remplis les 4 mères.")
                self.mother_codes = [entree_vers_code(v) for v in vals]
                self.clear_active_solutions()
                self.afficher_theme(developper_theme(*self.mother_codes))
                pop.dismiss()
            except Exception as e:
                self.message("Erreur", str(e))
        btn.bind(on_release=go); pop.open()

    def theme_hasard(self):
        """Menu Reduction Binaire : Auto ou Manuel"""
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        box.add_widget(Label(
            text="[b]RÉDUCTION BINAIRE[/b]\nMéthode géomantique traditionnelle",
            markup=True, color=(1,1,1,1),
            size_hint=(1,None), height=dp(60), halign="center"
        ))
        btn_auto = Button(
            text="AUTOMATIQUE\n16 points aléatoires",
            size_hint=(1,None), height=dp(65),
            background_color=(0.1,0.55,0.35,1), font_size=dp(14)
        )
        btn_manuel = Button(
            text="MANUEL\nTape tes propres points",
            size_hint=(1,None), height=dp(65),
            background_color=(0.15,0.4,0.7,1), font_size=dp(14)
        )
        btn_simple = Button(
            text="ALÉATOIRE SIMPLE\n(ancienne méthode)",
            size_hint=(1,None), height=dp(50),
            background_color=(0.3,0.3,0.3,1), font_size=dp(12)
        )
        btn_close = Button(text="ANNULER", size_hint=(1,None), height=dp(42))
        box.add_widget(btn_auto)
        box.add_widget(btn_manuel)
        box.add_widget(btn_simple)
        box.add_widget(btn_close)
        pop = Popup(title="Générer un Thème", content=box, size_hint=(0.9,0.6))
        def do_auto(_):
            pop.dismiss()
            self._rb_auto()
        def do_manuel(_):
            pop.dismiss()
            self._rb_manuel()
        def do_simple(_):
            pop.dismiss()
            ms = [random.choice(TOUTES_LES_FIGURES) for _ in range(4)]
            self.mother_codes = ms
            self.clear_active_solutions()
            self.clear_note_zone() if hasattr(self,"clear_note_zone") else None
            self.afficher_theme(developper_theme(*ms))
        btn_auto.bind(on_release=do_auto)
        btn_manuel.bind(on_release=do_manuel)
        btn_simple.bind(on_release=do_simple)
        btn_close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    def _rb_points_vers_meres(self, points):
        meres = []
        for m in range(4):
            bits = ""
            for ligne in range(4):
                n = points[m * 4 + ligne]
                bits += "1" if (n % 2 == 1) else "2"
            meres.append(bits)
        return meres

    def _rb_auto(self):
        points = [random.randint(1, 9) for _ in range(16)]
        meres = self._rb_points_vers_meres(points)
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
        txt = "[b]Points générés :[/b]\n"
        noms = ["Mère 1","Mère 2","Mère 3","Mère 4"]
        for m in range(4):
            lignes = points[m*4:(m+1)*4]
            code = meres[m]
            nom = FIGURES.get(code, {}).get("africain", "?")
            occ = FIGURES.get(code, {}).get("occidental", "?")
            pts_str = "  ".join(f"{p}→{'1' if p%2==1 else '2'}" for p in lignes)
            txt += f"\n[b]{noms[m]}[/b] = {code} {nom} / {occ}\n{pts_str}\n"
        sv = ScrollView()
        lab = Label(text=txt, markup=True, color=(1,1,1,1), size_hint_y=None, halign="left", valign="top")
        lab.bind(texture_size=lambda i,v: setattr(i,"height",v[1]))
        lab.bind(width=lambda i,v: setattr(i,"text_size",(v,None)))
        sv.add_widget(lab)
        box.add_widget(sv)
        bb = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(44), spacing=dp(4))
        b_app = Button(text="APPLIQUER", background_color=(0.1,0.6,0.3,1))
        b_reg = Button(text="REGÉNÉRER")
        b_ann = Button(text="ANNULER")
        bb.add_widget(b_app); bb.add_widget(b_reg); bb.add_widget(b_ann)
        box.add_widget(bb)
        pop = Popup(title="Réduction Binaire — Auto", content=box, size_hint=(0.97,0.88))
        def appliquer(_):
            pop.dismiss()
            self.mother_codes = meres
            self.clear_active_solutions()
            self.afficher_theme(developper_theme(*meres))
        b_app.bind(on_release=appliquer)
        b_reg.bind(on_release=lambda x: (pop.dismiss(), self._rb_auto()))
        b_ann.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    def _rb_manuel(self):
        noms = ["Mere 1","Mere 2","Mere 3","Mere 4"]
        counts = [0] * 16
        btns = []

        def get_text(i):
            n = counts[i]
            if n == 0:
                return "L" + str(i+1) + "\n[ ]"
            bit = "1" if n % 2 == 1 else "2"
            return "L" + str(i+1) + " =" + bit + "\n" + str(n) + "pts"

        def get_color(i):
            n = counts[i]
            if n == 0: return (0.2,0.2,0.2,1)
            return (0.1,0.5,0.2,1) if n % 2 == 1 else (0.55,0.28,0.0,1)

        def tap(i):
            counts[i] += 1
            btns[i].text = get_text(i)
            btns[i].background_color = get_color(i)

        def reset_one(i):
            counts[i] = 0
            btns[i].text = get_text(i)
            btns[i].background_color = get_color(i)

        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))

        lbl = Label(
            text="Appuie pour +1 point  |  Double-appuie pour effacer",
            color=(0.85,0.85,0.85,1), size_hint=(1,None), height=dp(32),
            font_size=dp(11), halign="center"
        )
        box.add_widget(lbl)

        for m in range(4):
            box.add_widget(Label(
                text="[b]" + noms[m] + "[/b]", markup=True,
                color=(0.3,0.9,0.6,1), size_hint=(1,None), height=dp(24),
                font_size=dp(12)
            ))
            row = GridLayout(cols=4, spacing=dp(5), size_hint=(1,None), height=dp(75))
            for lg in range(4):
                i = m * 4 + lg
                b = Button(
                    text=get_text(i),
                    font_size=dp(12),
                    background_color=get_color(i),
                    halign="center"
                )
                btns.append(b)
                b.bind(on_touch_down=lambda btn, touch, idx=i: (
                    tap(idx) if btn.collide_point(*touch.pos) else None
                ))
                row.add_widget(b)
            box.add_widget(row)

        bbar = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(44), spacing=dp(4))
        b_rnd = Button(text="Hasard", background_color=(0.25,0.25,0.5,1))
        b_clr = Button(text="Effacer", background_color=(0.5,0.1,0.1,1))
        b_ok  = Button(text="CALCULER", background_color=(0.1,0.5,0.2,1))
        bbar.add_widget(b_rnd); bbar.add_widget(b_clr); bbar.add_widget(b_ok)
        box.add_widget(bbar)
        b_ann = Button(text="ANNULER", size_hint=(1,None), height=dp(40))
        box.add_widget(b_ann)

        pop = Popup(title="Points — Tactile", content=box, size_hint=(0.97,0.97))

        def do_rnd(_):
            for i in range(16):
                counts[i] = random.randint(1,9)
                btns[i].text = get_text(i)
                btns[i].background_color = get_color(i)

        def do_clr(_):
            for i in range(16):
                counts[i] = 0
                btns[i].text = get_text(i)
                btns[i].background_color = get_color(i)

        def calculer(_):
            if any(c == 0 for c in counts):
                self.message("Attention","Appuie sur chaque case (au moins 1 fois).")
                return
            meres = self._rb_points_vers_meres(counts)
            pop.dismiss()
            nms = ["Mere 1","Mere 2","Mere 3","Mere 4"]
            txt = "[b]Resultat :[/b]\n"
            for m in range(4):
                lgs = counts[m*4:(m+1)*4]
                code = meres[m]
                nom = FIGURES.get(code,{}).get("africain","?")
                occ = FIGURES.get(code,{}).get("occidental","?")
                ps = "  ".join(str(p)+("->1" if p%2==1 else "->2") for p in lgs)
                txt += "\n[b]" + nms[m] + "[/b] = " + code + " (" + nom + "/" + occ + ")\n" + ps + "\n"
            rb = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
            sv2 = ScrollView()
            lab = Label(text=txt, markup=True, color=(1,1,1,1), size_hint_y=None, halign="left", valign="top")
            lab.bind(texture_size=lambda i,v: setattr(i,"height",v[1]))
            lab.bind(width=lambda i,v: setattr(i,"text_size",(v,None)))
            sv2.add_widget(lab); rb.add_widget(sv2)
            bb2 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(44), spacing=dp(4))
            ba = Button(text="APPLIQUER", background_color=(0.1,0.6,0.3,1))
            br = Button(text="RETOUR")
            bb2.add_widget(ba); bb2.add_widget(br); rb.add_widget(bb2)
            pop2 = Popup(title="Resultat", content=rb, size_hint=(0.97,0.85))
            def app2(_):
                pop2.dismiss()
                self.mother_codes = meres
                self.clear_active_solutions()
                self.afficher_theme(developper_theme(*meres))
            ba.bind(on_release=app2)
            br.bind(on_release=lambda x: (pop2.dismiss(), self._rb_manuel()))
            pop2.open()

        b_rnd.bind(on_release=do_rnd)
        b_clr.bind(on_release=do_clr)
        b_ok.bind(on_release=calculer)
        b_ann.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    def figure_hasard(self):
        code = random.choice(TOUTES_LES_FIGURES)
        bits = code_vers_bin(code)
        d = data_fig(bits)
        self.message("Figure aléatoire", f"{d['africain']} / {d['occidental']}\nCode : {code}\nÉlément : {element_of_bits(bits)}\n\n{d['sens']}")

    def popup_edit_figure(self, maison):
        bits = self.h[maison]
        d = data_fig(bits)
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(text=f"Maison {maison}\n{d['africain']} / {d['occidental']}\nClic court = modifier. Appui long 3 secondes = déplacer.\nQ = superposition simple.", color=(1,1,1,1), size_hint=(1,None), height=dp(110)))
        grid = GridLayout(cols=3, spacing=dp(4), size_hint=(1,None), height=dp(170)); box.add_widget(grid)
        def mk(line, sym, label):
            b = Button(text=f"L{line+1}\n{label}")
            def act(_):
                self.apply_symbol(maison, line, sym); pop.dismiss()
            b.bind(on_release=act); return b
        for line in range(4):
            grid.add_widget(mk(line, "1", "1 point"))
            grid.add_widget(mk(line, "0", "2 points"))
            grid.add_widget(mk(line, "Q", "Q"))
        close = Button(text="FERMER", size_hint=(1,None), height=dp(42)); box.add_widget(close)
        pop = Popup(title="Modifier la figure", content=box, size_hint=(0.92,0.75))
        close.bind(on_release=lambda x: pop.dismiss()); pop.open()

    def apply_symbol(self, maison, line, sym):
        old = self.h[maison]
        new = old[:line] + sym + old[line+1:]
        self.h[maison] = new
        if maison in self.cards: self.cards[maison].set_bits(new)
        if maison in [1,2,3,4] and sym in ["1","0"]:
            mother_bits = [self.h[i] for i in [1,2,3,4]]
            if all(set(x).issubset(set("01")) for x in mother_bits):
                self.mother_codes = [bin_vers_code(x) for x in mother_bits]
                self.clear_active_solutions()
                self.afficher_theme(developper_theme(*self.mother_codes)); return
        self.mettre_infos()

    def current_key(self):
        return "-".join(self.mother_codes)

    def popup_notes_current(self):
        existing = None
        for n in self.notes:
            if n.get("key") == self.current_key():
                existing = n; break
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        name = TextInput(hint_text="Nom de la note", multiline=False, text=existing.get("nom", "") if existing else "")
        note = TextInput(hint_text="Note écrite", multiline=True, text=existing.get("note", "") if existing else "")
        vocal = TextInput(hint_text="Mémo vocal : nom du fichier ou remarque", multiline=False, text=existing.get("vocal", "") if existing else "")
        box.add_widget(name); box.add_widget(note); box.add_widget(vocal)
        btns = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        save_btn = Button(text="ENREGISTRER"); mic_btn = Button(text="MICRO"); delete_btn = Button(text="SUPPRIMER")
        btns.add_widget(save_btn); btns.add_widget(mic_btn); btns.add_widget(delete_btn); box.add_widget(btns)
        pop = Popup(title="NOTE du thème", content=box, size_hint=(0.94,0.78))
        def save(_):
            item = {"key": self.current_key(), "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "nom": name.text.strip() or "Note sans nom", "note": note.text.strip(), "vocal": vocal.text.strip(), "meres": self.mother_codes, "maisons": {str(k): v for k, v in self.h.items()}}
            found = False
            for i, n in enumerate(self.notes):
                if n.get("key") == item["key"]:
                    self.notes[i] = item; found = True; break
            if not found: self.notes.append(item)
            write_json(NOTES_FILE, self.notes)
            pop.dismiss(); self.message("NOTE", "Note enregistrée.")
        def delete(_):
            self.notes = [n for n in self.notes if n.get("key") != self.current_key()]
            write_json(NOTES_FILE, self.notes)
            pop.dismiss(); self.message("NOTE", "Note supprimée.")
        save_btn.bind(on_release=save); delete_btn.bind(on_release=delete); mic_btn.bind(on_release=lambda x: self.open_micro())
        pop.open()

    def open_micro(self):
        if platform == "android":
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                MediaStore = autoclass("android.provider.MediaStore")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(MediaStore.Audio.Media.RECORD_SOUND_ACTION)
                PythonActivity.mActivity.startActivity(intent)
                self.message("Micro", "Le micro Android a été ouvert. Enregistre ton mémo, puis indique son nom dans la note.")
            except Exception as e:
                self.message("Micro", "Impossible d'ouvrir le micro automatiquement ici. Utilise l'application Enregistreur vocal puis écris le nom du fichier dans la note.\n\n" + str(e))
        else:
            self.message("Micro", "Sur iPhone, le micro devra être branché lors du packaging iOS. Pour l'instant, écris le nom du fichier vocal dans la note.")

    def popup_notes_list(self):
        box = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(6))
        box.add_widget(Label(
            text="Favoris — " + str(len(self.notes)) + " note(s)",
            color=(1,1,1,1), size_hint=(1,None), height=dp(36)
        ))
        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        sv.add_widget(grid)
        for idx, n in enumerate(self.notes):
            meres = n.get("meres", ["","","",""])
            txt = (n.get("nom","Sans nom") + " | " + n.get("date","") +
                   "\nM1=" + meres[0] + " M2=" + meres[1] +
                   " M3=" + meres[2] + " M4=" + meres[3])
            b = Button(text=txt, font_size=dp(11), size_hint_y=None, height=dp(58))
            def on_note(btn, note=n, i=idx):
                pop.dismiss()
                # Activer la navigation notes via boutons Prec/Suiv
                self.active_notes = self.notes
                self.active_note_index = i
                self.load_note(note)
            b.bind(on_release=on_note)
            grid.add_widget(b)
        box.add_widget(sv)
        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        box.add_widget(close)
        pop = Popup(title="FAVORIS", content=box, size_hint=(0.95,0.88))
        close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    def load_note(self, note):
        meres = note.get("meres")
        if meres and len(meres) == 4:
            # Afficher le thème du favori visuellement SANS écraser mother_codes.
            # Ainsi HASARD/THEME/SOLUTIONS restent libres après consultation.
            self._loading_fav = True
            self.active_solutions = []
            self.active_solution_index = -1
            self.afficher_theme(developper_theme(*meres))
            self._loading_fav = False
            self._update_note_zone(note)

    def _update_note_zone(self, note=None):
        pass  # zone note supprimée

    def clear_active_solutions(self):
        self.active_solutions = []
        self.active_solution_index = -1
        # Quitter aussi le mode navigation favoris
        self.active_notes = []
        self.active_note_index = -1

    def clear_note_zone(self):
        """Appeler quand on charge un theme non-favori."""
        self.active_notes = []
        self.active_note_index = -1
        self._update_note_zone(None)

    def cache_key(self, positions, rare=False):
        return ("rare_" if rare else "strict_") + "_".join(map(str, positions))

    def get_solutions_cached(self, positions, rare=False):
        key = self.cache_key(positions, rare)
        if key in self.solution_cache:
            return self.solution_cache[key]
        sols = search_strict_positions(positions, None, rare)
        self.solution_cache[key] = sols
        write_json(CACHE_FILE, self.solution_cache)
        return sols

    def popup_solutions(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(text="Solutions intégrées + recherches personnalisées.", color=(1,1,1,1), size_hint=(1,None), height=dp(40)))
        options = [
            ("5-10-16 toutes", [5,10,16], False),
            ("5-10-16 rares 7-13/7-15", [5,10,16], True),
            ("3-10-15 toutes", [3,10,15], False),
            ("10-11-15", [10,11,15], False),
            ("3-11-15", [3,11,15], False),
            ("2-3-13", [2,3,13], False),
            ("10-13-15", [10,13,15], False),
            ("2-10-15", [2,10,15], False),
        ]
        for name, pos, rare in options:
            b = Button(text=name, size_hint=(1,None), height=dp(40))
            b.bind(on_release=lambda btn, n=name, p=pos, r=rare: self.open_solution_window(n, p, r))
            box.add_widget(b)
        add = Button(text="+ AJOUTER RECHERCHE PERSONNALISÉE", size_hint=(1,None), height=dp(42))
        add.bind(on_release=lambda x: self.popup_add_custom_search()); box.add_widget(add)
        if self.custom_searches:
            box.add_widget(Label(text="Recherches perso :", color=(1,1,1,1), size_hint=(1,None), height=dp(28)))
            for item in self.custom_searches:
                b = Button(text=f"{item.get('name')} : {item.get('positions')}", size_hint=(1,None), height=dp(38))
                b.bind(on_release=lambda btn, it=item: self.open_solution_window(it.get("name","Perso"), it.get("positions",[]), False))
                box.add_widget(b)
        btn_fig = Button(text="🔍 CHERCHER PAR FIGURE + MAISONS", size_hint=(1,None), height=dp(42), background_color=(0.1,0.6,0.5,1))
        btn_fig.bind(on_release=lambda x: self.popup_search_by_figure())
        box.add_widget(btn_fig)
        manage = Button(text="SUPPRIMER UNE RECHERCHE PERSO", size_hint=(1,None), height=dp(42))
        manage.bind(on_release=lambda x: self.popup_delete_custom_search()); box.add_widget(manage)
        sv_main = ScrollView()
        sv_main.add_widget(box)
        outer = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(4))
        outer.add_widget(sv_main)
        btn_close_sols = Button(text="FERMER", size_hint=(1,None), height=dp(44),
                                background_color=(0.3,0.3,0.3,1))
        outer.add_widget(btn_close_sols)
        pop_sols = Popup(title="SOLUTIONS", content=outer, size_hint=(0.94,0.92))
        btn_close_sols.bind(on_release=lambda x: pop_sols.dismiss())
        pop_sols.open()

    def open_solution_window(self, title, positions, rare):
        content = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(6))
        header = Label(text=f"{title}\nOuverture...", color=(1,1,1,1), size_hint=(1,None), height=dp(55)); content.add_widget(header)
        sv = ScrollView(); grid = GridLayout(cols=1, spacing=dp(3), size_hint_y=None); grid.bind(minimum_height=grid.setter("height")); sv.add_widget(grid); content.add_widget(sv)
        close = Button(text="FERMER", size_hint=(1,None), height=dp(42)); content.add_widget(close)
        pop = Popup(title=title, content=content, size_hint=(0.98,0.92)); close.bind(on_release=lambda x: pop.dismiss()); pop.open()
        def fill(dt):
            try:
                sols = self.get_solutions_cached(positions, rare)
                header.text = f"{title}\nTotal : {len(sols)} solution(s)"
                for idx, sol in enumerate(sols, 1):
                    fig = data_fig(sol["figure"])["africain"]
                    sec = (" | " + sol["secondary"]) if sol.get("secondary") else ""
                    txt = f"{idx}. {fig} {sol['positions']}  M1={sol['m1']} M2={sol['m2']} M3={sol['m3']} M4={sol['m4']}{sec}"
                    b = Button(text=txt, font_size=dp(10), size_hint_y=None, height=dp(42))
                    b.bind(on_release=lambda btn, s=sol, sol_list=sols, pp=pop: self.apply_solution_from_list(s, sol_list, pp))
                    grid.add_widget(b)
            except Exception as e:
                header.text = "Erreur"; grid.add_widget(Label(text=str(e), color=(1,1,1,1), size_hint_y=None, height=dp(80)))
        Clock.schedule_once(fill, 0.1)

    def apply_solution_from_list(self, sol, sol_list, pop=None):
        if pop: pop.dismiss()
        self.active_solutions = sol_list
        try: self.active_solution_index = sol_list.index(sol)
        except ValueError: self.active_solution_index = 0
        self.apply_solution(sol)

    def apply_solution(self, sol):
        # Ferme tous les popups ouverts avant d'afficher le theme
        from kivy.uix.popup import Popup
        for widget in list(Popup._popup_stack) if hasattr(Popup, "_popup_stack") else []:
            try: widget.dismiss()
            except: pass
        # Quitter le mode navigation favoris
        self.active_notes = []
        self.active_note_index = -1
        self.mother_codes = [sol["m1"], sol["m2"], sol["m3"], sol["m4"]]
        self.afficher_theme(developper_theme(*self.mother_codes))

    def solution_next(self):
        if not self.active_solutions: return
        self.active_solution_index = (self.active_solution_index + 1) % len(self.active_solutions)
        self.apply_solution(self.active_solutions[self.active_solution_index])

    def solution_previous(self):
        if not self.active_solutions: return
        self.active_solution_index = (self.active_solution_index - 1) % len(self.active_solutions)
        self.apply_solution(self.active_solutions[self.active_solution_index])

    def popup_add_custom_search(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        name = TextInput(hint_text="Nom : exemple Retour contact", multiline=False, size_hint=(1,None), height=dp(44))
        positions = TextInput(hint_text="Maisons : exemple M8 M7 M3 M9 ou 8,7,3,9", multiline=False, size_hint=(1,None), height=dp(44))
        figure = TextInput(hint_text="Figure facultative : Oumar ou 2122. Vide = toutes", multiline=False, size_hint=(1,None), height=dp(44))
        box.add_widget(name); box.add_widget(positions); box.add_widget(figure)
        btn = Button(text="CALCULER ET ENREGISTRER", size_hint=(1,None), height=dp(45)); box.add_widget(btn)
        pop = Popup(title="Nouvelle recherche personnalisee", content=box, size_hint=(0.95,0.45))
        def save(_):
            try:
                pos = parse_positions(positions.text)
                fig_text = figure.text.strip()
                target_code = None
                if fig_text:
                    fig_key = fig_text.lower().replace(" ", "")
                    if fig_text in FIGURES:
                        target_code = fig_text
                    elif fig_key in NOM_TO_CODE:
                        target_code = NOM_TO_CODE[fig_key]
                    else:
                        self.message("Erreur", "Figure inconnue : " + fig_text)
                        return
                item = {"name": name.text.strip() or "Recherche perso", "positions": pos, "target_code": target_code}
                if item not in self.custom_searches:
                    self.custom_searches.append(item); write_json(CUSTOM_FILE, self.custom_searches)
                pop.dismiss()
                if target_code:
                    fig_name = FIGURES[target_code]["africain"]
                    title = (name.text.strip() or fig_name) + " M" + "+M".join(str(p) for p in sorted(pos))
                    self.open_search_by_figure_window(title, target_code, sorted(pos))
                else:
                    self.open_solution_window(item["name"], pos, False)
            except Exception as e:
                self.message("Erreur", str(e))
        btn.bind(on_release=save); pop.open()

    def popup_delete_custom_search(self):
        content = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(6))
        content.add_widget(Label(text="Choisis une recherche à supprimer.", color=(1,1,1,1), size_hint=(1,None), height=dp(40)))
        for item in self.custom_searches:
            b = Button(text=f"{item.get('name')} : {item.get('positions')}", size_hint=(1,None), height=dp(42))
            b.bind(on_release=lambda btn, it=item: self.delete_custom_search(it))
            content.add_widget(b)
        Popup(title="Supprimer recherche", content=content, size_hint=(0.92,0.75)).open()

    def delete_custom_search(self, item):
        self.custom_searches = [x for x in self.custom_searches if x != item]
        write_json(CUSTOM_FILE, self.custom_searches)
        self.message("Recherche", "Recherche supprimée.")

    def popup_search_by_figure(self):
        from kivy.uix.togglebutton import ToggleButton
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(text="1. Choisis la figure :", color=(1,1,1,1), size_hint=(1,None), height=dp(30)))
        fig_grid = GridLayout(cols=2, spacing=dp(4), size_hint=(1,None))
        fig_grid.bind(minimum_height=fig_grid.setter("height"))
        selected_figure = [None]
        for code, data in FIGURES.items():
            label = f"{data['africain']} / {data['occidental']}"
            tb = ToggleButton(text=label, group="figure_choice", size_hint=(1,None), height=dp(38), font_size=dp(11))
            def on_fig_toggle(btn, c=code):
                if btn.state == "down":
                    selected_figure[0] = c
            tb.bind(on_press=on_fig_toggle)
            fig_grid.add_widget(tb)
        sv_fig = ScrollView(size_hint=(1,None), height=dp(180))
        sv_fig.add_widget(fig_grid)
        box.add_widget(sv_fig)
        box.add_widget(Label(text="2. Choisis les maisons :", color=(1,1,1,1), size_hint=(1,None), height=dp(30)))
        maison_grid = GridLayout(cols=4, spacing=dp(4), size_hint=(1,None), height=dp(160))
        maison_buttons = {}
        for i in range(1, 17):
            tb = ToggleButton(text=f"M{i}", size_hint=(1,None), height=dp(36), font_size=dp(12))
            maison_buttons[i] = tb
            maison_grid.add_widget(tb)
        box.add_widget(maison_grid)
        # Boutons mode strict / non strict
        from kivy.uix.togglebutton import ToggleButton as TB2
        mode_box = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(40), spacing=dp(6))
        btn_strict = TB2(text="STRICTE", group="mode_search", state="down", size_hint=(0.5,1))
        btn_libre = TB2(text="NON STRICTE", group="mode_search", size_hint=(0.5,1))
        mode_box.add_widget(btn_strict)
        mode_box.add_widget(btn_libre)
        box.add_widget(mode_box)

        btn_calc = Button(text="CALCULER LES SOLUTIONS", size_hint=(1,None), height=dp(45), background_color=(0.1,0.7,0.5,1))
        box.add_widget(btn_calc)
        pop = Popup(title="Recherche par figure", content=box, size_hint=(0.97,0.95))
        self.register_solution_popup(pop)
        def on_calculer(_):
            fig_code = selected_figure[0]
            if fig_code is None:
                self.message("Attention", "Choisis une figure d'abord.")
                return
            positions = sorted([i for i, tb in maison_buttons.items() if tb.state == "down"])
            if not positions:
                self.message("Attention", "Choisis au moins une maison.")
                return
            stricte = btn_strict.state == "down"
            pop.dismiss()
            fig_name = FIGURES[fig_code]["africain"]
            mode_txt = " [S]" if stricte else " [NS]"
            title = fig_name + " M" + "+M".join(str(p) for p in positions) + mode_txt
            self.open_search_by_figure_window(title, fig_code, positions, stricte)
        btn_calc.bind(on_release=on_calculer)
        pop.open()

    def open_search_by_figure_window(self, title, fig_code, positions, stricte=False):
        from kivy.uix.togglebutton import ToggleButton as TBx
        import os
        _app_dir = os.path.dirname(os.path.abspath(__file__))
        import os as _os
        SAVED_FILE = _get_saved_file()
        content = BoxLayout(orientation="vertical", padding=dp(4), spacing=dp(4))
        header = Label(text=f"{title}\nCalcul en cours...", color=(1,1,1,1), size_hint=(1,None), height=dp(55))
        content.add_widget(header)
        # Onglets
        tab_box = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(38), spacing=dp(4))
        tab_sol = TBx(text="SOLUTIONS", group="v12tabs_fig", state="down", size_hint=(0.5,1))
        tab_saved = TBx(text="COMBINAISONS", group="v12tabs_fig", size_hint=(0.5,1))
        tab_box.add_widget(tab_sol); tab_box.add_widget(tab_saved)
        content.add_widget(tab_box)
        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(3), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        sv.add_widget(grid)
        sv_saved = ScrollView()
        grid_saved = GridLayout(cols=1, spacing=dp(3), size_hint_y=None)
        grid_saved.bind(minimum_height=grid_saved.setter("height"))
        sv_saved.add_widget(grid_saved)
        zone = BoxLayout(size_hint=(1,1))
        zone.add_widget(sv)
        content.add_widget(zone)
        btn_box = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(42), spacing=dp(4))
        close = Button(text="FERMER", size_hint=(0.5,1))
        btn_save = Button(text="💾 ENREGISTRER", size_hint=(0.5,1), background_color=(0.1,0.5,0.3,1))
        btn_box.add_widget(close); btn_box.add_widget(btn_save)
        content.add_widget(btn_box)
        pop = Popup(title=title, content=content, size_hint=(0.98,0.95))
        self.register_solution_popup(pop)
        close.bind(on_release=lambda x: pop.dismiss())
        solutions_ref = []
        current_sol_ref = [None]
        def refresh_saved():
            grid_saved.clear_widgets()
            saved = read_json(SAVED_FILE, [])
            if not saved:
                grid_saved.add_widget(Label(text="Aucune combinaison.", color=(0.7,0.7,0.7,1), size_hint_y=None, height=dp(50)))
                return
            for idx, item in enumerate(saved, 1):
                fig_n = item.get("figure_nom","?")
                pos_str = item.get("positions_str","")
                m1,m2,m3,m4 = item.get("m1","?"),item.get("m2","?"),item.get("m3","?"),item.get("m4","?")
                mode = item.get("mode","")
                txt = f"{idx}. {fig_n} {pos_str} [{mode}]\n    M1={m1} M2={m2} M3={m3} M4={m4}"
                row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(54), spacing=dp(3))
                b = Button(text=txt, font_size=dp(9.5), size_hint=(0.75,1), halign="left")
                b_del = Button(text="✕", size_hint=(0.12,1), background_color=(0.7,0.1,0.1,1))
                b_app = Button(text="▶", size_hint=(0.13,1), background_color=(0.1,0.4,0.7,1))
                def on_app(btn, it=item):
                    pop.dismiss()
                    sol = {"m1":it["m1"],"m2":it["m2"],"m3":it["m3"],"m4":it["m4"],"figure":it.get("figure_bits","1111"),"positions":[],"secondary":""}
                    self.apply_solution(sol)
                def on_del(btn, it=item):
                    sv2 = read_json(SAVED_FILE, [])
                    sv2 = [x for x in sv2 if x != it]
                    write_json(SAVED_FILE, sv2)
                    refresh_saved()
                b.bind(on_release=on_app); b_app.bind(on_release=on_app); b_del.bind(on_release=on_del)
                row.add_widget(b); row.add_widget(b_app); row.add_widget(b_del)
                grid_saved.add_widget(row)
        def switch_tab(btn):
            zone.clear_widgets()
            if tab_sol.state == "down":
                zone.add_widget(sv)
            else:
                zone.add_widget(sv_saved)
                refresh_saved()
        tab_sol.bind(on_press=switch_tab)
        tab_saved.bind(on_press=switch_tab)
        def on_save(_):
            sol = current_sol_ref[0] or (solutions_ref[0] if solutions_ref else None)
            if sol is None: return
            saved = read_json(SAVED_FILE, [])
            fig_bits = code_vers_bin(fig_code)
            fig_nom = FIGURES[fig_code]["africain"]
            all_p = sol.get("all_positions", list(positions))
            pos_str = "M"+"M".join(str(p) for p in all_p)
            mode = "S" if stricte else "NS"
            entry = {"figure_nom":fig_nom,"figure_bits":fig_bits,"positions_str":pos_str,"mode":mode,"m1":sol["m1"],"m2":sol["m2"],"m3":sol["m3"],"m4":sol["m4"]}
            if entry not in saved:
                saved.append(entry)
                write_json(SAVED_FILE, saved)
            self.message("Enregistré", f"{fig_nom} {pos_str} [{mode}]\nM1={sol['m1']} M2={sol['m2']} M3={sol['m3']} M4={sol['m4']}")
        btn_save.bind(on_release=on_save)
        pop.open()
        def fill(dt):
            try:
                solutions = []
                seen = set()
                fig_bits = code_vers_bin(fig_code)
                for m1 in TOUTES_LES_FIGURES:
                    for m2 in TOUTES_LES_FIGURES:
                        for m3 in TOUTES_LES_FIGURES:
                            for m4 in TOUTES_LES_FIGURES:
                                theme = developper_theme(m1, m2, m3, m4)
                                if not all(theme[p] == fig_bits for p in positions):
                                    continue
                                all_pos = [i for i in range(1, 17) if theme[i] == fig_bits]
                                if stricte and all_pos != list(positions):
                                    continue
                                key = (m1, m2, m3, m4)
                                if key in seen: continue
                                seen.add(key)
                                solutions.append({"m1":m1,"m2":m2,"m3":m3,"m4":m4,"positions":list(positions),"figure":fig_bits,"secondary":"","all_positions":all_pos})
                solutions_ref.clear(); solutions_ref.extend(solutions)
                mode_lbl = "STRICTE" if stricte else "NON STRICTE"
                header.text = f"{title}\n{len(solutions)} solution(s) — {mode_lbl}"
                fig_name = FIGURES[fig_code]["africain"]
                for idx, sol in enumerate(solutions, 1):
                    all_p = sol["all_positions"]
                    pos_ch = set(positions)
                    pos_sup = [p for p in all_p if p not in pos_ch]
                    pos_ch_str = "M"+"M".join(str(p) for p in positions)
                    if stricte:
                        pos_txt = pos_ch_str
                        bg = (0.15,0.15,0.15,1)
                    else:
                        if pos_sup:
                            pos_sup_str = "M"+"M".join(str(p) for p in pos_sup)
                            pos_txt = pos_ch_str + " [+aussi: " + pos_sup_str + "]"
                            bg = (0.1,0.35,0.55,1)
                        else:
                            pos_txt = pos_ch_str + " [exacte]"
                            bg = (0.15,0.15,0.15,1)
                    txt = f"{idx}. {fig_name} en {pos_txt}\n    M1={sol['m1']} M2={sol['m2']} M3={sol['m3']} M4={sol['m4']}"
                    b = Button(text=txt, font_size=dp(10), size_hint_y=None, height=dp(56), halign="left", background_color=bg)
                    row2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(58), spacing=dp(3))
                    def on_sol_click(btn, s=sol, sl=solutions):
                        current_sol_ref[0] = s
                        # Auto-save si non stricte
                        if not stricte:
                            import os as _os
                            SF = _get_saved_file()
                            sv = read_json(SF, [])
                            fig_bits2 = code_vers_bin(fig_code)
                            fig_nom2 = FIGURES[fig_code]["africain"]
                            all_p2 = s.get("all_positions", list(positions))
                            ps2 = "M"+"M".join(str(p) for p in all_p2)
                            entry2 = {"figure_nom":fig_nom2,"figure_bits":fig_bits2,
                                     "positions_str":ps2,"mode":"NS",
                                     "m1":s["m1"],"m2":s["m2"],"m3":s["m3"],"m4":s["m4"]}
                            if entry2 not in sv:
                                sv.append(entry2)
                                write_json(SF, sv)
                        self.close_all_solution_popups()
                        self.apply_solution_from_list(s, sl, None)
                    b.bind(on_release=on_sol_click)
                    row2.add_widget(b)
                    grid.add_widget(row2)
                if not solutions:
                    grid.add_widget(Label(text="Aucune solution trouvée.", color=(1,0.4,0.4,1), size_hint_y=None, height=dp(60)))
            except Exception as e:
                header.text = "Erreur"
                grid.add_widget(Label(text=str(e), color=(1,1,1,1), size_hint_y=None, height=dp(80)))
        Clock.schedule_once(fill, 0.2)

    def popup_table(self):
        txt = "Éléments :\nFeu rouge : 1121, 1222, 1122, 1212\nVent gris : 2111, 2122, 2112, 2121\nEau bleu : 1111, 2222, 1112, 2212\nTerre vert : 2211, 1221, 1211, 2221\n\n"
        for code, d in FIGURES.items():
            bits = code_vers_bin(code)
            txt += f"{d['africain']} / {d['occidental']} : {code} | {element_of_bits(bits)}\n{d['sens']}\n\n"
        self.message("Table des 16 figures", txt)

    def message(self, titre_txt, message):
        content = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))
        sv = ScrollView()
        lab = Label(text=message, color=(1,1,1,1), size_hint_y=None, halign="left", valign="top")
        lab.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        lab.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        sv.add_widget(lab); content.add_widget(sv)
        btn = Button(text="OK", size_hint=(1,None), height=dp(45)); content.add_widget(btn)
        pop = Popup(title=titre_txt, content=content, size_hint=(0.9,0.7))
        btn.bind(on_release=lambda x: pop.dismiss()); pop.open()

class MoneyApp(App):
    def build(self):
        self.title = "GEOSTAR"

        from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
        from kivy.uix.floatlayout import FloatLayout as _FL2
        from kivy.uix.boxlayout import BoxLayout as _BL2
        from kivy.uix.label import Label as _Lbl2
        from kivy.uix.button import Button as _Btn2
        from kivy.metrics import dp as _dp2
        from kivy.graphics import Color as _Clr2, Rectangle as _Rct2, RoundedRectangle as _RR2
        import webbrowser as _wb

        # Créer l'écran d'accueil
        sm = ScreenManager(transition=FadeTransition(duration=0.3))

        # ── ÉCRAN D'ACCUEIL ──────────────────────────────────────
        welcome = Screen(name="welcome")
        wbox = _FL2()

        with wbox.canvas.before:
            _Clr2(0.02, 0.72, 0.70, 1)
            wbox._bg = _Rct2(pos=wbox.pos, size=wbox.size)
        wbox.bind(size=lambda s,v: setattr(s._bg,"size",v))
        wbox.bind(pos=lambda s,v: setattr(s._bg,"pos",v))

        content = _BL2(
            orientation="vertical",
            spacing=_dp2(18),
            padding=[_dp2(30), _dp2(40)],
            size_hint=(0.88, None),
            height=_dp2(520),
            pos_hint={"center_x": 0.5, "center_y": 0.52}
        )

        # Titre GEOSTAR
        content.add_widget(_Lbl2(
            text="[b]GEOSTAR[/b]",
            markup=True,
            font_size=_dp2(42),
            color=(1, 1, 1, 1),
            size_hint=(1, None),
            height=_dp2(65),
            halign="center"
        ))

        # Sous-titre
        content.add_widget(_Lbl2(
            text="Application de Géomancie",
            font_size=_dp2(16),
            color=(0.9, 1.0, 0.98, 0.85),
            size_hint=(1, None),
            height=_dp2(30),
            halign="center"
        ))

        # Séparateur visuel
        sep = _BL2(size_hint=(0.6, None), height=_dp2(2))
        sep.pos_hint = {"center_x": 0.5}
        with sep.canvas:
            _Clr2(1, 1, 1, 0.3)
            _Rct2(pos=sep.pos, size=sep.size)
        content.add_widget(sep)

        # Description
        desc = _Lbl2(
            text="Tracez et analysez vos themes geomantiques avec precision et profondeur.",
            font_size=_dp2(14),
            color=(0.9, 1.0, 0.98, 0.85),
            size_hint=(1, None),
            height=_dp2(55),
            halign="center"
        )
        desc.bind(width=lambda s,w: setattr(s,"text_size",(w,None)))
        content.add_widget(desc)

        # Bouton ACCÉDER
        btn_enter = _Btn2(
            text="ACCÉDER À L'APPLICATION",
            size_hint=(1, None),
            height=_dp2(62),
            bold=True,
            font_size=_dp2(16),
            background_color=(0.0, 0.0, 0.0, 0.0)
        )
        with btn_enter.canvas.before:
            _Clr2(1, 1, 1, 0.95)
            btn_enter._bg = _RR2(pos=btn_enter.pos, size=btn_enter.size, radius=[_dp2(10)])
        btn_enter.bind(size=lambda s,v: setattr(s._bg,"size",v))
        btn_enter.bind(pos=lambda s,v: setattr(s._bg,"pos",v))
        btn_enter.color = (0.02, 0.55, 0.53, 1)

        def go_app(_):
            """Vérifie la licence. Si valide -> app. Sinon -> écran activation."""
            import os as _os2, json as _js2, re as _re2
            from datetime import datetime as _dt2
            from kivy.core.window import Window as _Win2
            from kivy.uix.floatlayout import FloatLayout as _FL3
            from kivy.uix.boxlayout import BoxLayout as _BL3
            from kivy.uix.label import Label as _Lbl3
            from kivy.uix.button import Button as _Btn3
            from kivy.metrics import dp as _dp3
            from kivy.graphics import Color as _Clr3, Rectangle as _Rct3

            # Chemin licence
            try:
                from kivy.utils import platform as _p3
                if _p3 == "android":
                    from android.storage import app_storage_path as _asp3
                    _base3 = _asp3()
                else:
                    _base3 = _os2.path.expanduser("~")
            except:
                _base3 = _os2.path.expanduser("~")
            _lic3 = _os2.path.join(_base3, ".geostar_licence.json")

            # Lire licence locale
            _local3 = None
            try:
                with open(_lic3, "r", encoding="utf-8") as _f3:
                    _local3 = _js2.load(_f3)
            except:
                pass

            _CODE_RE3 = _re2.compile(r"^GEO-[A-Z0-9]{4}$")
            _autorise3 = False
            _is_blocked3 = False

            if _local3:
                _code3 = _local3.get("code", "")
                _derniere3 = _local3.get("derniere_verif", "")
                _statut3 = _local3.get("statut", "actif")

                if _statut3 == "bloque":
                    _is_blocked3 = True
                elif _CODE_RE3.match(_code3) and _derniere3:
                    # Vérifier en ligne
                    try:
                        import ssl as _ssl3, urllib.request as _ur3
                        _ctx3 = _ssl3.SSLContext(_ssl3.PROTOCOL_TLS_CLIENT)
                        _ctx3.check_hostname = False
                        _ctx3.verify_mode = _ssl3.CERT_NONE
                        _req3 = _ur3.Request(
                            "https://raw.githubusercontent.com/Moneymyck/geostar-android/main/codes_geostar.json",
                            headers={"User-Agent": "GEOSTAR/12.26"}
                        )
                        with _ur3.urlopen(_req3, timeout=6, context=_ctx3) as _rsp3:
                            _rem3 = _js2.loads(_rsp3.read().decode("utf-8"))
                        _blqs3 = _rem3.get("codes_bloques", [])
                        _vals3 = _rem3.get("codes_valides", {})
                        if _code3 in _blqs3:
                            _is_blocked3 = True
                            try:
                                _local3["statut"] = "bloque"
                                with open(_lic3, "w") as _fw3:
                                    _js2.dump(_local3, _fw3)
                            except: pass
                        elif _code3 in _vals3:
                            _autorise3 = True
                            _local3["derniere_verif"] = _dt2.now().strftime("%Y-%m-%d")
                            _local3["statut"] = "actif"
                            try:
                                with open(_lic3, "w") as _fw3:
                                    _js2.dump(_local3, _fw3)
                            except: pass
                    except:
                        # Pas internet: grace 30j
                        try:
                            _d3 = _dt2.strptime(_derniere3, "%Y-%m-%d")
                            if (_dt2.now() - _d3).days <= 30:
                                _autorise3 = True
                        except: pass

            if _autorise3:
                sm.current = "app"
                return

            # PAS AUTORISÉ -> Afficher overlay d'activation sur l'écran d'accueil
            # Vérifier qu'un overlay n'est pas déjà ouvert
            for _w3 in list(_Win2.children):
                if getattr(_w3, "_geostar_activ", False):
                    return

            # Créer overlay d'activation
            class _ActOv(_FL3):
                def on_touch_down(self, t):
                    super().on_touch_down(t)
                    return True
                def on_touch_move(self, t):
                    super().on_touch_move(t)
                    return True
                def on_touch_up(self, t):
                    super().on_touch_up(t)
                    return True

            _ov3 = _ActOv(size=_Win2.size)
            _ov3._geostar_activ = True
            with _ov3.canvas.before:
                _Clr3(0.05, 0.05, 0.08, 0.97)
                _ov3._bg3 = _Rct3(pos=_ov3.pos, size=_ov3.size)
            _ov3.bind(size=lambda s,v: setattr(s._bg3,"size",v))
            _ov3.bind(pos=lambda s,v: setattr(s._bg3,"pos",v))

            _bx3 = _BL3(
                orientation="vertical", padding=_dp3(30), spacing=_dp3(14),
                size_hint=(0.88, None), height=_dp3(430),
                pos_hint={"center_x":0.5,"center_y":0.5}
            )

            _bx3.add_widget(_Lbl3(
                text="[b]GEOSTAR[/b]", markup=True,
                color=(1,0.85,0.1,1), font_size=_dp3(34),
                size_hint=(1,None), height=_dp3(50), halign="center"
            ))

            if _is_blocked3:
                _msg3 = "Votre acces a ete suspendu.\nContactez l'administrateur."
                _msg_clr3 = (1, 0.3, 0.3, 1)
            else:
                _msg3 = "Entrez votre code d'activation"
                _msg_clr3 = (0.8, 0.8, 0.8, 1)

            _bx3.add_widget(_Lbl3(
                text=_msg3, color=_msg_clr3, font_size=_dp3(15),
                size_hint=(1,None), height=_dp3(50), halign="center"
            ))
            _bx3.add_widget(_Lbl3(
                text="Format : GEO-XXXX", color=(0.6,0.6,0.6,1),
                font_size=_dp3(13), size_hint=(1,None), height=_dp3(28),
                halign="center"
            ))

            _inp3 = None
            _btn3 = None

            if not _is_blocked3:
                _inp3 = _BL3.__mro__[0].__new__(_BL3.__mro__[0])
                from kivy.uix.textinput import TextInput as _TI3
                _inp3 = _TI3(
                    hint_text="GEO-XXXX", multiline=False,
                    size_hint=(1,None), height=_dp3(55),
                    font_size=_dp3(22), halign="center",
                    background_color=(0.15,0.17,0.22,1),
                    foreground_color=(1,1,1,1)
                )
                _bx3.add_widget(_inp3)

            _st3 = _Lbl3(
                text="", color=(1,0.3,0.3,1), font_size=_dp3(13),
                size_hint=(1,None), height=_dp3(38), halign="center"
            )
            _st3.bind(width=lambda s,w: setattr(s,"text_size",(w,None)))
            _bx3.add_widget(_st3)

            if not _is_blocked3:
                _btn3 = _Btn3(
                    text="ACTIVER", size_hint=(1,None), height=_dp3(58),
                    background_color=(0.1,0.6,0.3,1), bold=True, font_size=_dp3(18)
                )
                _bx3.add_widget(_btn3)

            _bq3 = _Btn3(
                text="Retour", size_hint=(1,None), height=_dp3(42),
                background_color=(0.25,0.25,0.25,1), font_size=_dp3(14)
            )
            _bx3.add_widget(_bq3)
            _ov3.add_widget(_bx3)
            _Win2.add_widget(_ov3)

            def _activer3(_b):
                if not _inp3: return
                _c3 = _inp3.text.strip().upper()
                if not _c3:
                    _st3.text = "Entrez votre code"
                    return
                if not _c3.startswith("GEO-") and len(_c3)==4:
                    _c3 = "GEO-" + _c3
                if not _CODE_RE3.match(_c3):
                    _st3.text = "Format invalide (ex: GEO-A7K9)"
                    return
                _st3.text = "Verification..."
                _st3.color = (1,1,0.3,1)
                try:
                    import ssl as _s4, urllib.request as _u4
                    _c4 = _s4.SSLContext(_s4.PROTOCOL_TLS_CLIENT)
                    _c4.check_hostname = False
                    _c4.verify_mode = _s4.CERT_NONE
                    _r4 = _u4.Request(
                        "https://raw.githubusercontent.com/Moneymyck/geostar-android/main/codes_geostar.json",
                        headers={"User-Agent":"GEOSTAR/12.26"}
                    )
                    with _u4.urlopen(_r4, timeout=8, context=_c4) as _rsp4:
                        _rem4 = _js2.loads(_rsp4.read().decode("utf-8"))
                    _vals4 = _rem4.get("codes_valides", {})
                    _blqs4 = _rem4.get("codes_bloques", [])
                    if _c3 in _blqs4:
                        _st3.text = "Code bloque"
                        _st3.color = (1,0.3,0.3,1)
                    elif _c3 in _vals4:
                        try:
                            with open(_lic3,"w",encoding="utf-8") as _fw4:
                                _js2.dump({
                                    "code":_c3,
                                    "expire":_vals4[_c3].get("expire",""),
                                    "derniere_verif":_dt2.now().strftime("%Y-%m-%d"),
                                    "statut":"actif"
                                }, _fw4)
                        except: pass
                        _Win2.remove_widget(_ov3)
                        sm.current = "app"
                    else:
                        _st3.text = "Code inconnu. Verifiez votre code."
                        _st3.color = (1,0.3,0.3,1)
                except Exception as _e4:
                    if _CODE_RE3.match(_c3):
                        try:
                            with open(_lic3,"w",encoding="utf-8") as _fw4:
                                _js2.dump({
                                    "code":_c3,"expire":"",
                                    "derniere_verif":"","statut":"pending"
                                }, _fw4)
                        except: pass
                        _st3.text = "Pas de connexion. Code enregistre."
                        _st3.color = (0.3,1,0.3,1)
                    else:
                        _st3.text = "Erreur connexion"
                        _st3.color = (1,0.5,0.1,1)

            def _retour3(_b):
                _Win2.remove_widget(_ov3)

            if _btn3:
                _btn3.bind(on_release=_activer3)
            _bq3.bind(on_release=_retour3)

        btn_enter.bind(on_release=go_app)
        content.add_widget(btn_enter)

        # Séparateur
        content.add_widget(_Lbl2(
            text="──────────────────────────",
            color=(1,1,1,0.2),
            size_hint=(1,None), height=_dp2(20),
            halign="center", font_size=_dp2(12)
        ))

        # Section contact
        content.add_widget(_Lbl2(
            text="Pour obtenir un code d'activation :",
            font_size=_dp2(13),
            color=(1, 1, 1, 0.9),
            size_hint=(1, None),
            height=_dp2(28),
            halign="center"
        ))

        # Bouton Email
        btn_email = _Btn2(
            text="  anthom1253@gmail.com",
            size_hint=(1, None),
            height=_dp2(52),
            font_size=_dp2(14),
            background_color=(0.0, 0.0, 0.0, 0.0)
        )
        with btn_email.canvas.before:
            _Clr2(0.0, 0.45, 0.43, 1)
            btn_email._bg = _RR2(pos=btn_email.pos, size=btn_email.size, radius=[_dp2(8)])
        btn_email.bind(size=lambda s,v: setattr(s._bg,"size",v))
        btn_email.bind(pos=lambda s,v: setattr(s._bg,"pos",v))
        btn_email.color = (1, 1, 1, 1)

        def open_email(_):
            try:
                _wb.open("mailto:anthom1253@gmail.com?subject=Code activation GEOSTAR")
            except Exception:
                pass
        btn_email.bind(on_release=open_email)
        content.add_widget(btn_email)

        # Copyright
        content.add_widget(_Lbl2(
            text="GEOSTAR © 2026",
            font_size=_dp2(11),
            color=(1,1,1,0.5),
            size_hint=(1,None), height=_dp2(24),
            halign="center"
        ))

        wbox.add_widget(content)
        welcome.add_widget(wbox)
        sm.add_widget(welcome)

        # ── ÉCRAN APPLICATION ────────────────────────────────────
        app_screen = Screen(name="app")
        root = MoneyRoot()
        app_screen.add_widget(root)
        sm.add_widget(app_screen)

        sm.current = "welcome"

        def _verif_licence(dt, r=root):
            import os as _os, json as _js, re as _re
            from datetime import datetime as _dt
            from kivy.core.window import Window as _Win
            from kivy.uix.floatlayout import FloatLayout as _FL
            from kivy.uix.boxlayout import BoxLayout as _BL
            from kivy.uix.label import Label as _Lbl
            from kivy.uix.button import Button as _Btn
            from kivy.uix.textinput import TextInput as _TI
            from kivy.metrics import dp as _dp
            from kivy.graphics import Color as _Clr, Rectangle as _Rct

            # Chemin du fichier licence
            try:
                from kivy.utils import platform as _plat
                if _plat == "android":
                    from android.storage import app_storage_path as _asp
                    _base = _asp()
                else:
                    _base = _os.path.expanduser("~")
            except Exception:
                _base = _os.path.expanduser("~")
            _lic_path = _os.path.join(_base, ".geostar_licence.json")

            # Lire le fichier licence local
            _local = None
            try:
                with open(_lic_path, "r", encoding="utf-8") as _f:
                    _local = _js.load(_f)
            except Exception:
                pass

            # Vérifier si activation nécessaire
            _need_activation = True
            _is_blocked = False  # Initialisation obligatoire
            _CODE_RE = _re.compile(r"^GEO-[A-Z0-9]{4}$")

            if _local:
                _code = _local.get("code", "")
                _derniere = _local.get("derniere_verif", "")
                if _CODE_RE.match(_code):
                    # Toujours tenter vérification en ligne d'abord
                    _online_ok = False
                    _is_blocked = False
                    try:
                        import ssl as _ssl, urllib.request as _ur
                        _ctx = _ssl.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
                        _ctx.check_hostname = False
                        _ctx.verify_mode = _ssl.CERT_NONE
                        _req = _ur.Request(
                            "https://raw.githubusercontent.com/Moneymyck/geostar-android/main/codes_geostar.json",
                            headers={"User-Agent": "GEOSTAR/12.26"}
                        )
                        with _ur.urlopen(_req, timeout=8, context=_ctx) as _resp:
                            _remote = _js.loads(_resp.read().decode("utf-8"))
                        _valides = _remote.get("codes_valides", {})
                        _bloques = _remote.get("codes_bloques", [])
                        _online_ok = True
                        if _code in _bloques:
                            # BLOQUÉ -> marquer mais garder le fichier
                            # (si débloqué plus tard, pas besoin de réentrer le code)
                            _is_blocked = True
                            _need_activation = True
                            try:
                                _local["statut"] = "bloque"
                                with open(_lic_path, "w") as _f:
                                    _js.dump(_local, _f)
                            except: pass
                        elif _code in _valides:
                            # Vérifier expiration
                            _exp = _valides[_code].get("expire", "")
                            _expire_ok = True
                            if _exp:
                                try:
                                    if _dt.now() > _dt.strptime(_exp, "%Y-%m-%d"):
                                        _expire_ok = False
                                except: pass
                            if _expire_ok:
                                _need_activation = False
                                _local["derniere_verif"] = _dt.now().strftime("%Y-%m-%d")
                                _local["statut"] = "actif"  # Réinitialiser si débloqué
                                try:
                                    with open(_lic_path, "w") as _f:
                                        _js.dump(_local, _f)
                                except: pass
                            else:
                                _need_activation = True
                                try: _os.remove(_lic_path)
                                except: pass
                        else:
                            # Code inconnu sur GitHub -> demander nouveau code
                            _need_activation = True
                    except Exception:
                        # Pas internet -> grâce 30 jours SEULEMENT si déjà vérifié en ligne
                        if _derniere and not _is_blocked:
                            try:
                                _d = _dt.strptime(_derniere, "%Y-%m-%d")
                                if (_dt.now() - _d).days <= 30:
                                    _need_activation = False
                            except: pass
                        # Si jamais vérifié en ligne -> toujours demander activation
                        elif not _derniere:
                            _need_activation = True

            if not _need_activation:
                return  # App autorisée

            # Déjà un overlay ouvert ?
            for _w in list(_Win.children):
                if getattr(_w, "_geostar_activ", False):
                    return

            # Si bloqué : afficher message spécial
            _blocked_msg = "Code bloqué par l'administrateur." if _is_blocked else ""

            # Créer l'overlay d'activation (bloque TOUTES les touches)
            from kivy.uix.floatlayout import FloatLayout as _FLBase

            class _ActivationOverlay(_FLBase):
                """Overlay qui bloque toutes les touches en dessous."""
                def on_touch_down(self, touch):
                    super().on_touch_down(touch)
                    return True  # Bloque tout
                def on_touch_move(self, touch):
                    super().on_touch_move(touch)
                    return True  # Bloque tout
                def on_touch_up(self, touch):
                    super().on_touch_up(touch)
                    return True  # Bloque tout

            _ov = _ActivationOverlay(size=_Win.size)
            _ov._geostar_activ = True
            with _ov.canvas.before:
                _Clr(0.05, 0.05, 0.08, 1)
                _ov._bg = _Rct(pos=_ov.pos, size=_ov.size)
            _ov.bind(size=lambda s,v: setattr(s._bg,"size",v))
            _ov.bind(pos=lambda s,v: setattr(s._bg,"pos",v))

            _box = _BL(orientation="vertical", padding=_dp(30),
                       spacing=_dp(12), size_hint=(0.88,None), height=_dp(420),
                       pos_hint={"center_x":0.5,"center_y":0.5})

            _box.add_widget(_Lbl(text="[b]GEOSTAR[/b]", markup=True,
                color=(1,0.85,0.1,1), font_size=_dp(34),
                size_hint=(1,None), height=_dp(55), halign="center"))

            _box.add_widget(_Lbl(text="Code d'activation requis",
                color=(0.8,0.8,0.8,1), font_size=_dp(16),
                size_hint=(1,None), height=_dp(35), halign="center"))

            _box.add_widget(_Lbl(text="Format : GEO-XXXX",
                color=(0.6,0.6,0.6,1), font_size=_dp(13),
                size_hint=(1,None), height=_dp(28), halign="center"))

            _inp = _TI(hint_text="GEO-XXXX", multiline=False,
                size_hint=(1,None), height=_dp(58), font_size=_dp(24),
                halign="center", background_color=(0.15,0.17,0.22,1),
                foreground_color=(1,1,1,1))
            _box.add_widget(_inp)

            _st = _Lbl(text="", color=(1,0.3,0.3,1), font_size=_dp(13),
                size_hint=(1,None), height=_dp(40), halign="center")
            _st.bind(width=lambda s,w: setattr(s,"text_size",(w,None)))
            _box.add_widget(_st)

            _btn = _Btn(text="ACTIVER", size_hint=(1,None), height=_dp(62),
                background_color=(0.1,0.6,0.3,1), bold=True, font_size=_dp(20))
            _box.add_widget(_btn)

            _bq = _Btn(text="Quitter", size_hint=(1,None), height=_dp(42),
                background_color=(0.3,0.3,0.3,1), font_size=_dp(14))
            _box.add_widget(_bq)

            _ov.add_widget(_box)

            _Win.add_widget(_ov)

            def _activer(_b):
                _code = _inp.text.strip().upper()
                if not _code:
                    _st.text = "Entrez votre code"
                    return
                if not _code.startswith("GEO-") and len(_code)==4:
                    _code = "GEO-" + _code
                if not _CODE_RE.match(_code):
                    _st.text = "Format invalide (ex: GEO-A7K9)"
                    return
                _st.text = "Vérification..."
                _st.color = (1,1,0.3,1)
                try:
                    import ssl as _s2, urllib.request as _u2
                    _c2 = _s2.SSLContext(_s2.PROTOCOL_TLS_CLIENT)
                    _c2.check_hostname = False
                    _c2.verify_mode = _s2.CERT_NONE
                    _r2 = _u2.Request(
                        "https://raw.githubusercontent.com/Moneymyck/geostar-android/main/codes_geostar.json",
                        headers={"User-Agent":"GEOSTAR/12.26"}
                    )
                    with _u2.urlopen(_r2, timeout=8, context=_c2) as _rsp:
                        _rem = _js.loads(_rsp.read().decode("utf-8"))
                    _vals = _rem.get("codes_valides", {})
                    _blqs = _rem.get("codes_bloques", [])
                    # Debug : afficher les codes disponibles
                    _codes_list = ", ".join(list(_vals.keys())[:3])
                    if _code in _blqs:
                        _st.text = "Code bloqué"
                        _st.color = (1,0.3,0.3,1)
                    elif _code in _vals:
                        # Code valide -> sauvegarder et ouvrir l'app
                        _info = _vals[_code]
                        # Vérifier expiration
                        _exp = _info.get("expire","")
                        _expire_ok = True
                        if _exp:
                            try:
                                from datetime import datetime as _dtcheck
                                if _dtcheck.now() > _dtcheck.strptime(_exp, "%Y-%m-%d"):
                                    _expire_ok = False
                                    _st.text = f"Code expiré le {_exp}"
                                    _st.color = (1,0.3,0.3,1)
                            except: pass
                        if _expire_ok:
                            try:
                                with open(_lic_path,"w",encoding="utf-8") as _f:
                                    _js.dump({"code":_code,"expire":_exp,
                                        "derniere_verif":_dt.now().strftime("%Y-%m-%d"),
                                        "active_le":_dt.now().strftime("%Y-%m-%d")},_f)
                            except: pass
                            _Win.remove_widget(_ov)
                    else:
                        _st.text = f"Code '{_code}' non trouvé.\nCodes dispo: {_codes_list or 'aucun'}"
                        _st.color = (1,0.5,0.1,1)
                except Exception as _e:
                    # Pas de connexion : si le code a le bon format,
                    # on l'accepte temporairement (sera vérifié plus tard)
                    if _CODE_RE.match(_code):
                        try:
                            with open(_lic_path,"w",encoding="utf-8") as _f:
                                _js.dump({"code":_code,"expire":"",
                                    "derniere_verif":"",
                                    "active_le":_dt.now().strftime("%Y-%m-%d")},_f)
                        except: pass
                        _st.text = "Code enregistré. Sera vérifié en ligne au prochain démarrage."
                        _st.color = (0.3,1,0.3,1)
                        import threading as _th
                        def _remove_overlay(dt):
                            try: _Win.remove_widget(_ov)
                            except: pass
                        from kivy.clock import Clock as _Clk2
                        _Clk2.schedule_once(_remove_overlay, 1.5)
                    else:
                        _st.text = "Pas de connexion. Vérifiez votre réseau."
                        _st.color = (1,0.5,0.1,1)

            def _quitter(_b):
                App.get_running_app().stop()

            _btn.bind(on_release=_activer)
            _bq.bind(on_release=_quitter)

        # La vérification se fait uniquement via le bouton ACCÉDER
        # Plus besoin de Clock auto
        return sm


# ============================================================
# PATCH V10.1 - FIGURE VISUELLE + RECHERCHE PERSO + MICRO
# ============================================================

def _money_v101_patch():
    def figure_hasard_visuelle(self):
        code = random.choice(TOUTES_LES_FIGURES)
        bits = code_vers_bin(code)
        d = data_fig(bits)

        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        title = Label(
            text=f"[b]{d['africain']} / {d['occidental']}[/b]\nCode : {code} | Élément : {element_of_bits(bits)}",
            markup=True,
            color=(1,1,1,1),
            size_hint=(1, None),
            height=dp(70)
        )
        box.add_widget(title)

        zone = FloatLayout(size_hint=(1, 1))
        box.add_widget(zone)

        card = FigureCard(
            maison=0,
            bits=bits,
            root=None,
            repeated=True,
            size_hint=(0.42, 0.72),
            pos_hint={"center_x": 0.5, "center_y": 0.55}
        )
        zone.add_widget(card)

        sens = Label(
            text=d["sens"],
            color=(1,1,1,1),
            font_size=dp(15),
            size_hint=(1, None),
            height=dp(65),
            pos_hint={"x": 0, "y": 0.02}
        )
        zone.add_widget(sens)

        btn = Button(text="OK", size_hint=(1, None), height=dp(45))
        box.add_widget(btn)

        pop = Popup(title="Figure aléatoire", content=box, size_hint=(0.92, 0.82))
        btn.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    MoneyRoot.figure_hasard = figure_hasard_visuelle

    def search_strict_positions_fixed(positions, target_bits=None, rare=False):
        solutions = []
        seen = set()
        positions = [int(p) for p in positions]

        for m1 in TOUTES_LES_FIGURES:
            for m2 in TOUTES_LES_FIGURES:
                for m3 in TOUTES_LES_FIGURES:
                    for m4 in TOUTES_LES_FIGURES:
                        h2 = developper_theme(m1, m2, m3, m4)
                        vals = [h2[p] for p in positions]

                        if not all(v == vals[0] for v in vals):
                            continue

                        fig = vals[0]

                        if target_bits is not None and fig != target_bits:
                            continue

                        exact_pos = [i for i in range(1, 17) if h2[i] == fig]
                        if exact_pos != positions:
                            continue

                        secondary = ""
                        if rare:
                            if h2[7] == h2[13] and h2[7] != fig:
                                secondary = "7-13 " + data_fig(h2[7])["africain"]
                            elif h2[7] == h2[15] and h2[7] != fig:
                                secondary = "7-15 " + data_fig(h2[7])["africain"]
                            else:
                                continue

                        key = (m1, m2, m3, m4, tuple(positions), fig, secondary)
                        if key in seen:
                            continue
                        seen.add(key)

                        solutions.append({
                            "m1": m1,
                            "m2": m2,
                            "m3": m3,
                            "m4": m4,
                            "positions": positions[:],
                            "figure": fig,
                            "secondary": secondary,
                        })

        return solutions

    globals()["search_strict_positions"] = search_strict_positions_fixed

    def get_solutions_cached_fixed(self, positions, rare=False):
        positions = [int(p) for p in positions]
        key = self.cache_key(positions, rare)

        if key in self.solution_cache:
            return self.solution_cache[key]

        self.info.text = "Calcul des 65 536 combinaisons en cours..."
        sols = search_strict_positions_fixed(positions, None, rare)
        self.solution_cache[key] = sols
        write_json(CACHE_FILE, self.solution_cache)
        return sols

    MoneyRoot.get_solutions_cached = get_solutions_cached_fixed

    def open_micro_fixed(self):
        if platform == "android":
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")

                intent = Intent("android.provider.MediaStore.RECORD_SOUND")
                PythonActivity.mActivity.startActivity(intent)

                self.message(
                    "Micro",
                    "Le micro Android a été ouvert. Après l'enregistrement, reviens dans GEOSTAR et écris le nom du fichier vocal dans la note."
                )
                return
            except Exception:
                pass

            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")

                intent = Intent(Intent.ACTION_MAIN)
                intent.addCategory(Intent.CATEGORY_APP_MUSIC)
                PythonActivity.mActivity.startActivity(intent)

                self.message(
                    "Micro",
                    "J'ai ouvert les applications audio disponibles. Utilise l'enregistreur vocal puis note le nom du fichier dans GEOSTAR."
                )
                return
            except Exception as e:
                self.message(
                    "Micro",
                    "Pydroid bloque l'accès direct au micro sur cette tablette. Solution fiable : utilise l'application Enregistreur vocal du téléphone, puis écris le nom du fichier dans la note.\n\nErreur technique : " + str(e)
                )
                return

        self.message(
            "Micro",
            "Sur iPhone ou Web, l'enregistrement vocal direct demande une version web spéciale ou une app native. Pour l'instant, utilise Dictaphone puis écris le nom du fichier dans la note."
        )

    MoneyRoot.open_micro = open_micro_fixed

_money_v101_patch()



# ============================================================
# PATCH V10.3 - RECHERCHE STRICTE PERSONNALISEE + REPETITIONS
# ============================================================

def _money_v103_patch():

    def search_custom_strict_positions(positions, target_bits=None, rare=False):
        """
        Recherche personnalisée stricte :
        Exemple positions = [8,2,13]
        GEOSTAR cherche tous les thèmes où une même figure apparaît
        exactement en M8, M2 et M13, et pas ailleurs.

        Les autres figures ont le droit de se répéter ailleurs.
        """
        solutions = []
        seen = set()
        positions = [int(p) for p in positions]

        for m1 in TOUTES_LES_FIGURES:
            for m2 in TOUTES_LES_FIGURES:
                for m3 in TOUTES_LES_FIGURES:
                    for m4 in TOUTES_LES_FIGURES:
                        h2 = developper_theme(m1, m2, m3, m4)
                        vals = [h2[p] for p in positions]

                        if not all(v == vals[0] for v in vals):
                            continue

                        fig = vals[0]

                        if target_bits is not None and fig != target_bits:
                            continue

                        # La figure ciblée ne doit apparaître QUE dans les maisons choisies.
                        exact_pos = [i for i in range(1, 17) if h2[i] == fig]
                        if exact_pos != positions:
                            continue

                        secondary = ""
                        if rare:
                            if h2[7] == h2[13] and h2[7] != fig:
                                secondary = "7-13 " + data_fig(h2[7])["africain"]
                            elif h2[7] == h2[15] and h2[7] != fig:
                                secondary = "7-15 " + data_fig(h2[7])["africain"]
                            else:
                                continue

                        key = (m1, m2, m3, m4, tuple(positions), fig, secondary)
                        if key in seen:
                            continue
                        seen.add(key)

                        solutions.append({
                            "m1": m1,
                            "m2": m2,
                            "m3": m3,
                            "m4": m4,
                            "positions": positions[:],
                            "figure": fig,
                            "secondary": secondary,
                            "all_positions": exact_pos,
                        })

        return solutions

    def search_by_repetition_count(count, target_bits=None):
        """
        Cherche toutes les combinaisons où une figure apparaît exactement N fois.
        Exemple count=3 : toutes les solutions où une figure apparaît exactement 3 fois.
        """
        count = int(count)
        solutions = []
        seen = set()

        for m1 in TOUTES_LES_FIGURES:
            for m2 in TOUTES_LES_FIGURES:
                for m3 in TOUTES_LES_FIGURES:
                    for m4 in TOUTES_LES_FIGURES:
                        h2 = developper_theme(m1, m2, m3, m4)

                        rep = {}
                        for i in range(1, 17):
                            rep.setdefault(h2[i], []).append(i)

                        for fig, pos in rep.items():
                            if len(pos) != count:
                                continue
                            if target_bits is not None and fig != target_bits:
                                continue

                            key = (m1, m2, m3, m4, fig, tuple(pos))
                            if key in seen:
                                continue
                            seen.add(key)

                            solutions.append({
                                "m1": m1,
                                "m2": m2,
                                "m3": m3,
                                "m4": m4,
                                "positions": pos[:],
                                "figure": fig,
                                "secondary": "",
                                "all_positions": pos[:],
                            })

        return solutions

    def cache_key_v103(self, positions, rare=False):
        return ("strict_rare_" if rare else "strict_custom_") + "_".join(map(str, positions))

    def get_solutions_cached_v103(self, positions, rare=False):
        positions = [int(p) for p in positions]
        key = cache_key_v103(self, positions, rare)

        if key in self.solution_cache:
            return self.solution_cache[key]

        self.info.text = "Recherche stricte : calcul des 65 536 combinaisons..."
        sols = search_custom_strict_positions(positions, None, rare)
        self.solution_cache[key] = sols
        write_json(CACHE_FILE, self.solution_cache)
        return sols

    MoneyRoot.cache_key = cache_key_v103
    MoneyRoot.get_solutions_cached = get_solutions_cached_v103

    def open_solution_window_v103(self, title, positions, rare):
        content = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(6))
        header = Label(
            text=f"{title}\nRecherche stricte : la figure doit apparaître uniquement dans les maisons choisies.",
            color=(1,1,1,1),
            size_hint=(1,None),
            height=dp(75)
        )
        content.add_widget(header)

        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(3), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        sv.add_widget(grid)
        content.add_widget(sv)

        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        content.add_widget(close)

        pop = Popup(title=title, content=content, size_hint=(0.98,0.92))
        close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

        def fill(dt):
            try:
                sols = self.get_solutions_cached(positions, rare)
                header.text = f"{title}\nTotal : {len(sols)} solution(s)"
                if not sols:
                    grid.add_widget(Label(
                        text="Aucune solution stricte trouvée pour ces maisons.",
                        color=(1,1,1,1),
                        size_hint_y=None,
                        height=dp(60)
                    ))
                    return

                for idx, sol in enumerate(sols, 1):
                    fig = data_fig(sol["figure"])["africain"]
                    sec = (" | " + sol["secondary"]) if sol.get("secondary") else ""
                    allpos = sol.get("all_positions", sol.get("positions", []))
                    txt = (
                        f"{idx}. {fig} uniquement {allpos}\n"
                        f"M1={sol['m1']} M2={sol['m2']} M3={sol['m3']} M4={sol['m4']}{sec}"
                    )
                    b = Button(text=txt, font_size=dp(10), size_hint_y=None, height=dp(54))
                    b.bind(on_release=lambda btn, s=sol, sol_list=sols, pp=pop: self.apply_solution_from_list(s, sol_list, pp))
                    grid.add_widget(b)
            except Exception as e:
                header.text = "Erreur"
                grid.add_widget(Label(text=str(e), color=(1,1,1,1), size_hint_y=None, height=dp(80)))

        Clock.schedule_once(fill, 0.1)

    MoneyRoot.open_solution_window = open_solution_window_v103

    def popup_repetition_count(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(
            text="GEOSTAR peut chercher toutes les solutions où une figure apparaît exactement N fois.",
            color=(1,1,1,1),
            size_hint=(1,None),
            height=dp(60)
        ))

        count_input = TextInput(
            hint_text="Nombre de répétitions désiré, exemple : 3",
            multiline=False
        )
        figure_input = TextInput(
            hint_text="Figure facultative : Sedjou ou 1121. Vide = toutes les figures",
            multiline=False
        )
        box.add_widget(count_input)
        box.add_widget(figure_input)

        btn = Button(text="CALCULER", size_hint=(1,None), height=dp(45))
        box.add_widget(btn)

        pop = Popup(title="Recherche par nombre de répétitions", content=box, size_hint=(0.92,0.55))

        def go(_):
            try:
                count = int(count_input.text.strip())
                if count < 2 or count > 16:
                    raise ValueError("Le nombre doit être entre 2 et 16.")

                target = None
                if figure_input.text.strip():
                    target = code_vers_bin(figure_input.text.strip())

                pop.dismiss()
                self.open_repetition_results(count, target)
            except Exception as e:
                self.message("Erreur", str(e))

        btn.bind(on_release=go)
        pop.open()

    MoneyRoot.popup_repetition_count = popup_repetition_count

    def open_repetition_results(self, count, target_bits=None):
        title = f"Répétition exacte x{count}"
        content = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(6))
        header = Label(
            text=f"{title}\nCalcul des 65 536 combinaisons...",
            color=(1,1,1,1),
            size_hint=(1,None),
            height=dp(65)
        )
        content.add_widget(header)

        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(3), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        sv.add_widget(grid)
        content.add_widget(sv)

        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        content.add_widget(close)

        pop = Popup(title=title, content=content, size_hint=(0.98,0.92))
        close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

        def fill(dt):
            key = "repeat_count_" + str(count) + "_" + (target_bits if target_bits else "all")
            if key in self.solution_cache:
                sols = self.solution_cache[key]
            else:
                sols = search_by_repetition_count(count, target_bits)
                self.solution_cache[key] = sols
                write_json(CACHE_FILE, self.solution_cache)

            header.text = f"{title}\nTotal : {len(sols)} solution(s)"

            for idx, sol in enumerate(sols, 1):
                fig = data_fig(sol["figure"])["africain"]
                txt = (
                    f"{idx}. {fig} x{count} en maisons {sol['positions']}\n"
                    f"M1={sol['m1']} M2={sol['m2']} M3={sol['m3']} M4={sol['m4']}"
                )
                b = Button(text=txt, font_size=dp(10), size_hint_y=None, height=dp(54))
                b.bind(on_release=lambda btn, s=sol, sol_list=sols, pp=pop: self.apply_solution_from_list(s, sol_list, pp))
                grid.add_widget(b)

        Clock.schedule_once(fill, 0.1)

    MoneyRoot.open_repetition_results = open_repetition_results

    old_popup_solutions = MoneyRoot.popup_solutions

    def popup_solutions_v103(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(
            text="Solutions intégrées + recherches personnalisées strictes.",
            color=(1,1,1,1),
            size_hint=(1,None),
            height=dp(40)
        ))

        options = [
            ("5-10-16 toutes", [5,10,16], False),
            ("5-10-16 rares 7-13/7-15", [5,10,16], True),
            ("3-10-15 toutes", [3,10,15], False),
            ("10-11-15", [10,11,15], False),
            ("3-11-15", [3,11,15], False),
            ("2-3-13", [2,3,13], False),
            ("10-13-15", [10,13,15], False),
            ("2-10-15", [2,10,15], False),
        ]

        for name, pos, rare in options:
            b = Button(text=name, size_hint=(1,None), height=dp(38))
            b.bind(on_release=lambda btn, n=name, p=pos, r=rare: self.open_solution_window(n, p, r))
            box.add_widget(b)

        add = Button(text="+ AJOUTER RECHERCHE PERSONNALISÉE", size_hint=(1,None), height=dp(42))
        add.bind(on_release=lambda x: self.popup_add_custom_search())
        box.add_widget(add)

        rep_btn = Button(text="RECHERCHE PAR NOMBRE DE RÉPÉTITIONS", size_hint=(1,None), height=dp(42))
        rep_btn.bind(on_release=lambda x: self.popup_repetition_count())
        box.add_widget(rep_btn)

        if self.custom_searches:
            box.add_widget(Label(text="Recherches perso :", color=(1,1,1,1), size_hint=(1,None), height=dp(26)))
            for item in self.custom_searches:
                name = item.get("name", "Sans nom")
                pos = item.get("positions", [])
                b = Button(text=f"{name} : {pos}", size_hint=(1,None), height=dp(36))
                b.bind(on_release=lambda btn, it=item: self.open_solution_window(it.get("name","Perso"), it.get("positions",[]), False))
                box.add_widget(b)

        manage = Button(text="SUPPRIMER UNE RECHERCHE PERSO", size_hint=(1,None), height=dp(42))
        manage.bind(on_release=lambda x: self.popup_delete_custom_search())
        box.add_widget(manage)

        sv_sols = ScrollView()
        sv_sols.add_widget(box)
        outer_sols = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(4))
        outer_sols.add_widget(sv_sols)
        btn_fermer = Button(text="FERMER", size_hint=(1,None), height=dp(44),
                            background_color=(0.3,0.3,0.3,1))
        outer_sols.add_widget(btn_fermer)
        pop_s = Popup(title="SOLUTIONS", content=outer_sols, size_hint=(0.94,0.92))
        btn_fermer.bind(on_release=lambda x: pop_s.dismiss())
        self._popup_solutions_principale = pop_s
        pop_s.open()

    MoneyRoot.popup_solutions = popup_solutions_v103

    def popup_notes_current_v103(self):
        existing = None
        for n in self.notes:
            if n.get("key") == self.current_key():
                existing = n
                break

        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))

        name = TextInput(
            hint_text="Nom de la note",
            multiline=False,
            text=existing.get("nom", "") if existing else ""
        )
        note = TextInput(
            hint_text="Note écrite",
            multiline=True,
            text=existing.get("note", "") if existing else ""
        )
        vocal = TextInput(
            hint_text="Mémo vocal : nom du fichier ou chemin",
            multiline=False,
            text=existing.get("vocal", "") if existing else ""
        )

        box.add_widget(name)
        box.add_widget(note)
        box.add_widget(vocal)

        btns1 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        save_btn = Button(text="ENREGISTRER")
        mic_btn = Button(text="MICRO")
        play_btn = Button(text="LIRE VOCAL")
        btns1.add_widget(save_btn)
        btns1.add_widget(mic_btn)
        btns1.add_widget(play_btn)
        box.add_widget(btns1)

        btns2 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        delete_vocal_btn = Button(text="SUPPRIMER VOCAL")
        delete_note_btn = Button(text="SUPPRIMER NOTE")
        close_btn = Button(text="FERMER")
        btns2.add_widget(delete_vocal_btn)
        btns2.add_widget(delete_note_btn)
        btns2.add_widget(close_btn)
        box.add_widget(btns2)

        pop = Popup(title="NOTE du thème", content=box, size_hint=(0.94,0.84))

        def save(_):
            item = {
                "key": self.current_key(),
                "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "nom": name.text.strip() or "Note sans nom",
                "note": note.text.strip(),
                "vocal": vocal.text.strip(),
                "meres": self.mother_codes,
                "maisons": {str(k): v for k, v in self.h.items()},
            }

            found = False
            for i, n in enumerate(self.notes):
                if n.get("key") == item["key"]:
                    self.notes[i] = item
                    found = True
                    break
            if not found:
                self.notes.append(item)

            write_json(NOTES_FILE, self.notes)
            pop.dismiss()
            self.message("NOTE", "Note enregistrée.")

        def delete_vocal(_):
            vocal.text = ""
            self.message("Vocal", "Mémo vocal supprimé de cette note. Clique ensuite sur ENREGISTRER.")

        def delete_note(_):
            self.notes = [n for n in self.notes if n.get("key") != self.current_key()]
            write_json(NOTES_FILE, self.notes)
            pop.dismiss()
            self.message("NOTE", "Note supprimée.")

        def play_vocal(_):
            v = vocal.text.strip()
            if not v:
                self.message("Vocal", "Aucun mémo vocal indiqué dans cette note.")
                return
            self.message("Vocal", "Mémo vocal enregistré :\n" + v)

        save_btn.bind(on_release=save)
        mic_btn.bind(on_release=lambda x: self.open_micro())
        play_btn.bind(on_release=play_vocal)
        delete_vocal_btn.bind(on_release=delete_vocal)
        delete_note_btn.bind(on_release=delete_note)
        close_btn.bind(on_release=lambda x: pop.dismiss())

        pop.open()

    MoneyRoot.popup_notes_current = popup_notes_current_v103

_money_v103_patch()



# ============================================================
# PATCH GEOSTAR - ALIGNEMENT MAISONS 14 13 15 16
# ============================================================

def _geostar_alignment_patch():
    def maison_positions_geostar(self):
        return {
            # Ligne 1 droite -> gauche : M1 a droite, M8 a gauche
            8:(0.04,0.79,0.10,0.18),
            7:(0.16,0.79,0.10,0.18),
            6:(0.28,0.79,0.10,0.18),
            5:(0.40,0.79,0.10,0.18),
            4:(0.52,0.79,0.10,0.18),
            3:(0.64,0.79,0.10,0.18),
            2:(0.76,0.79,0.10,0.18),
            1:(0.88,0.79,0.10,0.18),

            # Ligne 2
            12:(0.10,0.57,0.10,0.18),
            11:(0.34,0.57,0.10,0.18),
            10:(0.58,0.57,0.10,0.18),
            9:(0.82,0.57,0.10,0.18),

            # Ligne 3 : M14, M15, M13, M16 alignées
            # M15 est entre M14 et M13.
            # M16 est à droite de M13.
            14:(0.20,0.33,0.10,0.18),
            15:(0.43,0.33,0.10,0.18),
            13:(0.66,0.33,0.10,0.18),
            16:(0.84,0.33,0.10,0.18),
        }

    MoneyRoot.maison_positions = maison_positions_geostar

_geostar_alignment_patch()



# ============================================================
# GEOSTAR V10.5 - PATCH COMPLET
# ============================================================
# Corrections appliquées :
# - Vent = jaune
# - Terre = marron
# - Statistiques bas écran : points 1 / points 2 + Feu/Vent/Eau/Terre
# - Recherche indépendante de l'ordre des maisons
# - Recherche personnalisée stricte : la figure ciblée apparaît uniquement
#   dans les maisons choisies, les autres figures peuvent se répéter ailleurs
# - Fermeture automatique de la fenêtre solution au clic
# - Cache permanent
# - Recherches par nombre de répétitions sauvegardables/supprimables
# - Notes vocales internes : enregistrer / arrêter / lire / supprimer
# ============================================================

REPEAT_FILE = "geostar_recherches_repetitions.json"
VOCAL_DIR = "geostar_vocaux"

def _geostar_v105_patch():

    # ---------------- COULEURS ----------------

    def element_color_v105(element):
        if element == "feu":
            return (1.0, 0.18, 0.12, 1)       # rouge
        if element == "vent":
            return (1.0, 0.85, 0.05, 1)       # jaune
        if element == "eau":
            return (0.15, 0.42, 1.0, 1)       # bleu
        if element == "terre":
            return (0.48, 0.28, 0.12, 1)      # marron
        if element == "quantique":
            return (0.65, 0.30, 1.0, 1)
        return (1, 1, 1, 1)

    globals()["element_color"] = element_color_v105

    # ---------------- POSITIONS MAISONS ----------------

    def maison_positions_geostar_v105(self):
        return {
            8:(0.04,0.79,0.10,0.18),
            7:(0.16,0.79,0.10,0.18),
            6:(0.28,0.79,0.10,0.18),
            5:(0.40,0.79,0.10,0.18),
            4:(0.52,0.79,0.10,0.18),
            3:(0.64,0.79,0.10,0.18),
            2:(0.76,0.79,0.10,0.18),
            1:(0.88,0.79,0.10,0.18),

            12:(0.10,0.57,0.10,0.18),
            11:(0.34,0.57,0.10,0.18),
            10:(0.58,0.57,0.10,0.18),
            9:(0.82,0.57,0.10,0.18),

            # 14, 15, 13, 16 sur la même ligne
            14:(0.20,0.33,0.10,0.18),
            15:(0.43,0.33,0.10,0.18),
            13:(0.66,0.33,0.10,0.18),
            16:(0.84,0.33,0.10,0.18),
        }

    MoneyRoot.maison_positions = maison_positions_geostar_v105

    # ---------------- STATISTIQUES ----------------

    def mettre_infos_v105(self):
        portes = analyser_portes(self.h)
        texte_portes = " | ".join([f"{p[0]}:{data_fig(p[1])['africain']}" for p in portes]) if portes else "Aucune porte"

        points_1 = 0
        points_2 = 0
        feu = vent = eau = terre = quantique = 0

        for i in range(1, 17):
            bits = self.h[i]
            points_1 += bits.count("1")
            points_2 += bits.count("0")

            el = element_of_bits(bits)
            if el == "feu":
                feu += 1
            elif el == "vent":
                vent += 1
            elif el == "eau":
                eau += 1
            elif el == "terre":
                terre += 1
            elif el == "quantique":
                quantique += 1

        nav = ""
        if getattr(self, "active_solutions", None) and self.active_solution_index >= 0:
            nav = f"\nSolution {self.active_solution_index+1}/{len(self.active_solutions)} — glisse gauche/droite"

        self.info.text = (
            f"Points 1 : {points_1} | Points 2 : {points_2}\n"
            f"Feu : {feu} | Vent : {vent} | Eau : {eau} | Terre : {terre}\n"
            f"Portes : {texte_portes}{nav}"
        )

    MoneyRoot.mettre_infos = mettre_infos_v105

    # ---------------- RECHERCHE ORDRE INDEPENDANT ----------------

    def parse_positions_v105(txt):
        nums = [int(x) for x in re.findall(r"\d+", txt)]
        nums = [n for n in nums if 1 <= n <= 16]
        nums = sorted(set(nums))
        if len(nums) < 2:
            raise ValueError("Il faut au moins deux maisons. Exemple : M8 M7 M3 M9")
        return nums

    globals()["parse_positions"] = parse_positions_v105

    def search_custom_strict_positions_v105(positions, target_bits=None, rare=False):
        """
        Recherche stricte :
        - Les maisons choisies peuvent être dans n'importe quel ordre.
        - Une même figure doit apparaître exactement dans ces maisons.
        - Cette figure ne doit pas apparaître ailleurs.
        - Les autres figures peuvent se répéter ailleurs.
        """
        wanted = sorted(set([int(p) for p in positions]))
        solutions = []
        seen = set()

        for m1 in TOUTES_LES_FIGURES:
            for m2 in TOUTES_LES_FIGURES:
                for m3 in TOUTES_LES_FIGURES:
                    for m4 in TOUTES_LES_FIGURES:
                        h2 = developper_theme(m1, m2, m3, m4)
                        vals = [h2[p] for p in wanted]

                        if not all(v == vals[0] for v in vals):
                            continue

                        fig = vals[0]

                        if target_bits is not None and fig != target_bits:
                            continue

                        exact_pos = sorted([i for i in range(1, 17) if h2[i] == fig])
                        if exact_pos != wanted:
                            continue

                        secondary = ""
                        if rare:
                            if h2[7] == h2[13] and h2[7] != fig:
                                secondary = "7-13 " + data_fig(h2[7])["africain"]
                            elif h2[7] == h2[15] and h2[7] != fig:
                                secondary = "7-15 " + data_fig(h2[7])["africain"]
                            else:
                                continue

                        key = (m1, m2, m3, m4, tuple(wanted), fig, secondary)
                        if key in seen:
                            continue
                        seen.add(key)

                        solutions.append({
                            "m1": m1,
                            "m2": m2,
                            "m3": m3,
                            "m4": m4,
                            "positions": wanted[:],
                            "figure": fig,
                            "secondary": secondary,
                            "all_positions": exact_pos,
                        })

        return solutions

    globals()["search_strict_positions"] = search_custom_strict_positions_v105

    def cache_key_v105(self, positions, rare=False):
        positions = sorted(set([int(p) for p in positions]))
        return ("strict_rare_" if rare else "strict_custom_") + "_".join(map(str, positions))

    def get_solutions_cached_v105(self, positions, rare=False):
        positions = sorted(set([int(p) for p in positions]))
        key = self.cache_key(positions, rare)

        if key in self.solution_cache:
            return self.solution_cache[key]

        self.info.text = "Calcul strict des 65 536 combinaisons..."
        sols = search_custom_strict_positions_v105(positions, None, rare)
        self.solution_cache[key] = sols
        write_json(CACHE_FILE, self.solution_cache)
        return sols

    MoneyRoot.cache_key = cache_key_v105
    MoneyRoot.get_solutions_cached = get_solutions_cached_v105

    # ---------------- SOLUTIONS ----------------

    def open_solution_window_v105(self, title, positions, rare):
        positions = sorted(set([int(p) for p in positions]))

        content = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(6))
        header = Label(
            text=f"{title}\nRecherche stricte : la figure apparaît uniquement dans {positions}.",
            color=(1,1,1,1),
            size_hint=(1,None),
            height=dp(75)
        )
        content.add_widget(header)

        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(3), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        sv.add_widget(grid)
        content.add_widget(sv)

        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        content.add_widget(close)

        pop = Popup(title=title, content=content, size_hint=(0.98,0.92))
        close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

        def fill(dt):
            try:
                sols = self.get_solutions_cached(positions, rare)
                header.text = f"{title}\nTotal : {len(sols)} solution(s)"

                if not sols:
                    grid.add_widget(Label(
                        text="Aucune solution stricte trouvée.",
                        color=(1,1,1,1),
                        size_hint_y=None,
                        height=dp(60)
                    ))
                    return

                for idx, sol in enumerate(sols, 1):
                    fig = data_fig(sol["figure"])["africain"]
                    sec = (" | " + sol["secondary"]) if sol.get("secondary") else ""
                    txt = (
                        f"{idx}. {fig} uniquement {sol['positions']}\n"
                        f"M1={sol['m1']} M2={sol['m2']} M3={sol['m3']} M4={sol['m4']}{sec}"
                    )
                    b = Button(text=txt, font_size=dp(10), size_hint_y=None, height=dp(54))
                    b.bind(on_release=lambda btn, s=sol, sol_list=sols, pp=pop: self.apply_solution_from_list_v105(s, sol_list, pp))
                    grid.add_widget(b)

            except Exception as e:
                header.text = "Erreur"
                grid.add_widget(Label(text=str(e), color=(1,1,1,1), size_hint_y=None, height=dp(80)))

        Clock.schedule_once(fill, 0.1)

    MoneyRoot.open_solution_window = open_solution_window_v105

    def apply_solution_from_list_v105(self, sol, sol_list, pop=None):
        if pop:
            pop.dismiss()
        self.active_solutions = sol_list
        try:
            self.active_solution_index = sol_list.index(sol)
        except ValueError:
            self.active_solution_index = 0

        self.mother_codes = [sol["m1"], sol["m2"], sol["m3"], sol["m4"]]
        self.afficher_theme(developper_theme(*self.mother_codes))

    MoneyRoot.apply_solution_from_list_v105 = apply_solution_from_list_v105
    MoneyRoot.apply_solution_from_list = apply_solution_from_list_v105

    # ---------------- RECHERCHES PAR NOMBRE DE REPETITIONS ----------------

    def get_repeat_searches(self):
        if not hasattr(self, "repeat_searches"):
            self.repeat_searches = read_json(REPEAT_FILE, [])
        return self.repeat_searches

    def save_repeat_searches(self):
        write_json(REPEAT_FILE, self.get_repeat_searches())

    MoneyRoot.get_repeat_searches = get_repeat_searches
    MoneyRoot.save_repeat_searches = save_repeat_searches

    def search_by_repetition_count_v105(count, target_bits=None):
        count = int(count)
        solutions = []
        seen = set()

        for m1 in TOUTES_LES_FIGURES:
            for m2 in TOUTES_LES_FIGURES:
                for m3 in TOUTES_LES_FIGURES:
                    for m4 in TOUTES_LES_FIGURES:
                        h2 = developper_theme(m1, m2, m3, m4)

                        rep = {}
                        for i in range(1, 17):
                            rep.setdefault(h2[i], []).append(i)

                        for fig, pos in rep.items():
                            if len(pos) != count:
                                continue
                            if target_bits is not None and fig != target_bits:
                                continue

                            pos = sorted(pos)
                            key = (m1, m2, m3, m4, fig, tuple(pos))
                            if key in seen:
                                continue
                            seen.add(key)

                            solutions.append({
                                "m1": m1,
                                "m2": m2,
                                "m3": m3,
                                "m4": m4,
                                "positions": pos[:],
                                "figure": fig,
                                "secondary": "",
                                "all_positions": pos[:],
                            })

        return solutions

    globals()["search_by_repetition_count"] = search_by_repetition_count_v105

    def popup_repetition_count_v105(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(
            text="Cherche toutes les solutions où une figure apparaît exactement N fois.",
            color=(1,1,1,1),
            size_hint=(1,None),
            height=dp(55)
        ))

        count_input = TextInput(hint_text="Nombre de répétitions, exemple : 3", multiline=False)
        figure_input = TextInput(hint_text="Figure facultative : Sedjou ou 1121. Vide = toutes", multiline=False)
        name_input = TextInput(hint_text="Nom de cette recherche à sauvegarder", multiline=False)

        box.add_widget(count_input)
        box.add_widget(figure_input)
        box.add_widget(name_input)

        btn = Button(text="CALCULER ET SAUVEGARDER", size_hint=(1,None), height=dp(45))
        box.add_widget(btn)

        pop = Popup(title="Recherche par répétitions", content=box, size_hint=(0.92,0.65))

        def go(_):
            try:
                count = int(count_input.text.strip())
                if count < 2 or count > 16:
                    raise ValueError("Le nombre doit être entre 2 et 16.")

                target = None
                fig_label = "toutes figures"
                if figure_input.text.strip():
                    target = code_vers_bin(figure_input.text.strip())
                    fig_label = data_fig(target)["africain"]

                item = {
                    "name": name_input.text.strip() or f"Répétition x{count} {fig_label}",
                    "count": count,
                    "target": target,
                }

                searches = self.get_repeat_searches()
                if item not in searches:
                    searches.append(item)
                    self.save_repeat_searches()

                pop.dismiss()
                self.open_repetition_results_v105(count, target)

            except Exception as e:
                self.message("Erreur", str(e))

        btn.bind(on_release=go)
        pop.open()

    MoneyRoot.popup_repetition_count = popup_repetition_count_v105

    def open_repetition_results_v105(self, count, target_bits=None):
        title = f"Répétition exacte x{count}"
        content = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(6))
        header = Label(text=f"{title}\nCalcul...", color=(1,1,1,1), size_hint=(1,None), height=dp(65))
        content.add_widget(header)

        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(3), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        sv.add_widget(grid)
        content.add_widget(sv)

        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        content.add_widget(close)

        pop = Popup(title=title, content=content, size_hint=(0.98,0.92))
        close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

        def fill(dt):
            key = "repeat_count_" + str(count) + "_" + (target_bits if target_bits else "all")
            if key in self.solution_cache:
                sols = self.solution_cache[key]
            else:
                sols = search_by_repetition_count_v105(count, target_bits)
                self.solution_cache[key] = sols
                write_json(CACHE_FILE, self.solution_cache)

            header.text = f"{title}\nTotal : {len(sols)} solution(s)"

            for idx, sol in enumerate(sols, 1):
                fig = data_fig(sol["figure"])["africain"]
                txt = (
                    f"{idx}. {fig} x{count} en maisons {sol['positions']}\n"
                    f"M1={sol['m1']} M2={sol['m2']} M3={sol['m3']} M4={sol['m4']}"
                )
                b = Button(text=txt, font_size=dp(10), size_hint_y=None, height=dp(54))
                b.bind(on_release=lambda btn, s=sol, sol_list=sols, pp=pop: self.apply_solution_from_list_v105(s, sol_list, pp))
                grid.add_widget(b)

        Clock.schedule_once(fill, 0.1)

    MoneyRoot.open_repetition_results_v105 = open_repetition_results_v105

    def popup_delete_repeat_search(self):
        searches = self.get_repeat_searches()

        content = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(6))
        content.add_widget(Label(text="Supprimer une recherche par répétitions.", color=(1,1,1,1), size_hint=(1,None), height=dp(40)))

        if not searches:
            content.add_widget(Label(text="Aucune recherche enregistrée.", color=(1,1,1,1), size_hint=(1,None), height=dp(45)))

        for item in searches:
            txt = f"{item.get('name')} | x{item.get('count')}"
            b = Button(text=txt, size_hint=(1,None), height=dp(42))
            b.bind(on_release=lambda btn, it=item: self.delete_repeat_search(it))
            content.add_widget(b)

        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        content.add_widget(close)

        pop = Popup(title="Supprimer répétitions", content=content, size_hint=(0.92,0.75))
        close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    MoneyRoot.popup_delete_repeat_search = popup_delete_repeat_search

    def delete_repeat_search(self, item):
        self.repeat_searches = [x for x in self.get_repeat_searches() if x != item]
        self.save_repeat_searches()
        self.message("Répétitions", "Recherche supprimée.")

    MoneyRoot.delete_repeat_search = delete_repeat_search

    # ---------------- MENU SOLUTIONS COMPLET ----------------

    def popup_solutions_v105(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(text="Solutions + recherches personnalisées.", color=(1,1,1,1), size_hint=(1,None), height=dp(36)))

        options = [
            ("5-10-16 toutes", [5,10,16], False),
            ("5-10-16 rares 7-13/7-15", [5,10,16], True),
            ("3-10-15 toutes", [3,10,15], False),
            ("10-11-15", [10,11,15], False),
            ("3-11-15", [3,11,15], False),
            ("2-3-13", [2,3,13], False),
            ("10-13-15", [10,13,15], False),
            ("2-10-15", [2,10,15], False),
        ]

        for name, pos, rare in options:
            b = Button(text=name, size_hint=(1,None), height=dp(36))
            b.bind(on_release=lambda btn, n=name, p=pos, r=rare: self.open_solution_window(n, p, r))
            box.add_widget(b)

        add = Button(text="+ AJOUTER RECHERCHE PERSONNALISÉE", size_hint=(1,None), height=dp(40))
        add.bind(on_release=lambda x: self.popup_add_custom_search())
        box.add_widget(add)

        rep_btn = Button(text="+ RECHERCHE PAR NOMBRE DE RÉPÉTITIONS", size_hint=(1,None), height=dp(40))
        rep_btn.bind(on_release=lambda x: self.popup_repetition_count())
        box.add_widget(rep_btn)

        if self.custom_searches:
            box.add_widget(Label(text="Recherches perso :", color=(1,1,1,1), size_hint=(1,None), height=dp(24)))
            for item in self.custom_searches:
                name = item.get("name", "Sans nom")
                pos = sorted(set(item.get("positions", [])))
                b = Button(text=f"{name} : {pos}", size_hint=(1,None), height=dp(34))
                b.bind(on_release=lambda btn, it=item: self.open_solution_window(it.get("name","Perso"), sorted(set(it.get("positions",[]))), False))
                box.add_widget(b)

        repeat_searches = self.get_repeat_searches()
        if repeat_searches:
            box.add_widget(Label(text="Recherches répétitions :", color=(1,1,1,1), size_hint=(1,None), height=dp(24)))
            for item in repeat_searches:
                name = item.get("name", "Répétition")
                count = item.get("count")
                target = item.get("target")
                b = Button(text=f"{name} | x{count}", size_hint=(1,None), height=dp(34))
                b.bind(on_release=lambda btn, it=item: self.open_repetition_results_v105(it.get("count"), it.get("target")))
                box.add_widget(b)

        manage = Button(text="SUPPRIMER RECHERCHE PERSO", size_hint=(1,None), height=dp(38))
        manage.bind(on_release=lambda x: self.popup_delete_custom_search())
        box.add_widget(manage)

        manage_rep = Button(text="SUPPRIMER RECHERCHE RÉPÉTITIONS", size_hint=(1,None), height=dp(38))
        manage_rep.bind(on_release=lambda x: self.popup_delete_repeat_search())
        box.add_widget(manage_rep)

        Popup(title="SOLUTIONS", content=box, size_hint=(0.94,0.94)).open()

    MoneyRoot.popup_solutions = popup_solutions_v105

_geostar_v105_patch()



# ============================================================
# GEOSTAR V10.6 - VOCAUX INTERNES + NUANCES COULEURS
# ============================================================
import time

def _geostar_v106_patch():
    def color_for_bits_v106(bits):
        if bits not in BIN_TO_CODE:
            return (0.65, 0.30, 1.0, 1)
        code = BIN_TO_CODE[bits]
        maps = {
            "1121": (1.00, 0.10, 0.08, 1), "1222": (1.00, 0.28, 0.20, 1),
            "1122": (0.86, 0.05, 0.04, 1), "1212": (1.00, 0.45, 0.35, 1),
            "2111": (1.00, 0.92, 0.10, 1), "2122": (0.92, 0.78, 0.05, 1),
            "2112": (1.00, 0.82, 0.22, 1), "2121": (0.78, 0.68, 0.05, 1),
            "1111": (0.10, 0.35, 1.00, 1), "2222": (0.20, 0.55, 1.00, 1),
            "1112": (0.05, 0.22, 0.85, 1), "2212": (0.38, 0.68, 1.00, 1),
            "2211": (0.44, 0.24, 0.10, 1), "1221": (0.58, 0.34, 0.16, 1),
            "1211": (0.36, 0.20, 0.08, 1), "2221": (0.70, 0.45, 0.23, 1),
        }
        return maps.get(code, (1,1,1,1))

    def redraw(self, *args):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        if w <= 5 or h <= 5:
            return
        with self.canvas:
            if getattr(self, "repeated", False):
                Color(*color_for_bits_v106(self.bits))
            else:
                Color(1, 1, 1, 1)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(5)])
            Color(0, 0, 0, 1)
            top = h * 0.17
            bottom = h * 0.13
            row_gap = (h - top - bottom) / 4.0
            dot_r = min(w, h) * 0.055
            sep = w * 0.18
            for i, b in enumerate(self.bits):
                cy = y + h - top - (i+0.5)*row_gap
                cx = x + w/2
                self.draw_symbol(cx, cy, dot_r, sep, b)
            Color(0, 0, 0, 0.25)
            Line(rounded_rectangle=(x, y, w, h, dp(5)), width=1)

    FigureCard.redraw = redraw

    def ensure_vocal_dir():
        path = os.path.abspath(VOCAL_DIR)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path

    def safe_key_for_file(key):
        return "".join(c if c.isalnum() else "_" for c in key)

    def start_recording_v106(self, vocal_input=None):
        if platform != "android":
            self.message("Micro", "Enregistrement direct disponible sur Android uniquement pour l’instant.")
            return
        try:
            from jnius import autoclass
            MediaRecorder = autoclass("android.media.MediaRecorder")
            AudioSource = autoclass("android.media.MediaRecorder$AudioSource")
            OutputFormat = autoclass("android.media.MediaRecorder$OutputFormat")
            AudioEncoder = autoclass("android.media.MediaRecorder$AudioEncoder")
            folder = ensure_vocal_dir()
            filepath = os.path.join(folder, "geostar_" + safe_key_for_file(self.current_key()) + "_" + str(int(time.time())) + ".m4a")
            recorder = MediaRecorder()
            recorder.setAudioSource(AudioSource.MIC)
            recorder.setOutputFormat(OutputFormat.MPEG_4)
            recorder.setAudioEncoder(AudioEncoder.AAC)
            recorder.setOutputFile(filepath)
            recorder.prepare()
            recorder.start()
            self._geostar_recorder = recorder
            self._geostar_recording_path = filepath
            if vocal_input is not None:
                vocal_input.text = filepath
            self.message("Micro", "Enregistrement commencé dans GEOSTAR.\nQuand tu as terminé, clique sur STOP VOCAL.")
        except Exception as e:
            self.message("Micro", "Impossible d’enregistrer directement.\nVérifie la permission Micro de Pydroid.\n\nErreur : " + str(e))

    def stop_recording_v106(self, vocal_input=None):
        rec = getattr(self, "_geostar_recorder", None)
        path = getattr(self, "_geostar_recording_path", "")
        if rec is None:
            self.message("Micro", "Aucun enregistrement en cours.")
            return
        try:
            rec.stop()
            rec.release()
        except Exception:
            try:
                rec.release()
            except Exception:
                pass
        self._geostar_recorder = None
        if vocal_input is not None and path:
            vocal_input.text = path
        self.message("Micro", "Mémo vocal enregistré :\n" + path + "\nClique sur ENREGISTRER pour l’attacher à la note.")

    def play_vocal_v106(self, path):
        if not path:
            self.message("Vocal", "Aucun mémo vocal dans cette note.")
            return
        if not os.path.exists(path):
            self.message("Vocal", "Fichier introuvable :\n" + path)
            return
        if platform == "android":
            try:
                from jnius import autoclass
                MediaPlayer = autoclass("android.media.MediaPlayer")
                player = MediaPlayer()
                player.setDataSource(path)
                player.prepare()
                player.start()
                self._geostar_player = player
                self.message("Vocal", "Lecture du mémo vocal en cours.")
                return
            except Exception as e:
                self.message("Vocal", "Impossible de lire le vocal.\n\n" + str(e))
                return
        self.message("Vocal", "Fichier vocal :\n" + path)

    def delete_vocal_file_v106(self, vocal_input=None):
        path = vocal_input.text.strip() if vocal_input is not None else ""
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                self.message("Vocal", "Impossible de supprimer le fichier.\n\n" + str(e))
                return
        if vocal_input is not None:
            vocal_input.text = ""
        self.message("Vocal", "Vocal supprimé. Clique sur ENREGISTRER pour sauvegarder.")

    MoneyRoot.start_recording_v106 = start_recording_v106
    MoneyRoot.stop_recording_v106 = stop_recording_v106
    MoneyRoot.play_vocal_v106 = play_vocal_v106
    MoneyRoot.delete_vocal_file_v106 = delete_vocal_file_v106

    def popup_notes_current_v106(self):
        existing = None
        for n in self.notes:
            if n.get("key") == self.current_key():
                existing = n
                break
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        name = TextInput(hint_text="Nom de la note", multiline=False, text=existing.get("nom", "") if existing else "")
        note = TextInput(hint_text="Note écrite", multiline=True, text=existing.get("note", "") if existing else "")
        vocal = TextInput(hint_text="Mémo vocal GEOSTAR", multiline=False, text=existing.get("vocal", "") if existing else "")
        box.add_widget(name); box.add_widget(note); box.add_widget(vocal)
        row1 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        save_btn = Button(text="ENREGISTRER"); rec_btn = Button(text="REC VOCAL"); stop_btn = Button(text="STOP VOCAL")
        row1.add_widget(save_btn); row1.add_widget(rec_btn); row1.add_widget(stop_btn); box.add_widget(row1)
        row2 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        play_btn = Button(text="LIRE VOCAL"); del_vocal = Button(text="SUPPRIMER VOCAL"); del_note = Button(text="SUPPRIMER NOTE")
        row2.add_widget(play_btn); row2.add_widget(del_vocal); row2.add_widget(del_note); box.add_widget(row2)
        close_btn = Button(text="FERMER", size_hint=(1,None), height=dp(42)); box.add_widget(close_btn)
        pop = Popup(title="NOTE du thème", content=box, size_hint=(0.94,0.88))

        def save(_):
            item = {
                "key": self.current_key(),
                "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "nom": name.text.strip() or "Note sans nom",
                "note": note.text.strip(),
                "vocal": vocal.text.strip(),
                "meres": self.mother_codes,
                "maisons": {str(k): v for k, v in self.h.items()},
            }
            found = False
            for i, n in enumerate(self.notes):
                if n.get("key") == item["key"]:
                    self.notes[i] = item; found = True; break
            if not found:
                self.notes.append(item)
            write_json(NOTES_FILE, self.notes)
            self.message("NOTE", "Note enregistrée.")

        def delete_note(_):
            v = vocal.text.strip()
            if v and os.path.exists(v):
                try: os.remove(v)
                except Exception: pass
            self.notes = [n for n in self.notes if n.get("key") != self.current_key()]
            write_json(NOTES_FILE, self.notes)
            pop.dismiss()
            self.message("NOTE", "Note supprimée.")

        save_btn.bind(on_release=save)
        rec_btn.bind(on_release=lambda x: self.start_recording_v106(vocal))
        stop_btn.bind(on_release=lambda x: self.stop_recording_v106(vocal))
        play_btn.bind(on_release=lambda x: self.play_vocal_v106(vocal.text.strip()))
        del_vocal.bind(on_release=lambda x: self.delete_vocal_file_v106(vocal))
        del_note.bind(on_release=delete_note)
        close_btn.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    MoneyRoot.popup_notes_current = popup_notes_current_v106

_geostar_v106_patch()



# ============================================================
# GEOSTAR V10.6.1 - CORRECTION CRASH ADD_CARD
# ============================================================

def _geostar_v1061_patch():

    def add_card_flexible(self, maison, bits, rx, ry, rw, rh, repeated=False, *args, **kwargs):
        card = FigureCard(
            maison=maison,
            bits=bits,
            root=self,
            repeated=repeated,
            size_hint=(rw, rh),
            pos_hint={"x": rx, "y": ry}
        )

        label = Label(
            text=f"[b]M{maison}[/b]",
            markup=True,
            color=(1, 0.86, 0.05, 1),
            font_size=dp(14),
            size_hint=(rw, None),
            height=dp(22),
            pos_hint={"x": rx, "y": ry + rh}
        )

        self.board.add_widget(label)
        self.board.add_widget(card)
        self.cards[maison] = card
        self.labels[maison] = label

    MoneyRoot.add_card = add_card_flexible

    def afficher_theme_flexible(self, h):
        self.h = h
        self.board.clear_widgets()
        self.cards = {}
        self.labels = {}

        reps = analyser_repetitions(self.h)
        repeated = set()
        for bits, maisons in reps.items():
            if len(maisons) >= 2:
                for m in maisons:
                    repeated.add(m)

        for maison, pos in self.maison_positions().items():
            rx, ry, rw, rh = pos
            self.add_card(maison, h[maison], rx, ry, rw, rh, repeated=(maison in repeated))

        self.title.text = "[b]GEOSTAR[/b]\n" + datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.mettre_infos()

    MoneyRoot.afficher_theme = afficher_theme_flexible

_geostar_v1061_patch()



# ============================================================
# GEOSTAR V10.7 - VOCAUX MODE FIABLE Pydroid
# ============================================================
# Pydroid bloque souvent MediaRecorder direct.
# Cette version utilise :
# - OUVRIR ENREGISTREUR : ouvre l'app Android d'enregistrement.
# - CHOISIR VOCAL : ouvre le sélecteur de fichiers audio.
# - LIRE VOCAL : lit le vocal choisi.
# - SUPPRIMER VOCAL : supprime le fichier si Android/Pydroid autorise.
# ============================================================

def _geostar_v107_patch():

    def open_android_recorder_v107(self):
        if platform != "android":
            self.message("Micro", "Sur iPhone/Web, utilise Dictaphone puis indique le fichier vocal.")
            return

        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            intent = Intent("android.provider.MediaStore.RECORD_SOUND")
            PythonActivity.mActivity.startActivity(intent)

            self.message(
                "Micro",
                "L'enregistreur Android est ouvert.\n\n"
                "1. Enregistre ton mémo.\n"
                "2. Reviens dans GEOSTAR.\n"
                "3. Clique sur CHOISIR VOCAL pour l'attacher à la note."
            )
        except Exception as e:
            self.message(
                "Micro",
                "Impossible d'ouvrir l'enregistreur Android.\n\n"
                "Utilise l'application Enregistreur vocal manuellement, puis reviens dans GEOSTAR.\n\n"
                + str(e)
            )

    def choose_vocal_v107(self, vocal_input):
        if platform != "android":
            self.message("Vocal", "Sélection de fichier disponible surtout sur Android/Pydroid.")
            return

        try:
            from androidstorage4kivy import SharedStorage
            from plyer import filechooser

            def callback(selection):
                if selection:
                    vocal_input.text = selection[0]
                    self.message("Vocal", "Vocal sélectionné :\n" + selection[0] + "\n\nClique sur ENREGISTRER pour sauvegarder la note.")

            filechooser.open_file(
                title="Choisir un mémo vocal",
                filters=[("Audio", "*.aac", "*.m4a", "*.mp3", "*.wav", "*.3gp", "*.ogg")],
                on_selection=callback
            )
            return
        except Exception:
            pass

        try:
            from plyer import filechooser

            def callback(selection):
                if selection:
                    vocal_input.text = selection[0]
                    self.message("Vocal", "Vocal sélectionné :\n" + selection[0] + "\n\nClique sur ENREGISTRER pour sauvegarder la note.")

            filechooser.open_file(
                title="Choisir un mémo vocal",
                filters=["*.aac", "*.m4a", "*.mp3", "*.wav", "*.3gp", "*.ogg"],
                on_selection=callback
            )
            return
        except Exception as e:
            self.message(
                "Vocal",
                "Le sélecteur de fichier n'est pas disponible dans cette version de Pydroid.\n\n"
                "Solution : copie le nom/chemin du fichier vocal dans le champ vocal.\n\n"
                + str(e)
            )

    def play_vocal_v107(self, path):
        path = path.strip()
        if not path:
            self.message("Vocal", "Aucun mémo vocal attaché à cette note.")
            return

        if platform == "android":
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                File = autoclass("java.io.File")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")

                intent = Intent(Intent.ACTION_VIEW)

                if path.startswith("content://"):
                    uri = Uri.parse(path)
                else:
                    uri = Uri.fromFile(File(path))

                intent.setDataAndType(uri, "audio/*")
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                PythonActivity.mActivity.startActivity(intent)
                return
            except Exception as e:
                self.message("Vocal", "Impossible de lire automatiquement ce vocal.\n\nChemin :\n" + path + "\n\nErreur : " + str(e))
                return

        self.message("Vocal", "Fichier vocal attaché :\n" + path)

    def delete_vocal_v107(self, vocal_input):
        path = vocal_input.text.strip()
        if not path:
            self.message("Vocal", "Aucun vocal à supprimer.")
            return

        # Les URI content:// ne peuvent souvent pas être supprimées par Pydroid.
        if path.startswith("content://"):
            vocal_input.text = ""
            self.message(
                "Vocal",
                "Le lien vocal a été retiré de la note.\n\n"
                "Android ne permet pas toujours à Pydroid de supprimer directement un fichier content://.\n"
                "Supprime le fichier depuis l'application Enregistreur vocal si nécessaire.\n\n"
                "Clique sur ENREGISTRER pour sauvegarder."
            )
            return

        try:
            if os.path.exists(path):
                os.remove(path)
            vocal_input.text = ""
            self.message("Vocal", "Vocal supprimé. Clique sur ENREGISTRER pour sauvegarder.")
        except Exception as e:
            vocal_input.text = ""
            self.message(
                "Vocal",
                "Le lien vocal a été retiré de la note, mais le fichier n'a pas pu être supprimé.\n\n"
                "Erreur : " + str(e) + "\n\nClique sur ENREGISTRER."
            )

    MoneyRoot.open_android_recorder_v107 = open_android_recorder_v107
    MoneyRoot.choose_vocal_v107 = choose_vocal_v107
    MoneyRoot.play_vocal_v107 = play_vocal_v107
    MoneyRoot.delete_vocal_v107 = delete_vocal_v107

    def popup_notes_current_v107(self):
        existing = None
        for n in self.notes:
            if n.get("key") == self.current_key():
                existing = n
                break

        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))

        name = TextInput(
            hint_text="Nom de la note",
            multiline=False,
            text=existing.get("nom", "") if existing else ""
        )
        note = TextInput(
            hint_text="Note écrite",
            multiline=True,
            text=existing.get("note", "") if existing else ""
        )
        vocal = TextInput(
            hint_text="Mémo vocal attaché",
            multiline=False,
            text=existing.get("vocal", "") if existing else ""
        )

        box.add_widget(name)
        box.add_widget(note)
        box.add_widget(vocal)

        row1 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        save_btn = Button(text="ENREGISTRER")
        record_btn = Button(text="OUVRIR ENREGISTREUR")
        choose_btn = Button(text="CHOISIR VOCAL")
        row1.add_widget(save_btn)
        row1.add_widget(record_btn)
        row1.add_widget(choose_btn)
        box.add_widget(row1)

        row2 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        play_btn = Button(text="LIRE VOCAL")
        delete_vocal_btn = Button(text="SUPPRIMER VOCAL")
        delete_note_btn = Button(text="SUPPRIMER NOTE")
        row2.add_widget(play_btn)
        row2.add_widget(delete_vocal_btn)
        row2.add_widget(delete_note_btn)
        box.add_widget(row2)

        close_btn = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        box.add_widget(close_btn)

        pop = Popup(title="NOTE du thème", content=box, size_hint=(0.96,0.88))

        def save(_):
            item = {
                "key": self.current_key(),
                "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "nom": name.text.strip() or "Note sans nom",
                "note": note.text.strip(),
                "vocal": vocal.text.strip(),
                "meres": self.mother_codes,
                "maisons": {str(k): v for k, v in self.h.items()},
            }

            found = False
            for i, n in enumerate(self.notes):
                if n.get("key") == item["key"]:
                    self.notes[i] = item
                    found = True
                    break
            if not found:
                self.notes.append(item)

            write_json(NOTES_FILE, self.notes)
            self.message("NOTE", "Note enregistrée.")

        def delete_note(_):
            # On retire la note. Le vocal attaché est supprimé seulement si fichier direct accessible.
            path = vocal.text.strip()
            if path and not path.startswith("content://") and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

            self.notes = [n for n in self.notes if n.get("key") != self.current_key()]
            write_json(NOTES_FILE, self.notes)
            pop.dismiss()
            self.message("NOTE", "Note supprimée.")

        save_btn.bind(on_release=save)
        record_btn.bind(on_release=lambda x: self.open_android_recorder_v107())
        choose_btn.bind(on_release=lambda x: self.choose_vocal_v107(vocal))
        play_btn.bind(on_release=lambda x: self.play_vocal_v107(vocal.text))
        delete_vocal_btn.bind(on_release=lambda x: self.delete_vocal_v107(vocal))
        delete_note_btn.bind(on_release=delete_note)
        close_btn.bind(on_release=lambda x: pop.dismiss())

        pop.open()

    MoneyRoot.popup_notes_current = popup_notes_current_v107

_geostar_v107_patch()



# ============================================================
# GEOSTAR V10.8 - SELECTEUR VOCAL ANDROID SANS PLYER
# ============================================================
# Corrige : No module named plyer
# Utilise Intent ACTION_GET_CONTENT + android.activity.bind
# ============================================================

def _geostar_v108_patch():

    def choose_vocal_native_v108(self, vocal_input):
        if platform != "android":
            self.message("Vocal", "Sélection vocale native disponible sur Android.")
            return

        try:
            from jnius import autoclass
            from android import activity

            Intent = autoclass("android.content.Intent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            self._geostar_pending_vocal_input = vocal_input

            def on_activity_result(requestCode, resultCode, intent):
                try:
                    if requestCode != 8808:
                        return

                    activity.unbind(on_activity_result=on_activity_result)

                    if intent is None:
                        self.message("Vocal", "Aucun vocal sélectionné.")
                        return

                    uri = intent.getData()
                    if uri is None:
                        self.message("Vocal", "Aucun vocal sélectionné.")
                        return

                    uri_text = uri.toString()
                    self._geostar_pending_vocal_input.text = uri_text

                    self.message(
                        "Vocal",
                        "Vocal attaché à la note :\n" + uri_text + "\n\nClique sur ENREGISTRER pour sauvegarder."
                    )

                except Exception as e:
                    self.message("Vocal", "Erreur pendant la sélection :\n" + str(e))

            activity.bind(on_activity_result=on_activity_result)

            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType("audio/*")
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            PythonActivity.mActivity.startActivityForResult(intent, 8808)

        except Exception as e:
            self.message(
                "Vocal",
                "Impossible d'ouvrir le sélecteur vocal Android.\n\n"
                "Tu peux quand même copier/coller le chemin ou le lien du fichier vocal dans le champ.\n\n"
                "Erreur : " + str(e)
            )

    def play_vocal_native_v108(self, path):
        path = path.strip()
        if not path:
            self.message("Vocal", "Aucun vocal attaché à cette note.")
            return

        if platform == "android":
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                File = autoclass("java.io.File")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")

                intent = Intent(Intent.ACTION_VIEW)

                if path.startswith("content://"):
                    uri = Uri.parse(path)
                else:
                    uri = Uri.fromFile(File(path))

                intent.setDataAndType(uri, "audio/*")
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                PythonActivity.mActivity.startActivity(intent)
                return

            except Exception as e:
                self.message("Vocal", "Impossible de lire ce vocal.\n\n" + str(e))
                return

        self.message("Vocal", "Vocal :\n" + path)

    def delete_vocal_native_v108(self, vocal_input):
        path = vocal_input.text.strip()
        if not path:
            self.message("Vocal", "Aucun vocal attaché.")
            return

        # Sur Android content://, on retire le lien de la note.
        # La suppression physique se fait dans l'app enregistreur.
        if path.startswith("content://"):
            vocal_input.text = ""
            self.message(
                "Vocal",
                "Le vocal a été retiré de la note.\n\n"
                "Si tu veux supprimer le fichier lui-même, fais-le depuis l'application Enregistreur vocal.\n\n"
                "Clique sur ENREGISTRER pour sauvegarder."
            )
            return

        try:
            if os.path.exists(path):
                os.remove(path)
            vocal_input.text = ""
            self.message("Vocal", "Vocal supprimé. Clique sur ENREGISTRER pour sauvegarder.")
        except Exception as e:
            vocal_input.text = ""
            self.message(
                "Vocal",
                "Le vocal a été retiré de la note, mais Android n'a pas autorisé la suppression du fichier.\n\n"
                "Erreur : " + str(e) + "\n\nClique sur ENREGISTRER."
            )

    MoneyRoot.choose_vocal_v107 = choose_vocal_native_v108
    MoneyRoot.play_vocal_v107 = play_vocal_native_v108
    MoneyRoot.delete_vocal_v107 = delete_vocal_native_v108

    # Si la version précédente utilisait encore ces noms :
    MoneyRoot.choose_vocal_v108 = choose_vocal_native_v108
    MoneyRoot.play_vocal_v108 = play_vocal_native_v108
    MoneyRoot.delete_vocal_v108 = delete_vocal_native_v108

_geostar_v108_patch()



# ============================================================
# GEOSTAR V10.9 - VOCAUX PAR SCAN DOSSIERS TABLETTE
# ============================================================
# Pydroid bloque :
# - MediaRecorder direct
# - plyer
# - retour du sélecteur Android
#
# Solution fiable :
# - Tu enregistres avec l'application Enregistreur vocal Android.
# - GEOSTAR scanne les dossiers de la tablette.
# - Tu cliques sur un fichier vocal trouvé.
# - Il est attaché à la note.
# - LIRE VOCAL ouvre le fichier.
# - SUPPRIMER VOCAL retire le lien et tente de supprimer le fichier.
# ============================================================

def _geostar_v109_patch():

    AUDIO_EXTENSIONS = (".aac", ".m4a", ".mp3", ".wav", ".3gp", ".ogg", ".amr")

    def vocal_search_dirs():
        base_dirs = [
            "/storage/emulated/0/Recordings",
            "/storage/emulated/0/Recording",
            "/storage/emulated/0/Recorder",
            "/storage/emulated/0/Sounds",
            "/storage/emulated/0/SoundRecorder",
            "/storage/emulated/0/Music",
            "/storage/emulated/0/Download",
            "/storage/emulated/0/Downloads",
            "/storage/emulated/0/Documents",
            "/sdcard/Recordings",
            "/sdcard/Recording",
            "/sdcard/Sounds",
            "/sdcard/Music",
            "/sdcard/Download",
        ]
        return base_dirs

    def scan_audio_files_v109(self, limit=200):
        found = []
        seen = set()

        for folder in vocal_search_dirs():
            if not os.path.exists(folder):
                continue

            try:
                for root, dirs, files in os.walk(folder):
                    # évite les scans trop profonds
                    depth = root.replace(folder, "").count(os.sep)
                    if depth > 3:
                        dirs[:] = []
                        continue

                    for name in files:
                        if name.lower().endswith(AUDIO_EXTENSIONS):
                            path = os.path.join(root, name)
                            if path not in seen:
                                seen.add(path)
                                found.append(path)

                        if len(found) >= limit:
                            return found
            except Exception:
                pass

        # Ajoute aussi les vocaux déjà enregistrés dans les notes
        try:
            for n in self.notes:
                v = n.get("vocal", "")
                if v and v not in seen:
                    seen.add(v)
                    found.append(v)
        except Exception:
            pass

        return found

    def open_android_recorder_v109(self):
        if platform != "android":
            self.message("Micro", "Sur iPhone/Web, utilise Dictaphone puis indique le nom du fichier.")
            return

        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            intent = Intent("android.provider.MediaStore.RECORD_SOUND")
            PythonActivity.mActivity.startActivity(intent)

            self.message(
                "Micro",
                "L'enregistreur vocal Android est ouvert.\n\n"
                "Après avoir enregistré :\n"
                "1. Reviens dans GEOSTAR.\n"
                "2. Clique sur LISTE VOCAUX.\n"
                "3. Choisis le fichier vocal."
            )
        except Exception:
            self.message(
                "Micro",
                "Ouvre manuellement ton application Enregistreur vocal Android.\n\n"
                "Après l'enregistrement, reviens dans GEOSTAR puis clique sur LISTE VOCAUX."
            )

    def popup_vocal_list_v109(self, vocal_input):
        files = scan_audio_files_v109(self)

        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))

        content.add_widget(Label(
            text=f"Vocaux trouvés : {len(files)}\nClique sur un vocal pour l'attacher à la note.",
            color=(1,1,1,1),
            size_hint=(1,None),
            height=dp(55)
        ))

        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        sv.add_widget(grid)
        content.add_widget(sv)

        if not files:
            grid.add_widget(Label(
                text="Aucun fichier vocal trouvé.\nEssaie d'enregistrer un vocal avec l'app Enregistreur vocal, puis reviens ici.",
                color=(1,1,1,1),
                size_hint_y=None,
                height=dp(90)
            ))

        for path in files:
            short = os.path.basename(path)
            folder = os.path.dirname(path)
            txt = short + "\n" + folder

            b = Button(text=txt, font_size=dp(10), size_hint_y=None, height=dp(58))

            def choose(btn, p=path):
                vocal_input.text = p
                pop.dismiss()
                self.message(
                    "Vocal",
                    "Vocal attaché :\n" + p + "\n\nClique sur ENREGISTRER pour sauvegarder la note."
                )

            b.bind(on_release=choose)
            grid.add_widget(b)

        manual = Button(text="ENTRER CHEMIN MANUELLEMENT", size_hint=(1,None), height=dp(42))
        content.add_widget(manual)

        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        content.add_widget(close)

        pop = Popup(title="Liste des vocaux", content=content, size_hint=(0.96,0.90))

        def manual_entry(_):
            pop.dismiss()
            self.message(
                "Chemin vocal",
                "Copie le chemin ou le nom du fichier vocal dans le champ vocal de la note.\n\n"
                "Exemple : /storage/emulated/0/Recordings/20260520-182859.aac"
            )

        manual.bind(on_release=manual_entry)
        close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    def play_vocal_v109(self, path):
        path = path.strip()
        if not path:
            self.message("Vocal", "Aucun vocal attaché à cette note.")
            return

        if not os.path.exists(path):
            self.message(
                "Vocal",
                "Le fichier vocal est introuvable.\n\n"
                "Chemin enregistré :\n" + path + "\n\n"
                "Clique sur LISTE VOCAUX pour rattacher le bon fichier."
            )
            return

        if platform == "android":
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                File = autoclass("java.io.File")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")

                intent = Intent(Intent.ACTION_VIEW)
                uri = Uri.fromFile(File(path))
                intent.setDataAndType(uri, "audio/*")
                PythonActivity.mActivity.startActivity(intent)
                return
            except Exception as e:
                self.message("Vocal", "Impossible de lire automatiquement.\n\n" + str(e))
                return

        self.message("Vocal", "Fichier vocal :\n" + path)

    def delete_vocal_v109(self, vocal_input):
        path = vocal_input.text.strip()

        if not path:
            self.message("Vocal", "Aucun vocal à supprimer.")
            return

        deleted_file = False

        try:
            if os.path.exists(path):
                os.remove(path)
                deleted_file = True
        except Exception:
            deleted_file = False

        vocal_input.text = ""

        if deleted_file:
            self.message(
                "Vocal",
                "Le fichier vocal a été supprimé et retiré de la note.\n\nClique sur ENREGISTRER."
            )
        else:
            self.message(
                "Vocal",
                "Le vocal a été retiré de la note.\n\n"
                "Android n'a pas autorisé la suppression physique du fichier, "
                "ou le fichier était déjà introuvable.\n\nClique sur ENREGISTRER."
            )

    def popup_notes_current_v109(self):
        existing = None
        for n in self.notes:
            if n.get("key") == self.current_key():
                existing = n
                break

        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))

        name = TextInput(
            hint_text="Nom de la note",
            multiline=False,
            text=existing.get("nom", "") if existing else ""
        )
        note = TextInput(
            hint_text="Note écrite",
            multiline=True,
            text=existing.get("note", "") if existing else ""
        )
        vocal = TextInput(
            hint_text="Mémo vocal attaché",
            multiline=False,
            text=existing.get("vocal", "") if existing else ""
        )

        box.add_widget(name)
        box.add_widget(note)
        box.add_widget(vocal)

        row1 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        save_btn = Button(text="ENREGISTRER")
        record_btn = Button(text="OUVRIR ENREGISTREUR")
        list_btn = Button(text="LISTE VOCAUX")
        row1.add_widget(save_btn)
        row1.add_widget(record_btn)
        row1.add_widget(list_btn)
        box.add_widget(row1)

        row2 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        play_btn = Button(text="LIRE VOCAL")
        delete_vocal_btn = Button(text="SUPPRIMER VOCAL")
        delete_note_btn = Button(text="SUPPRIMER NOTE")
        row2.add_widget(play_btn)
        row2.add_widget(delete_vocal_btn)
        row2.add_widget(delete_note_btn)
        box.add_widget(row2)

        close_btn = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        box.add_widget(close_btn)

        pop = Popup(title="NOTE du thème", content=box, size_hint=(0.96,0.88))

        def save(_):
            item = {
                "key": self.current_key(),
                "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "nom": name.text.strip() or "Note sans nom",
                "note": note.text.strip(),
                "vocal": vocal.text.strip(),
                "meres": self.mother_codes,
                "maisons": {str(k): v for k, v in self.h.items()},
            }

            found = False
            for i, n in enumerate(self.notes):
                if n.get("key") == item["key"]:
                    self.notes[i] = item
                    found = True
                    break

            if not found:
                self.notes.append(item)

            write_json(NOTES_FILE, self.notes)
            self.message("NOTE", "Note enregistrée.")

        def delete_note(_):
            # Supprime la note mais ne supprime pas forcément le fichier vocal
            # sauf si Android autorise.
            path = vocal.text.strip()
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

            self.notes = [n for n in self.notes if n.get("key") != self.current_key()]
            write_json(NOTES_FILE, self.notes)
            pop.dismiss()
            self.message("NOTE", "Note supprimée.")

        save_btn.bind(on_release=save)
        record_btn.bind(on_release=lambda x: open_android_recorder_v109(self))
        list_btn.bind(on_release=lambda x: popup_vocal_list_v109(self, vocal))
        play_btn.bind(on_release=lambda x: play_vocal_v109(self, vocal.text))
        delete_vocal_btn.bind(on_release=lambda x: delete_vocal_v109(self, vocal))
        delete_note_btn.bind(on_release=delete_note)
        close_btn.bind(on_release=lambda x: pop.dismiss())

        pop.open()

    MoneyRoot.popup_notes_current = popup_notes_current_v109

_geostar_v109_patch()



# ============================================================
# GEOSTAR V10.9.1 - FIX LECTURE VOCALE FILEURIEXPOSED
# ============================================================
# Corrige : FileUriExposedException
# La lecture vocale utilise maintenant MediaPlayer directement.
# ============================================================

def _geostar_v1091_patch():

    def play_vocal_internal_v1091(self, path):
        path = path.strip()

        if not path:
            self.message("Vocal", "Aucun vocal attaché à cette note.")
            return

        if not os.path.exists(path):
            self.message(
                "Vocal",
                "Le fichier vocal est introuvable :\n" + path + "\n\n"
                "Clique sur LISTE VOCAUX pour rattacher le bon fichier."
            )
            return

        if platform == "android":
            try:
                from jnius import autoclass

                # Arrête l'ancien lecteur si besoin.
                old_player = getattr(self, "_geostar_player", None)
                if old_player is not None:
                    try:
                        old_player.stop()
                        old_player.release()
                    except Exception:
                        pass

                MediaPlayer = autoclass("android.media.MediaPlayer")
                player = MediaPlayer()
                player.setDataSource(path)
                player.prepare()
                player.start()

                self._geostar_player = player
                self.message("Vocal", "Lecture du mémo vocal en cours.\n\n" + path)
                return

            except Exception as e:
                self.message(
                    "Vocal",
                    "Impossible de lire le vocal avec le lecteur interne.\n\n"
                    "Chemin :\n" + path + "\n\nErreur : " + str(e)
                )
                return

        self.message("Vocal", "Vocal attaché :\n" + path)

    def stop_vocal_internal_v1091(self):
        player = getattr(self, "_geostar_player", None)

        if player is None:
            self.message("Vocal", "Aucune lecture vocale en cours.")
            return

        try:
            player.stop()
            player.release()
        except Exception:
            pass

        self._geostar_player = None
        self.message("Vocal", "Lecture vocale arrêtée.")

    MoneyRoot.play_vocal_v109 = play_vocal_internal_v1091
    MoneyRoot.stop_vocal_internal_v1091 = stop_vocal_internal_v1091

    def popup_notes_current_v1091(self):
        existing = None
        for n in self.notes:
            if n.get("key") == self.current_key():
                existing = n
                break

        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))

        name = TextInput(
            hint_text="Nom de la note",
            multiline=False,
            text=existing.get("nom", "") if existing else ""
        )
        note = TextInput(
            hint_text="Note écrite",
            multiline=True,
            text=existing.get("note", "") if existing else ""
        )
        vocal = TextInput(
            hint_text="Mémo vocal attaché",
            multiline=False,
            text=existing.get("vocal", "") if existing else ""
        )

        box.add_widget(name)
        box.add_widget(note)
        box.add_widget(vocal)

        row1 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        save_btn = Button(text="ENREGISTRER")
        record_btn = Button(text="OUVRIR ENREGISTREUR")
        list_btn = Button(text="LISTE VOCAUX")
        row1.add_widget(save_btn)
        row1.add_widget(record_btn)
        row1.add_widget(list_btn)
        box.add_widget(row1)

        row2 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        play_btn = Button(text="LIRE VOCAL")
        stop_btn = Button(text="STOP LECTURE")
        delete_vocal_btn = Button(text="SUPPRIMER VOCAL")
        row2.add_widget(play_btn)
        row2.add_widget(stop_btn)
        row2.add_widget(delete_vocal_btn)
        box.add_widget(row2)

        row3 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        delete_note_btn = Button(text="SUPPRIMER NOTE")
        close_btn = Button(text="FERMER")
        row3.add_widget(delete_note_btn)
        row3.add_widget(close_btn)
        box.add_widget(row3)

        pop = Popup(title="NOTE du thème", content=box, size_hint=(0.96,0.88))

        def save(_):
            item = {
                "key": self.current_key(),
                "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "nom": name.text.strip() or "Note sans nom",
                "note": note.text.strip(),
                "vocal": vocal.text.strip(),
                "meres": self.mother_codes,
                "maisons": {str(k): v for k, v in self.h.items()},
            }

            found = False
            for i, n in enumerate(self.notes):
                if n.get("key") == item["key"]:
                    self.notes[i] = item
                    found = True
                    break

            if not found:
                self.notes.append(item)

            write_json(NOTES_FILE, self.notes)
            self.message("NOTE", "Note enregistrée.")

        def delete_note(_):
            path = vocal.text.strip()
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

            self.notes = [n for n in self.notes if n.get("key") != self.current_key()]
            write_json(NOTES_FILE, self.notes)
            pop.dismiss()
            self.message("NOTE", "Note supprimée.")

        save_btn.bind(on_release=save)
        record_btn.bind(on_release=lambda x: open_android_recorder_v109(self))
        list_btn.bind(on_release=lambda x: popup_vocal_list_v109(self, vocal))
        play_btn.bind(on_release=lambda x: self.play_vocal_v109(vocal.text))
        stop_btn.bind(on_release=lambda x: self.stop_vocal_internal_v1091())
        delete_vocal_btn.bind(on_release=lambda x: delete_vocal_v109(self, vocal))
        delete_note_btn.bind(on_release=delete_note)
        close_btn.bind(on_release=lambda x: pop.dismiss())

        pop.open()

    MoneyRoot.popup_notes_current = popup_notes_current_v1091

_geostar_v1091_patch()



# ============================================================
# GEOSTAR V10.9.2 - FIX LISTE VOCAUX NAMEERROR
# ============================================================

def _geostar_v1092_patch():

    AUDIO_EXTENSIONS_V1092 = (".aac", ".m4a", ".mp3", ".wav", ".3gp", ".ogg", ".amr")

    def scan_audio_files_v1092(self, limit=300):
        folders = [
            "/storage/emulated/0/Music/recordings",
            "/storage/emulated/0/Music/Recordings",
            "/storage/emulated/0/Recordings",
            "/storage/emulated/0/Recording",
            "/storage/emulated/0/Recorder",
            "/storage/emulated/0/Sounds",
            "/storage/emulated/0/SoundRecorder",
            "/storage/emulated/0/Music",
            "/storage/emulated/0/Download",
            "/storage/emulated/0/Downloads",
            "/storage/emulated/0/Documents",
            "/sdcard/Music/recordings",
            "/sdcard/Recordings",
            "/sdcard/Download",
        ]

        found = []
        seen = set()

        for folder in folders:
            if not os.path.exists(folder):
                continue

            try:
                for root, dirs, files in os.walk(folder):
                    depth = root.replace(folder, "").count(os.sep)
                    if depth > 4:
                        dirs[:] = []
                        continue

                    for name in files:
                        if name.lower().endswith(AUDIO_EXTENSIONS_V1092):
                            path = os.path.join(root, name)
                            if path not in seen:
                                seen.add(path)
                                found.append(path)

                        if len(found) >= limit:
                            return found
            except Exception:
                pass

        try:
            for n in self.notes:
                v = n.get("vocal", "")
                if v and v not in seen:
                    seen.add(v)
                    found.append(v)
        except Exception:
            pass

        # Les plus récents en premier si possible
        try:
            found.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
        except Exception:
            pass

        return found

    def popup_vocal_list_v1092(self, vocal_input):
        files = self.scan_audio_files_v1092()

        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))

        content.add_widget(Label(
            text=f"Vocaux trouvés : {len(files)}\nClique sur un vocal pour l'attacher à la note.",
            color=(1,1,1,1),
            size_hint=(1,None),
            height=dp(55)
        ))

        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        sv.add_widget(grid)
        content.add_widget(sv)

        if not files:
            grid.add_widget(Label(
                text="Aucun vocal trouvé.\nEnregistre d'abord avec l'application Enregistreur vocal Android.",
                color=(1,1,1,1),
                size_hint_y=None,
                height=dp(90)
            ))

        for path in files:
            short = os.path.basename(path)
            folder = os.path.dirname(path)
            txt = short + "\n" + folder

            b = Button(text=txt, font_size=dp(10), size_hint_y=None, height=dp(58))

            def choose(btn, p=path):
                vocal_input.text = p
                pop.dismiss()
                self.message(
                    "Vocal",
                    "Vocal attaché :\n" + p + "\n\nClique sur ENREGISTRER pour sauvegarder la note."
                )

            b.bind(on_release=choose)
            grid.add_widget(b)

        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        content.add_widget(close)

        pop = Popup(title="Liste des vocaux", content=content, size_hint=(0.96,0.90))
        close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    def open_android_recorder_v1092(self):
        if platform != "android":
            self.message("Micro", "Sur iPhone/Web, utilise Dictaphone puis indique le fichier.")
            return

        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            intent = Intent("android.provider.MediaStore.RECORD_SOUND")
            PythonActivity.mActivity.startActivity(intent)

            self.message(
                "Micro",
                "L'enregistreur vocal Android est ouvert.\n\n"
                "Après l'enregistrement, reviens dans GEOSTAR puis clique sur LISTE VOCAUX."
            )
        except Exception:
            self.message(
                "Micro",
                "Ouvre manuellement l'application Enregistreur vocal Android, puis reviens dans GEOSTAR et clique sur LISTE VOCAUX."
            )

    def play_vocal_v1092(self, path):
        path = path.strip()

        if not path:
            self.message("Vocal", "Aucun vocal attaché à cette note.")
            return

        if not os.path.exists(path):
            self.message("Vocal", "Fichier vocal introuvable :\n" + path)
            return

        if platform == "android":
            try:
                from jnius import autoclass

                old_player = getattr(self, "_geostar_player", None)
                if old_player is not None:
                    try:
                        old_player.stop()
                        old_player.release()
                    except Exception:
                        pass

                MediaPlayer = autoclass("android.media.MediaPlayer")
                player = MediaPlayer()
                player.setDataSource(path)
                player.prepare()
                player.start()

                self._geostar_player = player
                self.message("Vocal", "Lecture en cours.\n\n" + os.path.basename(path))
                return
            except Exception as e:
                self.message("Vocal", "Impossible de lire le vocal.\n\n" + str(e))
                return

        self.message("Vocal", "Vocal :\n" + path)

    def stop_vocal_v1092(self):
        player = getattr(self, "_geostar_player", None)

        if player is None:
            self.message("Vocal", "Aucune lecture en cours.")
            return

        try:
            player.stop()
            player.release()
        except Exception:
            pass

        self._geostar_player = None
        self.message("Vocal", "Lecture arrêtée.")

    def delete_vocal_v1092(self, vocal_input):
        path = vocal_input.text.strip()

        if not path:
            self.message("Vocal", "Aucun vocal à supprimer.")
            return

        deleted = False
        try:
            if os.path.exists(path):
                os.remove(path)
                deleted = True
        except Exception:
            deleted = False

        vocal_input.text = ""

        if deleted:
            self.message("Vocal", "Fichier vocal supprimé.\nClique sur ENREGISTRER pour sauvegarder.")
        else:
            self.message("Vocal", "Vocal retiré de la note.\nLe fichier n'a pas pu être supprimé physiquement.\nClique sur ENREGISTRER.")

    MoneyRoot.scan_audio_files_v1092 = scan_audio_files_v1092
    MoneyRoot.popup_vocal_list_v1092 = popup_vocal_list_v1092
    MoneyRoot.open_android_recorder_v1092 = open_android_recorder_v1092
    MoneyRoot.play_vocal_v1092 = play_vocal_v1092
    MoneyRoot.stop_vocal_v1092 = stop_vocal_v1092
    MoneyRoot.delete_vocal_v1092 = delete_vocal_v1092

    def popup_notes_current_v1092(self):
        existing = None
        for n in self.notes:
            if n.get("key") == self.current_key():
                existing = n
                break

        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))

        name = TextInput(
            hint_text="Nom de la note",
            multiline=False,
            text=existing.get("nom", "") if existing else ""
        )
        note = TextInput(
            hint_text="Note écrite",
            multiline=True,
            text=existing.get("note", "") if existing else ""
        )
        vocal = TextInput(
            hint_text="Mémo vocal attaché",
            multiline=False,
            text=existing.get("vocal", "") if existing else ""
        )

        box.add_widget(name)
        box.add_widget(note)
        box.add_widget(vocal)

        row1 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        save_btn = Button(text="ENREGISTRER")
        record_btn = Button(text="OUVRIR ENREGISTREUR")
        list_btn = Button(text="LISTE VOCAUX")
        row1.add_widget(save_btn)
        row1.add_widget(record_btn)
        row1.add_widget(list_btn)
        box.add_widget(row1)

        row2 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        play_btn = Button(text="LIRE VOCAL")
        stop_btn = Button(text="STOP LECTURE")
        delete_vocal_btn = Button(text="SUPPRIMER VOCAL")
        row2.add_widget(play_btn)
        row2.add_widget(stop_btn)
        row2.add_widget(delete_vocal_btn)
        box.add_widget(row2)

        row3 = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        delete_note_btn = Button(text="SUPPRIMER NOTE")
        close_btn = Button(text="FERMER")
        row3.add_widget(delete_note_btn)
        row3.add_widget(close_btn)
        box.add_widget(row3)

        pop = Popup(title="NOTE du thème", content=box, size_hint=(0.96,0.88))

        def save(_):
            item = {
                "key": self.current_key(),
                "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "nom": name.text.strip() or "Note sans nom",
                "note": note.text.strip(),
                "vocal": vocal.text.strip(),
                "meres": self.mother_codes,
                "maisons": {str(k): v for k, v in self.h.items()},
            }

            found = False
            for i, n in enumerate(self.notes):
                if n.get("key") == item["key"]:
                    self.notes[i] = item
                    found = True
                    break

            if not found:
                self.notes.append(item)

            write_json(NOTES_FILE, self.notes)
            self.message("NOTE", "Note enregistrée.")

        def delete_note(_):
            path = vocal.text.strip()
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

            self.notes = [n for n in self.notes if n.get("key") != self.current_key()]
            write_json(NOTES_FILE, self.notes)
            pop.dismiss()
            self.message("NOTE", "Note supprimée.")

        save_btn.bind(on_release=save)
        record_btn.bind(on_release=lambda x: self.open_android_recorder_v1092())
        list_btn.bind(on_release=lambda x: self.popup_vocal_list_v1092(vocal))
        play_btn.bind(on_release=lambda x: self.play_vocal_v1092(vocal.text))
        stop_btn.bind(on_release=lambda x: self.stop_vocal_v1092())
        delete_vocal_btn.bind(on_release=lambda x: self.delete_vocal_v1092(vocal))
        delete_note_btn.bind(on_release=delete_note)
        close_btn.bind(on_release=lambda x: pop.dismiss())

        pop.open()

    MoneyRoot.popup_notes_current = popup_notes_current_v1092

_geostar_v1092_patch()



# ============================================================
# GEOSTAR V10.9.3 - FERMETURE COMPLETE DES FENETRES SOLUTIONS
# ============================================================
# Corrige :
# Quand on clique sur une solution, la liste se fermait,
# mais le menu principal SOLUTIONS restait ouvert derrière.
# Maintenant GEOSTAR ferme toutes les fenêtres solutions.
# ============================================================

def _geostar_v1093_patch():

    def register_solution_popup(self, pop):
        if not hasattr(self, "_solution_popups"):
            self._solution_popups = []
        self._solution_popups.append(pop)

    def close_all_solution_popups(self):
        if not hasattr(self, "_solution_popups"):
            self._solution_popups = []
            return

        for p in list(self._solution_popups):
            try:
                p.dismiss()
            except Exception:
                pass

        self._solution_popups = []

    MoneyRoot.register_solution_popup = register_solution_popup
    MoneyRoot.close_all_solution_popups = close_all_solution_popups

    old_popup_solutions = MoneyRoot.popup_solutions
    old_open_solution_window = MoneyRoot.open_solution_window
    old_apply_solution_from_list = MoneyRoot.apply_solution_from_list

    def popup_solutions_v1093(self):
        from kivy.uix.togglebutton import ToggleButton as TBs
        self.close_all_solution_popups()
        import os as _os
        # Dossier de sauvegarde compatible Android
        try:
            from kivy.utils import platform as _plat
            if _plat == "android":
                from android.storage import app_storage_path as _asp
                _base = _asp()
            else:
                _base = _os.path.expanduser("~")
        except Exception:
            _base = _os.path.expanduser("~")
        SAVED_FILE = _os.path.join(_base, "geostar_saved_combos.json")

        # Layout principal avec 2 onglets
        main = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(6))

        # Barre onglets
        tab_bar = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(40), spacing=dp(4))
        t_search = TBs(text="RECHERCHES", group="sol_tabs", state="down", size_hint=(0.5,1))
        t_saved  = TBs(text="SAUVEGARDE", group="sol_tabs", size_hint=(0.5,1))
        tab_bar.add_widget(t_search); tab_bar.add_widget(t_saved)
        main.add_widget(tab_bar)

        zone = BoxLayout(size_hint=(1,1))
        main.add_widget(zone)

        # ---- Contenu onglet RECHERCHES ----
        sv_search = ScrollView()
        box = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))

        def open_predef_menu():
            sub = BoxLayout(orientation="vertical", spacing=dp(5), padding=dp(8))
            sub.add_widget(Label(text="Solutions prédéfinies", color=(0.6,0.8,1,1), size_hint=(1,None), height=dp(28), font_size=dp(11)))
            sv_sub = ScrollView()
            grid_sub = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
            grid_sub.bind(minimum_height=grid_sub.setter("height"))
            options = [
                ("5-10-16 toutes", [5,10,16], False),
                ("5-10-16 rares 7-13/7-15", [5,10,16], True),
                ("3-10-15 toutes", [3,10,15], False),
                ("10-11-15", [10,11,15], False),
                ("3-11-15", [3,11,15], False),
                ("2-3-13", [2,3,13], False),
                ("10-13-15", [10,13,15], False),
                ("2-10-15", [2,10,15], False),
            ]
            for name, pos, rare in options:
                b = Button(text=name, size_hint=(1,None), height=dp(42))
                b.bind(on_release=lambda btn, n=name, p=pos, r=rare: self.open_solution_window(n, p, r))
                grid_sub.add_widget(b)
            sv_sub.add_widget(grid_sub)
            sub.add_widget(sv_sub)
            b_close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
            sub.add_widget(b_close)
            pop_sub = Popup(title="Solutions predefinies", content=sub, size_hint=(0.92,0.75))
            b_close.bind(on_release=lambda x: pop_sub.dismiss())
            self.register_solution_popup(pop_sub)
            pop_sub.open()

        btn_predef = Button(
            text="SOLUTIONS PRÉDÉFINIES",
            size_hint=(1,None), height=dp(42),
            background_color=(0.2,0.35,0.55,1)
        )
        btn_predef.bind(on_release=lambda x: open_predef_menu())
        box.add_widget(btn_predef)

        # Recherche non stricte personnalisée
        def open_non_stricte_menu():
            sub = BoxLayout(orientation="vertical", spacing=dp(5), padding=dp(8))
            sub.add_widget(Label(
                text="Choisis une figure et des maisons\nMode NON STRICTE : la figure peut apparaître ailleurs aussi",
                color=(0.6,0.85,1,1), size_hint=(1,None), height=dp(50),
                font_size=dp(11), halign="center"
            ))
            # Bouton vers la recherche par figure (qui a déjà strict/non strict)
            b_fig = Button(
                text="RECHERCHE PAR FIGURE (Strict / Non Strict)",
                size_hint=(1,None), height=dp(48),
                background_color=(0.1,0.4,0.65,1)
            )
            def go_fig(_):
                pop.dismiss()
                if hasattr(self, "popup_search_by_figure"):
                    self.popup_search_by_figure()
                elif hasattr(self, "popup_figure_search"):
                    self.popup_figure_search()
            b_fig.bind(on_release=go_fig)
            sub.add_widget(b_fig)
            b_close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
            sub.add_widget(b_close)
            pop_ns = Popup(title="Recherche Non Stricte", content=sub, size_hint=(0.92,0.5))
            b_close.bind(on_release=lambda x: pop_ns.dismiss())
            self.register_solution_popup(pop_ns)
            pop_ns.open()

        btn_ns = Button(
            text="+ RECHERCHE NON STRICTE / STRICTE",
            size_hint=(1,None), height=dp(42),
            background_color=(0.1,0.35,0.6,1)
        )
        btn_ns.bind(on_release=lambda x: open_non_stricte_menu())
        box.add_widget(btn_ns)

        add = Button(text="+ AJOUTER RECHERCHE PERSONNALISÉE", size_hint=(1,None), height=dp(40), background_color=(0.2,0.4,0.6,1))
        add.bind(on_release=lambda x: self.popup_add_custom_search())
        box.add_widget(add)

        rep_btn = Button(text="+ RECHERCHE PAR NOMBRE DE RÉPÉTITIONS", size_hint=(1,None), height=dp(40), background_color=(0.2,0.4,0.6,1))
        rep_btn.bind(on_release=lambda x: self.popup_repetition_count())
        box.add_widget(rep_btn)

        if self.custom_searches:
            box.add_widget(Label(text="Recherches perso :", color=(0.6,0.9,0.7,1), size_hint=(1,None), height=dp(24)))
            for item in self.custom_searches:
                name = item.get("name", "Sans nom")
                pos = sorted(set(item.get("positions", [])))
                b = Button(text=name + " : " + str(pos), size_hint=(1,None), height=dp(34))
                b.bind(on_release=lambda btn, it=item: self.open_solution_window(it.get("name","Perso"), sorted(set(it.get("positions",[]))), False))
                box.add_widget(b)

        repeat_searches = self.get_repeat_searches() if hasattr(self, "get_repeat_searches") else []
        if repeat_searches:
            box.add_widget(Label(text="Recherches répétitions :", color=(0.6,0.9,0.7,1), size_hint=(1,None), height=dp(24)))
            for item in repeat_searches:
                name = item.get("name", "Répétition")
                count = item.get("count")
                b = Button(text=name + " | x" + str(count), size_hint=(1,None), height=dp(34))
                if hasattr(self, "open_repetition_results_v105"):
                    b.bind(on_release=lambda btn, it=item: self.open_repetition_results_v105(it.get("count"), it.get("target")))
                elif hasattr(self, "open_repetition_results"):
                    b.bind(on_release=lambda btn, it=item: self.open_repetition_results(it.get("count"), it.get("target")))
                box.add_widget(b)

        manage = Button(text="SUPPRIMER RECHERCHE PERSO", size_hint=(1,None), height=dp(36), background_color=(0.4,0.15,0.15,1))
        manage.bind(on_release=lambda x: self.popup_delete_custom_search())
        box.add_widget(manage)
        manage_rep = Button(text="SUPPRIMER RECHERCHE RÉPÉTITIONS", size_hint=(1,None), height=dp(36), background_color=(0.4,0.15,0.15,1))
        if hasattr(self, "popup_delete_repeat_search"):
            manage_rep.bind(on_release=lambda x: self.popup_delete_repeat_search())
        box.add_widget(manage_rep)

        sv_search.add_widget(box)

        # ---- Contenu onglet COMBINAISONS ----
        sv_saved = ScrollView()
        grid_saved = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        grid_saved.bind(minimum_height=grid_saved.setter("height"))
        sv_saved.add_widget(grid_saved)

        def refresh_saved():
            grid_saved.clear_widgets()
            saved = read_json(SAVED_FILE, [])
            if not saved:
                grid_saved.add_widget(Label(
                    text="Aucune combinaison enregistree.\nUtilise SAVE dans une recherche.",
                    color=(0.6,0.6,0.6,1), size_hint_y=None, height=dp(70),
                    halign="center"
                ))
                return
            # Bouton tout supprimer
            b_del_all = Button(
                text="SUPPRIMER TOUTES LES COMBINAISONS",
                size_hint=(1,None), height=dp(40),
                background_color=(0.6,0.1,0.1,1)
            )
            def del_all(_):
                write_json(SAVED_FILE, [])
                refresh_saved()
            b_del_all.bind(on_release=del_all)
            grid_saved.add_widget(b_del_all)
            for idx, item in enumerate(saved, 1):
                fig_n = item.get("figure_nom","?")
                pos_str = item.get("positions_str","")
                m1,m2,m3,m4 = item.get("m1","?"),item.get("m2","?"),item.get("m3","?"),item.get("m4","?")
                mode = item.get("mode","")
                txt = str(idx) + ". " + fig_n + " " + pos_str + " [" + mode + "]\n    M1=" + m1 + " M2=" + m2 + " M3=" + m3 + " M4=" + m4
                row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(3))
                b = Button(text=txt, font_size=dp(10), size_hint=(0.75,1), halign="left")
                b_del = Button(text="X", size_hint=(0.12,1), background_color=(0.7,0.1,0.1,1))
                b_app = Button(text="GO", size_hint=(0.13,1), background_color=(0.1,0.4,0.7,1))
                def on_app(btn, it=item):
                    pop.dismiss()
                    sol = {"m1":it["m1"],"m2":it["m2"],"m3":it["m3"],"m4":it["m4"],
                           "figure":it.get("figure_bits","1111"),"positions":[],"secondary":""}
                    self.apply_solution(sol)
                def on_del(btn, it=item):
                    sv2 = read_json(SAVED_FILE, [])
                    sv2 = [x for x in sv2 if x != it]
                    write_json(SAVED_FILE, sv2)
                    refresh_saved()
                b.bind(on_release=on_app)
                b_app.bind(on_release=on_app)
                b_del.bind(on_release=on_del)
                row.add_widget(b); row.add_widget(b_app); row.add_widget(b_del)
                grid_saved.add_widget(row)

        def switch_tab(btn):
            zone.clear_widgets()
            if t_search.state == "down":
                zone.add_widget(sv_search)
            else:
                refresh_saved()
                zone.add_widget(sv_saved)

        t_search.bind(on_press=switch_tab)
        t_saved.bind(on_press=switch_tab)
        zone.add_widget(sv_search)  # Onglet par defaut

        pop = Popup(title="SOLUTIONS", content=main, size_hint=(0.95,0.95))
        self.register_solution_popup(pop)
        pop.open()

    MoneyRoot.popup_solutions = popup_solutions_v1093

    def open_solution_window_v1093(self, title, positions, rare):
        import os as _os
        try:
            from kivy.utils import platform as _plat
            if _plat == "android":
                from android.storage import app_storage_path as _asp
                _base = _asp()
            else:
                _base = _os.path.expanduser("~")
        except Exception:
            _base = _os.path.expanduser("~")
        SAVED_FILE = _os.path.join(_base, "geostar_saved_combos.json")
        positions = sorted(set([int(p) for p in positions]))
        current_sol = [None]

        content = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(4))
        header = Label(
            text=title + "\nCalcul en cours...",
            color=(1,1,1,1), size_hint=(1,None), height=dp(55)
        )
        content.add_widget(header)

        sv = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(3), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        sv.add_widget(grid)
        content.add_widget(sv)

        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        content.add_widget(close)

        pop = Popup(title=title, content=content, size_hint=(0.98,0.94))
        self.register_solution_popup(pop)
        close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

        def save_sol(sol):
            saved = read_json(SAVED_FILE, [])
            fig = data_fig(sol["figure"])["africain"]
            pos_str = "M" + "M".join(str(p) for p in sol.get("positions", positions))
            entry = {
                "figure_nom": fig,
                "figure_bits": sol["figure"],
                "positions_str": pos_str,
                "mode": "S" if rare else "NS",
                "m1": sol["m1"], "m2": sol["m2"],
                "m3": sol["m3"], "m4": sol["m4"]
            }
            if entry not in saved:
                saved.append(entry)
                write_json(SAVED_FILE, saved)
                self.message("Enregistre", fig + " " + pos_str + " sauvegarde!")
            else:
                self.message("Deja enregistre", fig + " " + pos_str + " existe deja.")

        def fill(dt):
            try:
                sols = self.get_solutions_cached(positions, rare)
                header.text = title + "\nTotal : " + str(len(sols)) + " solution(s)"

                if not sols:
                    grid.add_widget(Label(
                        text="Aucune solution trouvee.",
                        color=(1,0.4,0.4,1), size_hint_y=None, height=dp(60)
                    ))
                    return

                for idx, sol in enumerate(sols, 1):
                    fig = data_fig(sol["figure"])["africain"]
                    sec = (" | " + sol["secondary"]) if sol.get("secondary") else ""
                    txt = (str(idx) + ". " + fig + " " + str(sol["positions"]) +
                           "\nM1=" + sol["m1"] + " M2=" + sol["m2"] +
                           " M3=" + sol["m3"] + " M4=" + sol["m4"] + sec)

                    row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(3))

                    b = Button(text=txt, font_size=dp(10), size_hint=(0.78,1), halign="left")
                    b_save = Button(text="SAVE", size_hint=(0.22,1),
                                   background_color=(0.1,0.5,0.25,1), font_size=dp(11))

                    def on_click(btn, s=sol, sl=sols):
                        self.apply_solution_from_list_v1093(s, sl)
                    def on_save_click(btn, s=sol):
                        save_sol(s)

                    b.bind(on_release=on_click)
                    b_save.bind(on_release=on_save_click)
                    row.add_widget(b)
                    row.add_widget(b_save)
                    grid.add_widget(row)

            except Exception as e:
                header.text = "Erreur"
                grid.add_widget(Label(text=str(e), color=(1,1,1,1), size_hint_y=None, height=dp(80)))

        Clock.schedule_once(fill, 0.1)

    MoneyRoot.open_solution_window = open_solution_window_v1093

    def apply_solution_from_list_v1093(self, sol, sol_list, pop=None):
        # Ferme menu principal + liste.
        self.close_all_solution_popups()

        self.active_solutions = sol_list
        try:
            self.active_solution_index = sol_list.index(sol)
        except ValueError:
            self.active_solution_index = 0

        self.mother_codes = [sol["m1"], sol["m2"], sol["m3"], sol["m4"]]
        self.afficher_theme(developper_theme(*self.mother_codes))

    MoneyRoot.apply_solution_from_list_v1093 = apply_solution_from_list_v1093
    MoneyRoot.apply_solution_from_list = apply_solution_from_list_v1093
    MoneyRoot.apply_solution_from_list_v105 = apply_solution_from_list_v1093

    # Correction aussi pour la recherche par répétitions, si elle existe.
    if hasattr(MoneyRoot, "open_repetition_results_v105"):
        old_open_rep = MoneyRoot.open_repetition_results_v105

        def open_repetition_results_v1093(self, count, target_bits=None):
            old_open_rep(self, count, target_bits)
            # La fenêtre ouverte par l'ancien code n'est pas toujours enregistrée.
            # Mais les boutons internes utilisent maintenant apply_solution_from_list,
            # donc après sélection toutes les popups solutions seront fermées.

        MoneyRoot.open_repetition_results_v105 = open_repetition_results_v1093

_geostar_v1093_patch()



# ============================================================
# GEOSTAR V11.6 PROPRE
# ============================================================
# Reconstruction propre depuis base stable :
# - Photos stables dans les figures
# - Galerie rapide paginée
# - Nuances par figure répétée
# - Terre marron clair
# - Impression/export PNG dans Pictures/GEOSTAR
# - Aucun patch redraw_photo_v115
# ============================================================

IMAGE_FILE = "geostar_images_figures.json"
IMAGE_CACHE_FILE = "geostar_cache_images.json"
PRINT_IMAGE_FILE = "geostar_theme_export.png"

def _geostar_v116_clean_patch():

    try:
        from kivy.core.image import Image as CoreImage
    except Exception:
        CoreImage = None

    try:
        from kivy.uix.image import Image as KivyImage
    except Exception:
        KivyImage = None

    IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

    # ---------------- COULEURS NUANCÉES ----------------

    def color_for_bits_clean(bits):
        if bits not in BIN_TO_CODE:
            return (0.68, 0.38, 1.0, 1)

        code = BIN_TO_CODE[bits]

        colors = {
            # FEU rouges distincts
            "1121": (1.00, 0.08, 0.05, 1),  # Sedjou
            "1222": (1.00, 0.30, 0.20, 1),  # Adama
            "1122": (0.86, 0.03, 0.03, 1),  # Kalalao
            "1212": (1.00, 0.52, 0.42, 1),  # Inzan

            # VENT jaunes/or
            "2111": (1.00, 0.93, 0.10, 1),
            "2122": (0.95, 0.75, 0.05, 1),
            "2112": (1.00, 0.83, 0.25, 1),
            "2121": (0.82, 0.70, 0.12, 1),

            # EAU bleus
            "1111": (0.10, 0.38, 1.00, 1),
            "2222": (0.22, 0.60, 1.00, 1),
            "1112": (0.08, 0.25, 0.88, 1),
            "2212": (0.45, 0.75, 1.00, 1),

            # TERRE marrons clairs
            "2211": (0.74, 0.48, 0.24, 1),
            "1221": (0.86, 0.60, 0.32, 1),
            "1211": (0.66, 0.43, 0.22, 1),
            "2221": (0.92, 0.70, 0.42, 1),
        }
        return colors.get(code, (1,1,1,1))

    globals()["color_for_bits_v116"] = color_for_bits_clean
    globals()["color_for_bits_v106"] = color_for_bits_clean

    # ---------------- IMAGES PAR MAISON ----------------

    def load_figure_images(self):
        if not hasattr(self, "figure_images"):
            self.figure_images = read_json(IMAGE_FILE, {})
        return self.figure_images

    def save_figure_images(self):
        write_json(IMAGE_FILE, self.load_figure_images_v116())

    def theme_key(self):
        try:
            return self.current_key()
        except Exception:
            try:
                return "-".join(self.mother_codes)
            except Exception:
                return "theme_default"

    def get_image(self, maison):
        data = self.load_figure_images_v116()
        return data.get(self.theme_key_v116(), {}).get(str(maison), "")

    def set_image(self, maison, path):
        data = self.load_figure_images_v116()
        key = self.theme_key_v116()
        if key not in data:
            data[key] = {}
        data[key][str(maison)] = path
        self.save_figure_images_v116()

    def delete_image(self, maison):
        data = self.load_figure_images_v116()
        key = self.theme_key_v116()
        if key in data and str(maison) in data[key]:
            del data[key][str(maison)]
        self.save_figure_images_v116()

    MoneyRoot.load_figure_images_v116 = load_figure_images
    MoneyRoot.save_figure_images_v116 = save_figure_images
    MoneyRoot.theme_key_v116 = theme_key
    MoneyRoot.get_image_for_maison_v116 = get_image
    MoneyRoot.set_image_for_maison_v116 = set_image
    MoneyRoot.delete_image_for_maison_v116 = delete_image

    # ---------------- SCAN IMAGE RAPIDE ----------------

    def scan_image_files_v116(self, limit=500, force_refresh=False):
        if not force_refresh:
            cached = read_json(IMAGE_CACHE_FILE, [])
            valid = []
            for p in cached:
                try:
                    if os.path.exists(p) and "/.thumbnails/" not in p and "/.thumbnail/" not in p:
                        valid.append(p)
                except Exception:
                    pass
            if valid:
                return valid[:limit]

        folders = [
            "/storage/emulated/0/DCIM",
            "/storage/emulated/0/Pictures",
            "/storage/emulated/0/Download",
            "/storage/emulated/0/Downloads",
            "/storage/emulated/0/Documents",
            "/storage/emulated/0/Images",
            "/storage/emulated/0/WhatsApp/Media/WhatsApp Images",
            "/sdcard/DCIM",
            "/sdcard/Pictures",
            "/sdcard/Download",
            "/sdcard/Downloads",
        ]

        found = []
        seen = set()

        for folder in folders:
            if not os.path.exists(folder):
                continue

            try:
                for root, dirs, files in os.walk(folder):
                    dirs[:] = [d for d in dirs if d.lower() not in [".thumbnails", ".thumbnail", "thumbnails"]]
                    if "/.thumbnails/" in root or "/.thumbnail/" in root:
                        continue

                    depth = root.replace(folder, "").count(os.sep)
                    if depth > 3:
                        dirs[:] = []
                        continue

                    for name in files:
                        if name.lower().endswith(IMAGE_EXTENSIONS):
                            path = os.path.join(root, name)
                            if path not in seen:
                                seen.add(path)
                                found.append(path)

                        if len(found) >= limit:
                            break
                    if len(found) >= limit:
                        break
            except Exception:
                pass

        try:
            found.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
        except Exception:
            pass

        write_json(IMAGE_CACHE_FILE, found)
        return found

    MoneyRoot.scan_image_files_v116 = scan_image_files_v116

    # ---------------- CARTE STABLE PHOTO ----------------

    class GeoStarFigureCard(Widget):
        def __init__(self, maison=1, bits="0000", root=None, repeated=False, image_path="", **kwargs):
            super().__init__(**kwargs)
            self.maison = maison
            self.bits = bits
            self.root = root
            self.repeated = repeated
            self.image_path = image_path or ""
            self.drag_enabled = False
            self.dx = 0
            self.dy = 0
            self.long_event = None
            self.bind(pos=self.redraw, size=self.redraw)

        def set_bits(self, bits):
            self.bits = bits
            self.redraw()

        def enable_drag(self, dt):
            self.drag_enabled = True
            self.pos_hint = {}
            self.size_hint = (None, None)
            self.size = (self.width, self.height)
            if self.root:
                self.root.info.text = "Déplacement activé : glisse la figure."

        def on_touch_down(self, touch):
            if self.collide_point(*touch.pos):
                self.drag_enabled = False
                self.dx = self.x - touch.x
                self.dy = self.y - touch.y
                touch.grab(self)
                self.long_event = Clock.schedule_once(self.enable_drag, 3.0)
                return True
            return False

        def on_touch_move(self, touch):
            if touch.grab_current is self:
                if self.drag_enabled:
                    self.x = touch.x + self.dx
                    self.y = touch.y + self.dy
                return True
            return False

        def on_touch_up(self, touch):
            if touch.grab_current is self:
                touch.ungrab(self)
                if self.long_event:
                    self.long_event.cancel()
                    self.long_event = None
                if not self.drag_enabled and self.root:
                    self.root.popup_edit_figure(self.maison)
                self.drag_enabled = False
                return True
            return False

        def draw_symbol(self, cx, cy, dot_r, sep, symbol):
            if symbol == "1":
                Ellipse(pos=(cx-dot_r, cy-dot_r), size=(dot_r*2, dot_r*2))
            elif symbol == "0":
                Ellipse(pos=(cx-sep-dot_r, cy-dot_r), size=(dot_r*2, dot_r*2))
                Ellipse(pos=(cx+sep-dot_r, cy-dot_r), size=(dot_r*2, dot_r*2))
            elif symbol == "Q":
                Line(circle=(cx, cy, dot_r*1.45), width=2)
                Ellipse(pos=(cx-dot_r*0.35, cy-dot_r*0.35), size=(dot_r*0.7, dot_r*0.7))
            else:
                Ellipse(pos=(cx-dot_r, cy-dot_r), size=(dot_r*2, dot_r*2))

        def redraw(self, *args):
            self.canvas.clear()
            x, y = self.pos
            w, h = self.size
            if w <= 5 or h <= 5:
                return

            with self.canvas:
                drew_image = False

                if self.image_path and os.path.exists(self.image_path) and CoreImage is not None:
                    try:
                        tex = CoreImage(self.image_path).texture
                        Color(1, 1, 1, 1)
                        Rectangle(pos=(x, y), size=(w, h), texture=tex)
                        drew_image = True
                    except Exception:
                        drew_image = False

                if not drew_image:
                    if self.repeated:
                        Color(*color_for_bits_clean(self.bits))
                    else:
                        Color(1, 1, 1, 1)
                    RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(5)])
                else:
                    Color(1, 1, 1, 0.20)
                    RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(5)])

                # Points
                Color(0, 0, 0, 1)
                top = h * 0.17
                bottom = h * 0.13
                row_gap = (h - top - bottom) / 4.0
                dot_r = min(w, h) * 0.055
                sep = w * 0.18

                for i, b in enumerate(self.bits):
                    cy = y + h - top - (i+0.5)*row_gap
                    cx = x + w/2
                    self.draw_symbol(cx, cy, dot_r, sep, b)

                Color(0, 0, 0, 0.35)
                Line(rounded_rectangle=(x, y, w, h, dp(5)), width=1)

    globals()["GeoStarFigureCard"] = GeoStarFigureCard

    # ---------------- ADD_CARD STABLE ----------------

    def add_card_v116(self, maison, bits, rx, ry, rw, rh, repeated=False, *args, **kwargs):
        card = GeoStarFigureCard(
            maison=maison,
            bits=bits,
            root=self,
            repeated=repeated,
            image_path=self.get_image_for_maison_v116(maison),
            size_hint=(rw, rh),
            pos_hint={"x": rx, "y": ry}
        )

        label = Label(
            text=f"[b]M{maison}[/b]",
            markup=True,
            color=(1, 0.86, 0.05, 1),
            font_size=dp(14),
            size_hint=(rw, None),
            height=dp(22),
            pos_hint={"x": rx, "y": ry + rh}
        )

        self.board.add_widget(label)
        self.board.add_widget(card)
        self.cards[maison] = card
        self.labels[maison] = label

    MoneyRoot.add_card = add_card_v116

    # ---------------- GALERIE PAGINÉE ----------------

    def popup_image_list_v116(self, maison):
        files = self.scan_image_files_v116(limit=500, force_refresh=False)
        state = {"page": 0, "per_page": 24, "files": files}

        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))

        top = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(50), spacing=dp(5))
        title_lab = Label(text="", color=(1,1,1,1), size_hint=(0.45,1))
        refresh_btn = Button(text="RAFRAÎCHIR", size_hint=(0.28,1))
        reset_btn = Button(text="RESET CACHE", size_hint=(0.27,1))
        top.add_widget(title_lab)
        top.add_widget(refresh_btn)
        top.add_widget(reset_btn)
        content.add_widget(top)

        sv = ScrollView()
        grid = GridLayout(cols=4, spacing=dp(6), padding=dp(4), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        sv.add_widget(grid)
        content.add_widget(sv)

        nav = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        prev_btn = Button(text="◀ PRÉCÉDENT")
        next_btn = Button(text="SUIVANT ▶")
        nav.add_widget(prev_btn)
        nav.add_widget(next_btn)
        content.add_widget(nav)

        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        content.add_widget(close)

        pop = Popup(title=f"Choisir image pour M{maison}", content=content, size_hint=(0.96,0.90))

        def choose(path):
            self.set_image_for_maison_v116(maison, path)
            pop.dismiss()
            self.afficher_theme(self.h)
            self.message("Image", f"Image ajoutée à M{maison}.")

        def render():
            grid.clear_widgets()
            total = len(state["files"])
            per = state["per_page"]
            pages = max(1, (total + per - 1)//per)
            state["page"] = max(0, min(state["page"], pages-1))
            page = state["page"]
            title_lab.text = f"Images {total} | Page {page+1}/{pages}"

            current = state["files"][page*per:min((page+1)*per, total)]

            if not current:
                grid.cols = 1
                grid.add_widget(Label(
                    text="Aucune image trouvée.\nMets une photo dans DCIM, Pictures ou Download.",
                    color=(1,1,1,1),
                    size_hint_y=None,
                    height=dp(90)
                ))
                return

            grid.cols = 4

            for path in current:
                cell = FloatLayout(size_hint_y=None, height=dp(125))
                if KivyImage is not None:
                    try:
                        img = KivyImage(source=path, allow_stretch=True, keep_ratio=True, size_hint=(1,1), pos_hint={"x":0,"y":0})
                        cell.add_widget(img)
                    except Exception:
                        cell.add_widget(Label(text="IMG", color=(1,1,1,1)))
                else:
                    cell.add_widget(Label(text="IMG", color=(1,1,1,1)))

                overlay = Button(text="", background_color=(0,0,0,0), size_hint=(1,1), pos_hint={"x":0,"y":0})
                overlay.bind(on_release=lambda x, p=path: choose(p))
                cell.add_widget(overlay)
                grid.add_widget(cell)

        def refresh(_):
            state["files"] = self.scan_image_files_v116(limit=500, force_refresh=True)
            state["page"] = 0
            render()

        def reset(_):
            write_json(IMAGE_CACHE_FILE, [])
            state["files"] = self.scan_image_files_v116(limit=500, force_refresh=True)
            state["page"] = 0
            render()

        prev_btn.bind(on_release=lambda x: (state.__setitem__("page", state["page"]-1), render()))
        next_btn.bind(on_release=lambda x: (state.__setitem__("page", state["page"]+1), render()))
        refresh_btn.bind(on_release=refresh)
        reset_btn.bind(on_release=reset)
        close.bind(on_release=lambda x: pop.dismiss())

        render()
        pop.open()

    MoneyRoot.popup_image_list_v116 = popup_image_list_v116

    # ---------------- EDIT FIGURE ----------------

    def popup_edit_figure_v116(self, maison):
        bits = self.h[maison]
        d = data_fig(bits)
        current_img = self.get_image_for_maison_v116(maison)

        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        box.add_widget(Label(
            text=f"Maison {maison}\n{d['africain']} / {d['occidental']}\nImage : {'oui' if current_img else 'non'}",
            color=(1,1,1,1),
            size_hint=(1,None),
            height=dp(85)
        ))

        img_row = BoxLayout(orientation="horizontal", size_hint=(1,None), height=dp(45), spacing=dp(5))
        add_img_btn = Button(text="AJOUTER IMAGE")
        del_img_btn = Button(text="SUPPRIMER IMAGE")
        img_row.add_widget(add_img_btn)
        img_row.add_widget(del_img_btn)
        box.add_widget(img_row)

        box.add_widget(Label(text="Modifier les points :", color=(1,1,1,1), size_hint=(1,None), height=dp(25)))

        grid = GridLayout(cols=3, spacing=dp(4), size_hint=(1,None), height=dp(170))
        box.add_widget(grid)

        def mk(line, sym, label):
            b = Button(text=f"L{line+1}\n{label}")
            def act(_):
                self.apply_symbol(maison, line, sym)
                pop.dismiss()
            b.bind(on_release=act)
            return b

        for line in range(4):
            grid.add_widget(mk(line, "1", "1 point"))
            grid.add_widget(mk(line, "0", "2 points"))
            grid.add_widget(mk(line, "Q", "Q"))

        close = Button(text="FERMER", size_hint=(1,None), height=dp(42))
        box.add_widget(close)

        pop = Popup(title=f"Modifier M{maison}", content=box, size_hint=(0.92,0.82))

        add_img_btn.bind(on_release=lambda x: (pop.dismiss(), self.popup_image_list_v116(maison)))
        del_img_btn.bind(on_release=lambda x: (self.delete_image_for_maison_v116(maison), pop.dismiss(), self.afficher_theme(self.h), self.message("Image", f"Image supprimée de M{maison}.")))
        close.bind(on_release=lambda x: pop.dismiss())

        pop.open()

    MoneyRoot.popup_edit_figure = popup_edit_figure_v116

    # ---------------- IMPRESSION PNG ----------------

    def export_theme_png_v116(self):
        # CORRIGE V11.6.1 : on ecrit dans le dossier prive de l'app
        # (toujours accessible, pas de probleme de permission)
        if platform == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                ctx = PythonActivity.mActivity.getApplicationContext()
                out_dir = ctx.getCacheDir().getAbsolutePath()
            except Exception:
                out_dir = os.path.abspath(".")
        else:
            out_dir = os.path.abspath(".")

        try:
            if not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, "geostar_theme_export.png")
        except Exception:
            path = os.path.abspath("geostar_theme_export.png")

        try:
            self.board.export_to_png(path)
            return path
        except Exception:
            try:
                self.export_to_png(path)
                return path
            except Exception as e:
                self.message("Impression", "Impossible de créer l'image.\n\n" + str(e))
                return ""

    def print_theme_v116(self):
        # CORRIGE V11.6.1 : passage par MediaStore + URI content://
        # au lieu de file:// (bloque par Android 7+)
        path = self.export_theme_png_v116()
        if not path:
            return

        if platform != "android":
            self.message("Impression", "Image créée :\n" + path)
            return

        try:
            from jnius import autoclass, cast

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()
            resolver = context.getContentResolver()

            ContentValues = autoclass("android.content.ContentValues")
            MediaStoreImages = autoclass("android.provider.MediaStore$Images$Media")
            BitmapFactory = autoclass("android.graphics.BitmapFactory")
            CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
            Intent = autoclass("android.content.Intent")

            filename = "geostar_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"

            values = ContentValues()
            values.put("_display_name", filename)
            values.put("mime_type", "image/png")
            values.put("title", "GEOSTAR Theme")

            uri = resolver.insert(MediaStoreImages.EXTERNAL_CONTENT_URI, values)
            if uri is None:
                self.message("Impression", "Échec MediaStore.\nImage locale :\n" + path)
                return

            out_stream = resolver.openOutputStream(uri)
            bmp = BitmapFactory.decodeFile(path)
            if bmp is None:
                out_stream.close()
                self.message("Impression", "PNG illisible :\n" + path)
                return
            bmp.compress(CompressFormat.PNG, 100, out_stream)
            out_stream.flush()
            out_stream.close()

            intent = Intent(Intent.ACTION_SEND)
            intent.setType("image/png")
            intent.putExtra(Intent.EXTRA_STREAM, cast("android.os.Parcelable", uri))
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

            chooser = Intent.createChooser(intent, "Imprimer ou partager GEOSTAR")
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            activity.startActivity(chooser)

        except Exception as e:
            self.message(
                "Impression",
                "Erreur de partage.\nImage locale :\n" + path + "\n\nDétail : " + str(e)
            )

    MoneyRoot.export_theme_png_v116 = export_theme_png_v116
    MoneyRoot.print_theme_v112 = print_theme_v116
    MoneyRoot.print_theme_v113 = print_theme_v116
    MoneyRoot.print_theme_v114 = print_theme_v116
    MoneyRoot.print_theme_v115 = print_theme_v116
    MoneyRoot.print_theme_v116 = print_theme_v116

    # Si bouton IMPRIMER déjà créé par ancienne version, il pointera souvent vers print_theme_v112/113.
    # Ici toutes les routes pointent vers V11.6.

_geostar_v116_clean_patch()



# ============================================================
# PATCH GEOSTAR COMPLET — COMMUNAUTE + FERMETURE SOLUTIONS
# ============================================================

def _geostar_comm_solution_patch():
    import json, urllib.request, ssl
    from datetime import datetime
    from kivy.uix.popup import Popup
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.textinput import TextInput
    from kivy.metrics import dp

    SUPABASE_URL = "https://kvgjghvcptryghggzuui.supabase.co"
    SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt2Z2pnaHZjcHRyeWdoZ2d6dXVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3MDkxMzcsImV4cCI6MjA5NTI4NTEzN30.IzYhPAOUv50RmCVTe8KUaM2F4efyewgmxj-D9QVVjMU"

    def _ssl_ctx():
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        except Exception:
            return None

    def envoyer_note_communaute(self, auteur, texte, langue="fr"):
        theme_key = "-".join(getattr(self, "mother_codes", ["?", "?", "?", "?"]))
        payload = {
            "theme_key": theme_key,
            "auteur": auteur or "Anonyme",
            "code_licence": "",
            "langue": langue,
            "texte": texte,
            "audio_url": "",
            "statut": "attente",
            "date_soumission": datetime.now().isoformat()
        }
        req = urllib.request.Request(
            SUPABASE_URL + "/rest/v1/notes_communaute",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": "Bearer " + SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
                "User-Agent": "GEOSTAR-Community/1.0"
            }
        )
        try:
            ctx = _ssl_ctx()
            if ctx:
                urllib.request.urlopen(req, timeout=15, context=ctx).read()
            else:
                urllib.request.urlopen(req, timeout=15).read()
            self.message("COMMUNAUTÉ", "Note envoyée.\nElle sera visible après validation.")
        except Exception as e:
            self.message("Erreur COMM.", str(e)[:300])

    def ouvrir_communaute(self, *args):
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        box.add_widget(Label(
            text="[b]NOTE COMMUNAUTÉ[/b]\nÉcris une note liée au thème actuel.",
            markup=True, color=(1, 1, 1, 1),
            size_hint=(1, None), height=dp(70)
        ))
        inp_nom = TextInput(hint_text="Ton nom ou pseudo", multiline=False, size_hint=(1, None), height=dp(45))
        box.add_widget(inp_nom)
        inp_note = TextInput(hint_text="Écris ta note ici...", multiline=True, size_hint=(1, 1))
        box.add_widget(inp_note)
        row = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint=(1, None), height=dp(45))
        btn_send = Button(text="ENVOYER", background_color=(0.1, 0.6, 0.3, 1))
        btn_close = Button(text="FERMER", background_color=(0.4, 0.4, 0.4, 1))
        row.add_widget(btn_send)
        row.add_widget(btn_close)
        box.add_widget(row)
        pop = Popup(title="COMMUNAUTÉ", content=box, size_hint=(0.95, 0.75))

        def do_send(_):
            texte = inp_note.text.strip()
            if not texte:
                self.message("COMMUNAUTÉ", "Écris une note avant d’envoyer.")
                return
            pop.dismiss()
            envoyer_note_communaute(self, inp_nom.text.strip(), texte)

        btn_send.bind(on_release=do_send)
        btn_close.bind(on_release=lambda x: pop.dismiss())
        pop.open()

    MoneyRoot.ouvrir_communaute = ouvrir_communaute

    old_build_ui = MoneyRoot.build_ui
    def build_ui_with_comm(self):
        old_build_ui(self)
        try:
            for child in list(self.children):
                if isinstance(child, BoxLayout):
                    textes = [getattr(w, "text", "") for w in child.children]
                    if "THEME" in textes and "SOLUTIONS" in textes and "TABLE" in textes:
                        if "COMM." not in textes:
                            btn_comm = Button(text="COMM.", bold=True, background_color=(0.1, 0.45, 0.55, 1))
                            btn_comm.bind(on_release=lambda x: self.ouvrir_communaute())
                            child.add_widget(btn_comm)
                        break
        except Exception:
            pass
    MoneyRoot.build_ui = build_ui_with_comm

    def fermer_tous_popups():
        try:
            if hasattr(Popup, "_popup_stack"):
                for p in list(Popup._popup_stack):
                    try:
                        p.dismiss()
                    except Exception:
                        pass
        except Exception:
            pass

    if hasattr(MoneyRoot, "apply_solution"):
        old_apply_solution = MoneyRoot.apply_solution
        def apply_solution_close_popups(self, sol):
            fermer_tous_popups()
            return old_apply_solution(self, sol)
        MoneyRoot.apply_solution = apply_solution_close_popups

_geostar_comm_solution_patch()




# ============================================================
# PATCH GEOSTAR FINAL — MISE A JOUR DISTANTE + NOTES VALIDÉES
# ============================================================

def _geostar_remote_update_and_validated_notes_patch():
    import json
    import ssl
    import urllib.request
    import urllib.parse
    import threading
    from datetime import datetime
    from kivy.uix.popup import Popup
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.textinput import TextInput
    from kivy.metrics import dp
    from kivy.clock import Clock

    SUPABASE_URL = "https://kvgjghvcptryghggzuui.supabase.co"
    SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt2Z2pnaHZjcHRyeWdoZ2d6dXVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3MDkxMzcsImV4cCI6MjA5NTI4NTEzN30.IzYhPAOUv50RmCVTe8KUaM2F4efyewgmxj-D9QVVjMU"

    # Fichier distant modifiable sans recompiler.
    REMOTE_CONFIG_URL = "https://raw.githubusercontent.com/Moneymyck/geostar-android/main/config_geostar.json"

    DEFAULT_REMOTE_CONFIG = {
        "app_name": "GEOSTAR",
        "contact_email": "anthom1253@gmail.com",
        "message_accueil": "Bienvenue dans GEOSTAR",
        "comm_enabled": True,
        "notes_valides_enabled": True,
        "maintenance": False,
        "maintenance_message": "Application en maintenance.",
        "version_message": ""
    }

    def _ssl_ctx():
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        except Exception:
            return None

    def _http_json(method, url, payload=None, headers=None):
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers=headers or {"User-Agent": "GEOSTAR/1.0"}
        )
        ctx = _ssl_ctx()
        if ctx:
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                raw = r.read().decode("utf-8")
        else:
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read().decode("utf-8")
        if not raw:
            return None
        return json.loads(raw)

    def _get_remote_config():
        try:
            cfg = _http_json("GET", REMOTE_CONFIG_URL)
            if isinstance(cfg, dict):
                merged = dict(DEFAULT_REMOTE_CONFIG)
                merged.update(cfg)
                return merged
        except Exception:
            pass
        return dict(DEFAULT_REMOTE_CONFIG)

    def _supabase_headers(prefer="return=representation"):
        return {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": "Bearer " + SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
            "Prefer": prefer,
            "User-Agent": "GEOSTAR-Community/1.0"
        }

    def _theme_key(self):
        try:
            mothers = getattr(self, "mother_codes", None)
            if mothers and isinstance(mothers, (list, tuple)):
                return "-".join(str(x) for x in mothers)
        except Exception:
            pass
        try:
            mothers = getattr(self, "mothers", None)
            if mothers and isinstance(mothers, (list, tuple)):
                return "-".join(str(x) for x in mothers)
        except Exception:
            pass
        return "general"

    def _fetch_notes_valides(self, theme_key=None):
        # On lit toutes les notes validées. Si theme_key est disponible, on essaie d'abord ce theme.
        base = SUPABASE_URL + "/rest/v1/notes_communaute"
        if theme_key and theme_key != "general":
            q = "?select=*&statut=eq.valide&theme_key=eq." + urllib.parse.quote(theme_key) + "&order=date_soumission.desc"
        else:
            q = "?select=*&statut=eq.valide&order=date_soumission.desc"
        return _http_json("GET", base + q, headers=_supabase_headers()) or []

    def _send_note(self, auteur, texte, theme_key, langue="fr"):
        payload = {
            "theme_key": theme_key or "general",
            "auteur": auteur or "Anonyme",
            "code_licence": "",
            "langue": langue,
            "texte": texte,
            "audio_url": "",
            "statut": "attente",
            "date_soumission": datetime.now().isoformat()
        }
        url = SUPABASE_URL + "/rest/v1/notes_communaute"
        return _http_json("POST", url, payload=payload, headers=_supabase_headers("return=minimal"))

    def _safe_message(self, title, msg):
        try:
            return self.message(title, msg)
        except Exception:
            pop = Popup(title=title, content=Label(text=msg), size_hint=(0.85, 0.45))
            pop.open()

    # ---------- MISE A JOUR DISTANTE ----------
    def verifier_mise_a_jour_distante(self, silent=False):
        def worker():
            cfg = _get_remote_config()
            self.remote_config = cfg

            def finish(dt):
                if cfg.get("maintenance"):
                    _safe_message(self, "MAINTENANCE", str(cfg.get("maintenance_message", "Application en maintenance.")))
                    return
                msg = str(cfg.get("version_message", "") or "").strip()
                if msg and not silent:
                    _safe_message(self, "INFO GEOSTAR", msg)
            Clock.schedule_once(finish, 0)

        threading.Thread(target=worker, daemon=True).start()

    MoneyRoot.verifier_mise_a_jour_distante = verifier_mise_a_jour_distante

    # Appeler la vérification au lancement de l'interface
    try:
        old_build_ui = MoneyRoot.build_ui

        def build_ui_remote(self):
            old_build_ui(self)
            self.remote_config = _get_remote_config()
            try:
                self.verifier_mise_a_jour_distante(silent=True)
            except Exception:
                pass

            # Ajout du bouton COMM si absent.
            try:
                for child in list(self.children):
                    if isinstance(child, BoxLayout):
                        textes = [getattr(w, "text", "") for w in child.children]
                        if "THEME" in textes and "SOLUTIONS" in textes and "TABLE" in textes:
                            if "COMM." not in textes:
                                btn_comm = Button(text="COMM.", bold=True, background_color=(0.1, 0.45, 0.55, 1))
                                btn_comm.bind(on_release=lambda x: self.ouvrir_communaute())
                                child.add_widget(btn_comm)
                            break
            except Exception:
                pass

        MoneyRoot.build_ui = build_ui_remote
    except Exception:
        pass

    # ---------- COMMUNAUTE : ENVOI + NOTES VALIDÉES ----------
    def ouvrir_communaute(self, *args):
        cfg = getattr(self, "remote_config", None) or _get_remote_config()
        if not cfg.get("comm_enabled", True):
            _safe_message(self, "COMMUNAUTÉ", "La communauté est désactivée temporairement.")
            return

        theme = _theme_key(self)

        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        titre = Label(
            text="[b]COMMUNAUTÉ[/b]\nThème : " + str(theme),
            markup=True,
            color=(1, 1, 1, 1),
            size_hint=(1, None),
            height=dp(58)
        )
        box.add_widget(titre)

        row_top = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(6))
        btn_valides = Button(text="VOIR NOTES VALIDÉES", background_color=(0.05, 0.45, 0.65, 1))
        btn_ecrire = Button(text="ÉCRIRE UNE NOTE", background_color=(0.1, 0.55, 0.25, 1))
        row_top.add_widget(btn_valides)
        row_top.add_widget(btn_ecrire)
        box.add_widget(row_top)

        content_area = BoxLayout(orientation="vertical", size_hint=(1, 1), spacing=dp(6))
        box.add_widget(content_area)

        bottom = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(6))
        btn_refresh = Button(text="ACTUALISER", background_color=(0.15, 0.25, 0.45, 1))
        btn_close = Button(text="FERMER", background_color=(0.35, 0.35, 0.35, 1))
        bottom.add_widget(btn_refresh)
        bottom.add_widget(btn_close)
        box.add_widget(bottom)

        pop = Popup(title="COMMUNAUTÉ", content=box, size_hint=(0.96, 0.88))

        def show_write():
            content_area.clear_widgets()
            inp_nom = TextInput(hint_text="Ton nom ou pseudo", multiline=False, size_hint=(1, None), height=dp(44))
            inp_note = TextInput(hint_text="Écris ta note ici...", multiline=True, size_hint=(1, 1))
            send = Button(text="ENVOYER POUR VALIDATION", size_hint=(1, None), height=dp(46), background_color=(0.1, 0.6, 0.3, 1))
            content_area.add_widget(inp_nom)
            content_area.add_widget(inp_note)
            content_area.add_widget(send)

            def do_send(_):
                texte = inp_note.text.strip()
                if not texte:
                    _safe_message(self, "COMMUNAUTÉ", "Écris une note avant d’envoyer.")
                    return
                send.disabled = True
                send.text = "ENVOI..."

                def worker():
                    try:
                        _send_note(inp_nom.text.strip(), texte, theme)
                        ok, msg = True, "Note envoyée.\nElle apparaîtra après validation Admin."
                    except Exception as e:
                        ok, msg = False, "Erreur envoi : " + str(e)[:250]

                    def finish(dt):
                        send.disabled = False
                        send.text = "ENVOYER POUR VALIDATION"
                        _safe_message(self, "COMMUNAUTÉ" if ok else "ERREUR", msg)
                        if ok:
                            inp_note.text = ""
                    Clock.schedule_once(finish, 0)

                threading.Thread(target=worker, daemon=True).start()

            send.bind(on_release=do_send)

        def show_valides():
            content_area.clear_widgets()
            content_area.add_widget(Label(text="Chargement des notes validées...", color=(1, 1, 1, 1)))

            def worker():
                try:
                    notes = _fetch_notes_valides(theme)
                    # Si aucune note pour ce thème, afficher toutes les notes validées.
                    if not notes and theme != "general":
                        notes = _fetch_notes_valides(None)
                    err = ""
                except Exception as e:
                    notes = []
                    err = str(e)[:300]

                def finish(dt):
                    content_area.clear_widgets()
                    if err:
                        content_area.add_widget(Label(text="Erreur lecture Supabase :\n" + err, color=(1, 0.3, 0.3, 1)))
                        return

                    if not notes:
                        content_area.add_widget(Label(text="Aucune note validée pour le moment.", color=(1, 1, 1, 1)))
                        return

                    sv = ScrollView()
                    grid = GridLayout(cols=1, spacing=dp(8), padding=dp(4), size_hint_y=None)
                    grid.bind(minimum_height=grid.setter("height"))
                    sv.add_widget(grid)

                    for note in notes:
                        auteur = note.get("auteur", "Anonyme")
                        texte = note.get("texte", "")
                        d = str(note.get("date_soumission", ""))[:19]
                        tk = note.get("theme_key", "")

                        card = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(4), size_hint_y=None, height=dp(126))
                        card.add_widget(Label(text="[b]" + str(auteur) + "[/b]  " + str(d), markup=True, color=(1, 0.85, 0.15, 1), size_hint=(1, None), height=dp(24)))
                        card.add_widget(Label(text="Thème : " + str(tk), color=(0.75, 0.75, 0.8, 1), size_hint=(1, None), height=dp(20)))
                        lbl = Label(text=str(texte)[:260], color=(1, 1, 1, 1), halign="left", valign="top")
                        lbl.bind(width=lambda s, w: setattr(s, "text_size", (w, None)))
                        card.add_widget(lbl)
                        grid.add_widget(card)

                    content_area.add_widget(sv)

                Clock.schedule_once(finish, 0)

            threading.Thread(target=worker, daemon=True).start()

        btn_valides.bind(on_release=lambda x: show_valides())
        btn_ecrire.bind(on_release=lambda x: show_write())
        btn_refresh.bind(on_release=lambda x: show_valides())
        btn_close.bind(on_release=lambda x: pop.dismiss())

        pop.open()
        show_valides()

    MoneyRoot.ouvrir_communaute = ouvrir_communaute

    # ---------- FERMER POPUP SOLUTIONS ----------
    try:
        old_popup_open = Popup.open

        def popup_open_with_close(self, *args, **kwargs):
            result = old_popup_open(self, *args, **kwargs)
            try:
                title = getattr(self, "title", "")
                if title and "SOLUTION" in title.upper():
                    content = getattr(self, "content", None)
                    if content is not None and hasattr(content, "add_widget"):
                        deja = False
                        if hasattr(content, "children"):
                            for child in content.children:
                                if getattr(child, "text", "") == "FERMER":
                                    deja = True
                        if not deja:
                            b = Button(text="FERMER", size_hint=(1, None), height=dp(52), bold=True, background_color=(0.45, 0.15, 0.15, 1))
                            b.bind(on_release=lambda x: self.dismiss())
                            content.add_widget(b)
            except Exception:
                pass
            return result

        Popup.open = popup_open_with_close
    except Exception:
        pass

_geostar_remote_update_and_validated_notes_patch()

if __name__ == "__main__":
    MoneyApp().run()
