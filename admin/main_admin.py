from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.metrics import dp

import json
import os
import ssl
import urllib.request
import urllib.parse
import base64
import random
import string
from datetime import datetime, timedelta

Window.clearcolor = (0.04, 0.04, 0.06, 1)

SUPABASE_URL = "https://kvgjghvcptryghggzuui.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt2Z2pnaHZjcHRyeWdoZ2d6dXVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3MDkxMzcsImV4cCI6MjA5NTI4NTEzN30.IzYhPAOUv50RmCVTe8KUaM2F4efyewgmxj-D9QVVjMU"
SETTINGS_FILE = "geostar_admin_settings.json"
PIN_FILE = "geostar_admin_pin.json"


def ssl_ctx():
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return None


def read_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_pin():
    return str(read_json(PIN_FILE, {"pin": "1253"}).get("pin", "1253"))


def set_pin(pin):
    write_json(PIN_FILE, {"pin": str(pin)})


def settings():
    return read_json(SETTINGS_FILE, {
        "github_token": "",
        "owner": "Moneymyck",
        "repo": "geostar-android",
        "branch": "main",
        "codes_file": "codes_geostar.json"
    })


def save_settings(s):
    write_json(SETTINGS_FILE, s)


def make_label(text, size=16, color=(1, 1, 1, 1), h=40, bold=False):
    lbl = Label(text=text, font_size=dp(size), color=color, bold=bold,
                size_hint_y=None, height=dp(h), halign="center", valign="middle")
    lbl.bind(size=lambda s, v: setattr(s, "text_size", v))
    return lbl


def make_btn(text, bg=(0.1, 0.25, 0.45, 1), h=52):
    return Button(text=text, bold=True, size_hint_y=None, height=dp(h),
                  background_color=bg, color=(1, 1, 1, 1))


def alert(title, msg):
    box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    box.add_widget(make_label(str(msg), size=14, h=160))
    btn = make_btn("OK", bg=(0.35, 0.35, 0.35, 1), h=46)
    box.add_widget(btn)
    pop = Popup(title=title, content=box, size_hint=(0.9, 0.55))
    btn.bind(on_release=lambda x: pop.dismiss())
    pop.open()


def http_json(method, url, payload=None, headers=None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {"User-Agent": "GEOSTAR-ADMIN/1.0"})
    ctx = ssl_ctx()
    if ctx:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            raw = r.read().decode("utf-8")
    else:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8")
    if not raw:
        return None
    return json.loads(raw)


def github_headers(token):
    return {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "GEOSTAR-ADMIN/1.0"
    }


def github_get_codes():
    s = settings()
    token = s.get("github_token", "").strip()
    if not token:
        raise Exception("Token GitHub vide. Va dans PARAMÈTRES.")
    owner, repo, branch, path = s["owner"], s["repo"], s["branch"], s["codes_file"]
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    data = http_json("GET", url, headers=github_headers(token))
    sha = data.get("sha")
    raw = base64.b64decode(data.get("content", "")).decode("utf-8")
    codes = json.loads(raw) if raw else {}
    if not isinstance(codes, dict):
        codes = {}
    codes.setdefault("codes_valides", {})
    codes.setdefault("codes_bloques", [])
    return codes, sha


def github_save_codes(codes, sha, message):
    s = settings()
    token = s.get("github_token", "").strip()
    owner, repo, branch, path = s["owner"], s["repo"], s["branch"], s["codes_file"]
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    content = json.dumps(codes, ensure_ascii=False, indent=2)
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
        "sha": sha
    }
    return http_json("PUT", url, payload=payload, headers=github_headers(token))


def generate_geo_code():
    chars = string.ascii_uppercase + string.digits
    return "GEO-" + "".join(random.choice(chars) for _ in range(4))


def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
        "User-Agent": "GEOSTAR-ADMIN/1.0"
    }


def fetch_notes():
    url = SUPABASE_URL + "/rest/v1/notes_communaute?select=*&order=date_soumission.desc"
    data = http_json("GET", url, headers=supabase_headers())
    return data if isinstance(data, list) else []


def update_note_status(note_id, statut):
    url = SUPABASE_URL + "/rest/v1/notes_communaute?id=eq." + urllib.parse.quote(str(note_id))
    payload = {"statut": statut, "date_validation": datetime.now().isoformat()}
    return http_json("PATCH", url, payload=payload, headers=supabase_headers())


