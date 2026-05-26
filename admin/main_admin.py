from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.core.window import Window

import requests
import json
import random
import string

Window.clearcolor = (0.05, 0.05, 0.05, 1)

SUPABASE_URL = "https://kvgjghvcptryghggzuui.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt2Z2pnaHZjcHRyeWdoZ2d6dXVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3MDkxMzcsImV4cCI6MjA5NTI4NTEzN30.IzYhPAOUv50RmCVTe8KUaM2F4efyewgmxj-D9QVVjMU"

PIN_ADMIN = "1253"


class AdminApp(App):

    def build(self):

        self.root = BoxLayout(
            orientation="vertical",
            padding=20,
            spacing=15
        )

        title = Label(
            text="GEOSTAR ADMIN",
            font_size=32,
            bold=True,
            color=(1, 0.8, 0, 1),
            size_hint=(1, 0.15)
        )

        self.pin_input = TextInput(
            hint_text="PIN ADMIN",
            multiline=False,
            password=True,
            size_hint=(1, 0.1)
        )

        login_btn = Button(
            text="CONNEXION",
            background_color=(0, 0.5, 0, 1),
            size_hint=(1, 0.1)
        )

        login_btn.bind(on_press=self.login)

        self.info = Label(
            text="",
            color=(1, 0.3, 0.3, 1),
            size_hint=(1, 0.1)
        )

        self.root.add_widget(title)
        self.root.add_widget(self.pin_input)
        self.root.add_widget(login_btn)
        self.root.add_widget(self.info)

        return self.root

    def login(self, instance):

        if self.pin_input.text == PIN_ADMIN:
            self.open_admin()
        else:
            self.info.text = "PIN incorrect"

    def open_admin(self):

        self.root.clear_widgets()

        title = Label(
            text="PANNEAU ADMIN",
            font_size=28,
            bold=True,
            color=(0, 1, 1, 1),
            size_hint=(1, 0.1)
        )

        btn_code = Button(
            text="+ NOUVEAU CODE",
            background_color=(0, 0.5, 0, 1),
            size_hint=(1, 0.1)
        )

        btn_code.bind(on_press=self.generate_code)

        btn_notes = Button(
            text="NOTES SUPABASE",
            background_color=(0.3, 0.3, 0.8, 1),
            size_hint=(1, 0.1)
        )

        btn_notes.bind(on_press=self.show_notes)

        self.codes_label = Label(
            text="",
            size_hint=(1, 0.15),
            color=(1, 1, 1, 1)
        )

        self.root.add_widget(title)
        self.root.add_widget(btn_code)
        self.root.add_widget(btn_notes)
        self.root.add_widget(self.codes_label)

    def generate_code(self, instance):

        chars = string.ascii_uppercase + string.digits

        code = "GEO-" + ''.join(
            random.choice(chars)
            for _ in range(4)
        )

        self.codes_label.text = f"CODE : {code}"

        popup = Popup(
            title="CODE GÉNÉRÉ",
            content=Label(text=code),
            size_hint=(0.7, 0.4)
        )

        popup.open()

    def show_notes(self, instance):

        layout = GridLayout(
            cols=1,
            spacing=15,
            size_hint_y=None,
            padding=15
        )

        layout.bind(minimum_height=layout.setter('height'))

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        try:

            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/notes_communaute?select=*",
                headers=headers
            )

            notes = response.json()

            if isinstance(notes, dict):
                raise Exception(str(notes))

            if len(notes) == 0:

                layout.add_widget(
                    Label(
                        text="AUCUNE NOTE",
                        size_hint_y=None,
                        height=100
                    )
                )

            for note in notes:

                auteur = note.get("auteur", "Anonyme")
                texte = note.get("texte", "")
                theme = note.get("theme_key", "")
                statut = note.get("statut", "attente")

                card = BoxLayout(
                    orientation="vertical",
                    size_hint_y=None,
                    height=300,
                    spacing=10,
                    padding=10
                )

                txt = f"""
AUTEUR : {auteur}

THEME :
{theme}

NOTE :
{texte}

STATUT :
{statut}
"""

                label = Label(
                    text=txt,
                    halign="left",
                    valign="top"
                )

                label.bind(
                    size=lambda s, w:
                    setattr(s, 'text_size', w)
                )

                btns = BoxLayout(
                    size_hint_y=None,
                    height=60,
                    spacing=10
                )

                valider = Button(
                    text="VALIDER",
                    background_color=(0, 0.6, 0, 1)
                )

                rejeter = Button(
                    text="REJETER",
                    background_color=(0.7, 0, 0, 1)
                )

                valider.bind(
                    on_press=lambda x,
                    id_note=note["id"]:
                    self.update_note(
                        id_note,
                        "valide"
                    )
                )

                rejeter.bind(
                    on_press=lambda x,
                    id_note=note["id"]:
                    self.update_note(
                        id_note,
                        "rejete"
                    )
                )

                btns.add_widget(valider)
                btns.add_widget(rejeter)

                card.add_widget(label)
                card.add_widget(btns)

                layout.add_widget(card)

        except Exception as e:

            layout.add_widget(
                Label(
                    text=f"ERREUR : {str(e)}",
                    size_hint_y=None,
                    height=100
                )
            )

        scroll = ScrollView()
        scroll.add_widget(layout)

        close_btn = Button(
            text="FERMER",
            size_hint=(1, 0.1),
            background_color=(0.2, 0.2, 0.2, 1)
        )

        main = BoxLayout(
            orientation="vertical"
        )

        main.add_widget(scroll)
        main.add_widget(close_btn)

        popup = Popup(
            title="NOTES COMMUNAUTÉ",
            content=main,
            size_hint=(0.95, 0.95)
        )

        close_btn.bind(
            on_press=popup.dismiss
        )

        popup.open()

    def update_note(self, note_id, statut):

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "statut": statut
        }

        try:

            requests.patch(
                f"{SUPABASE_URL}/rest/v1/notes_communaute?id=eq.{note_id}",
                headers=headers,
                data=json.dumps(data)
            )

        except Exception as e:

            print(str(e))


AdminApp().run()