class AdminApp(App):
    def build(self):
        self.root = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12))
        self.show_login()
        return self.root

    def clear(self):
        self.root.clear_widgets()

    def show_login(self):
        self.clear()
        self.root.add_widget(Label(size_hint_y=1))
        self.root.add_widget(make_label("GEOSTAR ADMIN", size=30, color=(1, 0.82, 0.05, 1), bold=True, h=60))
        self.pin_input = TextInput(hint_text="Code PIN admin", multiline=False, password=True, input_filter="int",
                                   size_hint_y=None, height=dp(56), font_size=dp(22), halign="center")
        self.root.add_widget(self.pin_input)
        btn = make_btn("CONNEXION", bg=(0, 0.35, 0.05, 1), h=58)
        btn.bind(on_release=self.login)
        self.root.add_widget(btn)
        self.info = make_label("PIN par défaut : 1253", size=14, color=(0.8, 0.8, 0.8, 1), h=45)
        self.root.add_widget(self.info)
        self.root.add_widget(Label(size_hint_y=1))

    def login(self, *_):
        if self.pin_input.text.strip() == get_pin():
            self.show_dashboard()
        else:
            self.info.text = "PIN incorrect"

    def show_dashboard(self):
        self.clear()
        top = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8))
        top.add_widget(make_label("GEOSTAR ADMIN", size=22, color=(1, 0.82, 0.05, 1), bold=True, h=54))
        bs = make_btn("PARAMÈTRES", bg=(0.18, 0.18, 0.3, 1), h=54)
        bs.bind(on_release=lambda x: self.show_settings())
        top.add_widget(bs)
        self.root.add_widget(top)

        b1 = make_btn("+ NOUVEAU CODE", bg=(0, 0.45, 0.05, 1), h=62)
        b1.bind(on_release=self.create_code_popup)
        self.root.add_widget(b1)
        b2 = make_btn("NOTES SUPABASE", bg=(0.22, 0.22, 0.55, 1), h=62)
        b2.bind(on_release=self.show_notes_popup)
        self.root.add_widget(b2)
        b3 = make_btn("TESTER SUPABASE", bg=(0.12, 0.35, 0.45, 1), h=52)
        b3.bind(on_release=lambda x: self.test_supabase())
        self.root.add_widget(b3)
        self.status = make_label("", size=15, color=(1, 1, 1, 1), h=120)
        self.root.add_widget(self.status)
        self.root.add_widget(Label(size_hint_y=1))
        bl = make_btn("SE DÉCONNECTER", bg=(0.45, 0.05, 0.05, 1), h=54)
        bl.bind(on_release=lambda x: self.show_login())
        self.root.add_widget(bl)

    def show_settings(self):
        self.clear()
        s = settings()
        self.root.add_widget(make_label("PARAMÈTRES", size=24, color=(1, 0.82, 0.05, 1), bold=True, h=55))
        self.in_token = TextInput(text=s.get("github_token", ""), hint_text="Token GitHub", password=True, multiline=False, size_hint_y=None, height=dp(50))
        self.in_owner = TextInput(text=s.get("owner", "Moneymyck"), hint_text="Propriétaire", multiline=False, size_hint_y=None, height=dp(50))
        self.in_repo = TextInput(text=s.get("repo", "geostar-android"), hint_text="Dépôt", multiline=False, size_hint_y=None, height=dp(50))
        self.in_branch = TextInput(text=s.get("branch", "main"), hint_text="Branche", multiline=False, size_hint_y=None, height=dp(50))
        self.in_file = TextInput(text=s.get("codes_file", "codes_geostar.json"), hint_text="Fichier codes", multiline=False, size_hint_y=None, height=dp(50))
        for label, widget in [("Token GitHub", self.in_token), ("Propriétaire", self.in_owner), ("Dépôt", self.in_repo), ("Branche", self.in_branch), ("Fichier", self.in_file)]:
            self.root.add_widget(make_label(label, size=13, color=(0.9, 0.9, 0.9, 1), h=25))
            self.root.add_widget(widget)
        bs = make_btn("ENREGISTRER PARAMÈTRES", bg=(0.05, 0.25, 0.55, 1), h=52)
        bs.bind(on_release=lambda x: self.save_settings_screen())
        self.root.add_widget(bs)
        bp = make_btn("MODIFIER CODE PIN", bg=(0.5, 0.25, 0, 1), h=52)
        bp.bind(on_release=lambda x: self.change_pin_popup())
        self.root.add_widget(bp)
        br = make_btn("< RETOUR", bg=(0.25, 0.25, 0.25, 1), h=52)
        br.bind(on_release=lambda x: self.show_dashboard())
        self.root.add_widget(br)

    def save_settings_screen(self):
        save_settings({
            "github_token": self.in_token.text.strip(),
            "owner": self.in_owner.text.strip() or "Moneymyck",
            "repo": self.in_repo.text.strip() or "geostar-android",
            "branch": self.in_branch.text.strip() or "main",
            "codes_file": self.in_file.text.strip() or "codes_geostar.json"
        })
        alert("OK", "Paramètres enregistrés.")

    def change_pin_popup(self):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        old = TextInput(hint_text="Ancien PIN", password=True, multiline=False, input_filter="int", size_hint_y=None, height=dp(50))
        new = TextInput(hint_text="Nouveau PIN 4 chiffres", password=True, multiline=False, input_filter="int", size_hint_y=None, height=dp(50))
        msg = make_label("", size=13, color=(1, 0.3, 0.3, 1), h=35)
        bsave = make_btn("ENREGISTRER", bg=(0, 0.45, 0.05, 1), h=50)
        breset = make_btn("REMETTRE 1253", bg=(0.55, 0.25, 0, 1), h=46)
        for w in [old, new, msg, bsave, breset]:
            box.add_widget(w)
        pop = Popup(title="Modifier PIN", content=box, size_hint=(0.9, 0.55))
        def do_save(_):
            if old.text.strip() != get_pin():
                msg.text = "Ancien PIN incorrect"
                return
            if len(new.text.strip()) != 4 or not new.text.strip().isdigit():
                msg.text = "PIN invalide"
                return
            set_pin(new.text.strip())
            pop.dismiss(); alert("OK", "PIN modifié.")
        def do_reset(_):
            set_pin("1253")
            pop.dismiss(); alert("OK", "PIN remis à 1253.")
        bsave.bind(on_release=do_save)
        breset.bind(on_release=do_reset)
        pop.open()

    def create_code_popup(self, *_):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        pseudo = TextInput(hint_text="Nom client / note", multiline=False, size_hint_y=None, height=dp(50))
        jours = TextInput(text="30", hint_text="Durée en jours", multiline=False, input_filter="int", size_hint_y=None, height=dp(50))
        msg = make_label("", size=13, color=(1, 1, 1, 1), h=70)
        btn = make_btn("CRÉER ET SYNCHRONISER", bg=(0, 0.45, 0.05, 1), h=54)
        for w in [make_label("Créer un code GEO-XXXX", size=18, color=(1, 0.82, 0.05, 1), bold=True, h=45), pseudo, jours, msg, btn]:
            box.add_widget(w)
        pop = Popup(title="Nouveau code", content=box, size_hint=(0.92, 0.64))
        def do_create(_):
            try:
                nb = int(jours.text.strip() or "30")
                code = generate_geo_code()
                expire = (datetime.now() + timedelta(days=nb)).strftime("%Y-%m-%d")
                codes, sha = github_get_codes()
                codes["codes_valides"][code] = {"client": pseudo.text.strip() or "Client", "expire": expire, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
                github_save_codes(codes, sha, "GEOSTAR Admin - nouveau code " + code)
                msg.text = "CODE CRÉÉ : " + code + "\nExpire : " + expire
                self.status.text = msg.text
            except Exception as e:
                msg.text = "ERREUR : " + str(e)[:250]
        btn.bind(on_release=do_create)
        pop.open()

    def test_supabase(self):
        try:
            notes = fetch_notes()
            alert("SUPABASE OK", "Connexion OK.\nNotes trouvées : " + str(len(notes)))
        except Exception as e:
            alert("ERREUR SUPABASE", str(e)[:500])

    def show_notes_popup(self, *_):
        main = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))
        header = make_label("Chargement...", size=16, color=(1, 0.82, 0.05, 1), bold=True, h=40)
        main.add_widget(header)
        btns = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        b_all = make_btn("TOUTES", bg=(0.1, 0.25, 0.45, 1), h=42)
        b_att = make_btn("ATTENTE", bg=(0.55, 0.28, 0, 1), h=42)
        b_val = make_btn("VALIDÉES", bg=(0, 0.45, 0.05, 1), h=42)
        b_rej = make_btn("REJETÉES", bg=(0.5, 0.05, 0.05, 1), h=42)
        for b in [b_all, b_att, b_val, b_rej]:
            btns.add_widget(b)
        main.add_widget(btns)
        scroll = ScrollView(); grid = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height")); scroll.add_widget(grid); main.add_widget(scroll)
        bottom = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        br = make_btn("ACTUALISER", bg=(0.1, 0.25, 0.45, 1), h=46)
        bc = make_btn("FERMER", bg=(0.25, 0.25, 0.25, 1), h=46)
        bottom.add_widget(br); bottom.add_widget(bc); main.add_widget(bottom)
        pop = Popup(title="Notes communauté Supabase", content=main, size_hint=(0.96, 0.92))
        state = {"notes": [], "filter": "all"}
        def render(f="all"):
            state["filter"] = f; grid.clear_widgets()
            notes = state["notes"] if f == "all" else [n for n in state["notes"] if str(n.get("statut", "attente")) == f]
            header.text = "Notes : " + str(len(notes)) + " / Total : " + str(len(state["notes"]))
            if not notes:
                grid.add_widget(make_label("Aucune note", size=16, color=(0.8, 0.8, 0.8, 1), h=80)); return
            for note in notes:
                grid.add_widget(self.note_card(note, lambda: load_notes(state["filter"])))
        def load_notes(f="all"):
            try:
                state["notes"] = fetch_notes(); render(f)
            except Exception as e:
                grid.clear_widgets(); header.text = "Erreur Supabase"; grid.add_widget(make_label(str(e)[:500], size=12, color=(1, 0.3, 0.3, 1), h=150))
        b_all.bind(on_release=lambda x: render("all")); b_att.bind(on_release=lambda x: render("attente")); b_val.bind(on_release=lambda x: render("valide")); b_rej.bind(on_release=lambda x: render("rejete"))
        br.bind(on_release=lambda x: load_notes(state["filter"])); bc.bind(on_release=lambda x: pop.dismiss())
        pop.open(); load_notes("all")

    def note_card(self, note, refresh):
        statut = str(note.get("statut", "attente")); auteur = str(note.get("auteur", "Anonyme")); theme = str(note.get("theme_key", "")); texte = str(note.get("texte", "")); nid = note.get("id", "")
        card = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(4), size_hint_y=None, height=dp(210))
        lab = Label(text=f"[b]{auteur}[/b] | {statut.upper()}\nThème : {theme}\n\n{texte[:250]}", markup=True, color=(1, 1, 1, 1), halign="left", valign="top")
        lab.bind(size=lambda s, v: setattr(s, "text_size", v)); card.add_widget(lab)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        def set_status(st):
            try:
                update_note_status(nid, st); refresh()
            except Exception as e:
                alert("Erreur", str(e)[:300])
        for txt, st, bg in [("ATTENTE", "attente", (0.55, 0.28, 0, 1)), ("VALIDER", "valide", (0, 0.45, 0.05, 1)), ("REJETER", "rejete", (0.5, 0.05, 0.05, 1))]:
            b = make_btn(txt, bg=bg, h=44); b.bind(on_release=lambda x, ss=st: set_status(ss)); row.add_widget(b)
        card.add_widget(row); return card



# ============================================================
# PATCH ADMIN — DEMANDES SUPPRESSION NOTES PUBLIQUES
# ============================================================

def _admin_delete_request_notes_patch():
    from kivy.uix.boxlayout import BoxLayout
    from kivy.metrics import dp

    def note_card_with_delete_request(self, n, reload):
        card = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(4), size_hint_y=None, height=dp(230))
        statut = str(n.get("statut", "attente"))
        txt = (
            "[b]" + str(n.get("auteur", "Anonyme")) + "[/b] | " + statut.upper()
            + "\nThème : " + str(n.get("theme_key", ""))
            + "\n\n" + str(n.get("texte", ""))[:250]
        )
        card.add_widget(make_label(txt, size=13, h=125))

        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))

        if statut == "demande_suppression":
            b_accept = make_btn("ACCEPTER SUPPR.", bg=(0.50, 0.05, 0.05, 1), h=44)
            b_refuse = make_btn("REFUSER SUPPR.", bg=(0, 0.45, 0.05, 1), h=44)

            def accept(_):
                try:
                    update_note_status(n.get("id"), "supprime")
                    reload()
                except Exception as e:
                    alert("Erreur", str(e)[:300])

            def refuse(_):
                try:
                    update_note_status(n.get("id"), "valide")
                    reload()
                except Exception as e:
                    alert("Erreur", str(e)[:300])

            b_accept.bind(on_release=accept)
            b_refuse.bind(on_release=refuse)
            row.add_widget(b_accept)
            row.add_widget(b_refuse)
        else:
            for txt_btn, st, color in [
                ("ATTENTE", "attente", (0.55, 0.28, 0, 1)),
                ("VALIDER", "valide", (0, 0.45, 0.05, 1)),
                ("REJETER", "rejete", (0.5, 0.05, 0.05, 1)),
                ("SUPPRIMER", "supprime", (0.18, 0.18, 0.18, 1)),
            ]:
                b = make_btn(txt_btn, bg=color, h=44)
                b.bind(on_release=lambda x, ss=st: (update_note_status(n.get("id"), ss), reload()))
                row.add_widget(b)

        card.add_widget(row)
        return card

    AdminApp.note_card = note_card_with_delete_request

_admin_delete_request_notes_patch()

if __name__ == "__main__":
    AdminApp().run()
