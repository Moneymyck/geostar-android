from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import platform
import os, json, ssl, base64, random, string, urllib.request, urllib.parse, tempfile
from datetime import datetime, timedelta

Window.clearcolor = (0.04, 0.04, 0.06, 1)

SUPABASE_URL = 'https://kvgjghvcptryghggzuui.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt2Z2pnaHZjcHRyeWdoZ2d6dXVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3MDkxMzcsImV4cCI6MjA5NTI4NTEzN30.IzYhPAOUv50RmCVTe8KUaM2F4efyewgmxj-D9QVVjMU'
AUDIO_BUCKET = 'geostar-audio'
SETTINGS_FILE = 'geostar_admin_settings.json'
PIN_FILE = 'geostar_admin_pin.json'

_CURRENT_SOUND = None
_CURRENT_AUDIO_FILE = None


def ctx():
    c = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def rj(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default


def wj(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_pin():
    return str(rj(PIN_FILE, {'pin': '1253'}).get('pin', '1253'))


def set_pin(p):
    wj(PIN_FILE, {'pin': str(p)})


def settings():
    return rj(SETTINGS_FILE, {
        'github_token': '',
        'owner': 'Moneymyck',
        'repo': 'geostar-android',
        'branch': 'main',
        'codes_file': 'codes_geostar.json'
    })


def save_settings(s):
    wj(SETTINGS_FILE, s)


def lab(t, size=15, color=(1, 1, 1, 1), h=40, bold=False, halign='center'):
    x = Label(
        text=str(t), font_size=dp(size), color=color, bold=bold, markup=True,
        size_hint_y=None, height=dp(h), halign=halign, valign='middle'
    )
    x.bind(size=lambda a, b: setattr(a, 'text_size', b))
    return x


def btn(t, bg=(0.1, 0.25, 0.45, 1), h=52):
    return Button(
        text=t, bold=True, color=(1, 1, 1, 1), background_color=bg,
        size_hint_y=None, height=dp(h)
    )


def msg(title, text):
    box = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
    box.add_widget(lab(text, h=220))
    b = btn('OK', bg=(.25, .25, .25, 1), h=48)
    box.add_widget(b)
    p = Popup(title=title, content=box, size_hint=(.9, .55))
    b.bind(on_release=lambda x: p.dismiss())
    p.open()


def http(method, url, payload=None, headers=None, raw_data=None):
    if raw_data is not None:
        data = raw_data
    else:
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {'User-Agent': 'GEOSTAR-ADMIN/4.0'})
    with urllib.request.urlopen(req, timeout=35, context=ctx()) as res:
        raw = res.read().decode('utf-8')
    return json.loads(raw) if raw else None


def gh_headers():
    tok = settings().get('github_token', '').strip()
    if not tok:
        raise Exception('Token GitHub vide. Va dans PARAMÈTRES.')
    return {
        'Authorization': 'Bearer ' + tok,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': 'GEOSTAR-ADMIN/4.0'
    }


def gh_info():
    s = settings()
    return s['owner'].strip(), s['repo'].strip(), s['branch'].strip(), s['codes_file'].strip()


def load_codes():
    owner, repo, branch, path = gh_info()
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}'
    data = http('GET', url, headers=gh_headers())
    sha = data.get('sha')
    content = base64.b64decode(data.get('content', '')).decode('utf-8')
    codes = json.loads(content) if content.strip() else {}
    codes.setdefault('codes_valides', {})
    codes.setdefault('codes_bloques', [])
    return codes, sha


def save_codes(codes, sha, message):
    owner, repo, branch, path = gh_info()
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    content = json.dumps(codes, ensure_ascii=False, indent=2)
    payload = {
        'message': message,
        'content': base64.b64encode(content.encode()).decode(),
        'branch': branch,
        'sha': sha
    }
    return http('PUT', url, payload, gh_headers())


def make_code():
    return 'GEO-' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))


def sb_headers(prefer='return=representation'):
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + SUPABASE_KEY,
        'Content-Type': 'application/json',
        'Prefer': prefer,
        'User-Agent': 'GEOSTAR-ADMIN/4.0'
    }


def sb_storage_headers(content_type='application/json'):
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + SUPABASE_KEY,
        'Content-Type': content_type,
        'User-Agent': 'GEOSTAR-ADMIN/4.0'
    }


def fetch_notes():
    data = http('GET', SUPABASE_URL + '/rest/v1/notes_communaute?select=*&statut=neq.supprime&order=date_soumission.desc', headers=sb_headers())
    return data if isinstance(data, list) else []


def set_note_status(note_id, statut):
    url = SUPABASE_URL + '/rest/v1/notes_communaute?id=eq.' + urllib.parse.quote(str(note_id))
    return http('PATCH', url, {'statut': statut, 'date_validation': datetime.now().isoformat()}, sb_headers('return=minimal'))


def delete_note_real(note_id):
    url = SUPABASE_URL + '/rest/v1/notes_communaute?id=eq.' + urllib.parse.quote(str(note_id))
    return http('DELETE', url, headers=sb_headers('return=minimal'))


def delete_note_and_audio(note):
    """Supprime l'audio Supabase Storage puis la note Supabase."""
    try:
        au = str(note.get('audio_url','') or '')
        if au:
            delete_audio_from_storage(au)
    except Exception:
        pass
    return delete_note_real(note.get('id'))


def audio_path_from_url(url):
    if not url:
        return ''
    text = str(url)
    marker = '/storage/v1/object/public/' + AUDIO_BUCKET + '/'
    if marker in text:
        return urllib.parse.unquote(text.split(marker, 1)[1].split('?', 1)[0])
    marker2 = '/storage/v1/object/' + AUDIO_BUCKET + '/'
    if marker2 in text:
        return urllib.parse.unquote(text.split(marker2, 1)[1].split('?', 1)[0])
    if AUDIO_BUCKET + '/' in text:
        return urllib.parse.unquote(text.split(AUDIO_BUCKET + '/', 1)[1].split('?', 1)[0])
    return ''


def delete_audio_from_storage(audio_url):
    path = audio_path_from_url(audio_url)
    if not path:
        return False
    url = SUPABASE_URL + '/storage/v1/object/' + AUDIO_BUCKET + '/' + urllib.parse.quote(path, safe='/')
    try:
        http('DELETE', url, headers=sb_storage_headers())
        return True
    except Exception:
        return False


def _download_audio_to_cache(url):
    ext = '.3gp'
    clean = str(url).split('?', 1)[0].lower()
    for e in ['.mp3', '.m4a', '.mp4', '.3gp', '.wav', '.ogg', '.aac']:
        if clean.endswith(e):
            ext = e
            break
    filename = 'geostar_admin_audio' + ext
    folder = tempfile.gettempdir()
    path = os.path.join(folder, filename)
    headers = {'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + SUPABASE_KEY, 'User-Agent': 'GEOSTAR-ADMIN/4.0'}
    req = urllib.request.Request(str(url), headers=headers)
    with urllib.request.urlopen(req, timeout=35, context=ctx()) as res:
        data = res.read()
    with open(path, 'wb') as f:
        f.write(data)
    return path


def popup_audio_player(audio_url):
    """Lecture directe depuis l'URL Supabase avec Android MediaPlayer.
    Ne télécharge plus dans Kivy et n'ouvre plus Photos / YouTube Music.
    """
    box = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
    status = lab('Connexion au vocal Supabase...', 14, (1, 1, 1, 1), 90)
    box.add_widget(status)
    row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
    b_play = btn('▶ LIRE', (.0, .42, .18, 1), 50)
    b_stop = btn('■ STOP', (.55, .12, .12, 1), 50)
    row.add_widget(b_play)
    row.add_widget(b_stop)
    box.add_widget(row)
    b_close = btn('FERMER', (.25, .25, .25, 1), 48)
    box.add_widget(b_close)
    p = Popup(title='Lecture vocale', content=box, size_hint=(.92, .45))
    state = {'mp': None, 'ready': False}

    def prepare(dt):
        try:
            from kivy.utils import platform
            if platform != 'android':
                status.text = 'Lecture intégrée disponible surtout sur Android.'
                return
            from jnius import autoclass
            MediaPlayer = autoclass('android.media.MediaPlayer')
            mp = MediaPlayer()
            state['mp'] = mp
            def on_prepared(player):
                state['ready'] = True
                status.text = 'Vocal prêt depuis Supabase. Appuie sur LIRE.'
            def on_error(player, what, extra):
                status.text = 'Erreur lecteur Android : ' + str(what) + ' / ' + str(extra)
                return True
            mp.setOnPreparedListener(on_prepared)
            mp.setOnErrorListener(on_error)
            mp.setDataSource(str(audio_url))
            mp.prepareAsync()
        except Exception as e:
            status.text = 'Impossible de lire directement le vocal :\n' + str(e)[:260]

    def play(_):
        try:
            mp = state.get('mp')
            if not mp:
                status.text = 'Audio non prêt.'
                return
            if not state.get('ready'):
                status.text = 'Chargement en cours, attends quelques secondes.'
                return
            mp.start()
            status.text = 'Lecture en cours depuis Supabase...'
        except Exception as e:
            status.text = 'Erreur lecture : ' + str(e)[:220]

    def stop(_):
        try:
            mp = state.get('mp')
            if mp and mp.isPlaying():
                mp.pause()
                status.text = 'Lecture arrêtée.'
        except Exception:
            pass

    def close(_):
        try:
            mp = state.get('mp')
            if mp:
                if mp.isPlaying():
                    mp.stop()
                mp.release()
                state['mp'] = None
        except Exception:
            pass
        p.dismiss()

    b_play.bind(on_release=play)
    b_stop.bind(on_release=stop)
    b_close.bind(on_release=close)
    p.bind(on_dismiss=lambda *a: close(None) if state.get('mp') else None)
    p.open()
    Clock.schedule_once(prepare, 0.1)


def code_status(info, blocked=False):
    if blocked:
        return 'BLOQUÉ', (.65, .20, .05, 1)
    exp = str(info.get('expire', ''))
    if exp == '2099-12-31':
        return 'À VIE', (.15, .50, .85, 1)
    try:
        d = datetime.strptime(exp, '%Y-%m-%d')
        if d.date() < datetime.now().date():
            return 'EXPIRÉ', (.65, .05, .05, 1)
        return 'ACTIF', (.0, .45, .12, 1)
    except Exception:
        return 'ACTIF', (.0, .45, .12, 1)


class AdminApp(App):
    def build(self):
        self.root = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(12))
        self.login_screen()
        return self.root

    def clear(self):
        self.root.clear_widgets()

    def login_screen(self):
        self.clear()
        self.root.add_widget(Label(size_hint_y=1))
        self.root.add_widget(lab('GEOSTAR ADMIN', 30, (1, .82, 0, 1), 60, True))
        self.pin = TextInput(hint_text='Code PIN admin', password=True, input_filter='int', multiline=False, halign='center', font_size=dp(22), size_hint_y=None, height=dp(56))
        self.root.add_widget(self.pin)
        b = btn('CONNEXION', (.0, .35, .05, 1), 58)
        b.bind(on_release=lambda x: self.do_login())
        self.root.add_widget(b)
        self.info = lab('PIN par défaut : 1253', 14, (.8, .8, .8, 1), 45)
        self.root.add_widget(self.info)
        self.root.add_widget(Label(size_hint_y=1))

    def do_login(self):
        self.home() if self.pin.text.strip() == get_pin() else setattr(self.info, 'text', 'PIN incorrect')

    def home(self):
        self.clear()
        top = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(8))
        top.add_widget(lab('GEOSTAR ADMIN', 22, (1, .82, 0, 1), 55, True))
        bs = btn('PARAMÈTRES', (.15, .15, .28, 1), 55)
        bs.bind(on_release=lambda x: self.settings_screen())
        top.add_widget(bs)
        self.root.add_widget(top)
        for t, f, c in [
            ('+ NOUVEAU CODE', self.create_code, (0, .45, .05, 1)),
            ('GÉRER CODES', self.manage_codes, (.55, .28, 0, 1)),
            ('SYNCHRONISER GITHUB', self.sync, (.05, .25, .55, 1)),
            ('NOTES SUPABASE', self.notes, (.22, .22, .55, 1)),
            ('TESTER SUPABASE', self.test_sb, (.08, .32, .40, 1)),
            ('TESTER GITHUB', self.test_gh, (.18, .18, .35, 1))
        ]:
            b = btn(t, c, 56)
            b.bind(on_release=lambda x, fn=f: fn())
            self.root.add_widget(b)
        self.status = lab('', 14, h=100)
        self.root.add_widget(self.status)
        self.root.add_widget(Label(size_hint_y=1))
        out = btn('SE DÉCONNECTER', (.45, .05, .05, 1), 54)
        out.bind(on_release=lambda x: self.login_screen())
        self.root.add_widget(out)

    def settings_screen(self):
        self.clear()
        s = settings()
        self.root.add_widget(lab('PARAMÈTRES', 24, (1, .82, 0, 1), 55, True))
        self.inputs = []
        for key, hint, pwd in [('github_token', 'Token GitHub', True), ('owner', 'Propriétaire', False), ('repo', 'Dépôt', False), ('branch', 'Branche', False), ('codes_file', 'Fichier codes', False)]:
            self.root.add_widget(lab(hint, 12, (.75, .75, .75, 1), 24))
            inp = TextInput(text=s.get(key, ''), hint_text=hint, password=pwd, multiline=False, size_hint_y=None, height=dp(50))
            self.inputs.append((key, inp))
            self.root.add_widget(inp)
        b = btn('ENREGISTRER PARAMÈTRES', (.05, .25, .55, 1))
        b.bind(on_release=lambda x: self.save_settings_screen())
        self.root.add_widget(b)
        bp = btn('MODIFIER CODE PIN', (.5, .25, 0, 1))
        bp.bind(on_release=lambda x: self.change_pin())
        self.root.add_widget(bp)
        back = btn('< RETOUR', (.25, .25, .25, 1))
        back.bind(on_release=lambda x: self.home())
        self.root.add_widget(back)

    def save_settings_screen(self):
        save_settings({k: i.text.strip() for k, i in self.inputs})
        msg('OK', 'Paramètres enregistrés.')

    def change_pin(self):
        box = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
        old = TextInput(hint_text='Ancien PIN', password=True, input_filter='int', multiline=False, size_hint_y=None, height=dp(50))
        new = TextInput(hint_text='Nouveau PIN 4 chiffres', password=True, input_filter='int', multiline=False, size_hint_y=None, height=dp(50))
        m = lab('', 13, (1, .3, .3, 1), 35)
        save = btn('ENREGISTRER', (0, .45, .05, 1))
        close = btn('FERMER', (.25, .25, .25, 1))
        for w in [old, new, m, save, close]:
            box.add_widget(w)
        p = Popup(title='Modifier PIN', content=box, size_hint=(.9, .58))
        def do(_):
            if old.text.strip() != get_pin():
                m.text = 'Ancien PIN incorrect'; return
            if len(new.text.strip()) != 4 or not new.text.strip().isdigit():
                m.text = 'PIN invalide'; return
            set_pin(new.text.strip()); p.dismiss(); msg('OK', 'PIN modifié')
        save.bind(on_release=do)
        close.bind(on_release=lambda x: p.dismiss())
        p.open()

    def test_sb(self):
        try:
            msg('SUPABASE OK', 'Notes trouvées : ' + str(len(fetch_notes())))
        except Exception as e:
            msg('ERREUR SUPABASE', str(e)[:500])

    def test_gh(self):
        try:
            c, sha = load_codes()
            msg('GITHUB OK', 'Actifs : ' + str(len(c.get('codes_valides', {}))) + '\nBloqués : ' + str(len(c.get('codes_bloques', []))))
        except Exception as e:
            msg('ERREUR GITHUB', str(e)[:500])

    def sync(self):
        try:
            c, sha = load_codes()
            save_codes(c, sha, 'GEOSTAR Admin - synchronisation')
            msg('SYNC OK', 'Synchronisation GitHub réussie.')
        except Exception as e:
            msg('ERREUR SYNC', str(e)[:500])

    def create_code(self):
        box = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
        name = TextInput(hint_text='Nom client', multiline=False, size_hint_y=None, height=dp(50))
        days = TextInput(text='30', hint_text='Durée jours', input_filter='int', multiline=False, size_hint_y=None, height=dp(50))
        m = lab('', h=80)
        create = btn('CRÉER + SYNCHRONISER', (0, .45, .05, 1))
        create_life = btn('CRÉER CODE À VIE', (.15, .15, .45, 1))
        close = btn('FERMER', (.25, .25, .25, 1))
        for w in [lab('Créer un code', 18, (1, .82, 0, 1), 40, True), name, days, m, create, create_life, close]:
            box.add_widget(w)
        p = Popup(title='Nouveau code', content=box, size_hint=(.92, .82))
        def create_with_exp(expire_date):
            try:
                codes, sha = load_codes()
                c = make_code()
                codes['codes_valides'][c] = {
                    'client': name.text.strip() or 'Client',
                    'expire': expire_date,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                save_codes(codes, sha, 'GEOSTAR Admin - nouveau code ' + c)
                m.text = 'CODE CRÉÉ : ' + c + '\nExpire : ' + expire_date
                self.status.text = m.text
            except Exception as e:
                m.text = 'ERREUR : ' + str(e)[:250]
        def do(_):
            try:
                exp = (datetime.now() + timedelta(days=int(days.text or '30'))).strftime('%Y-%m-%d')
                create_with_exp(exp)
            except Exception as e:
                m.text = 'ERREUR : ' + str(e)[:250]
        create.bind(on_release=do)
        create_life.bind(on_release=lambda x: create_with_exp('2099-12-31'))
        close.bind(on_release=lambda x: p.dismiss())
        p.open()

    def manage_codes(self):
        main = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))
        head = lab('Chargement codes...', 16, (1, .82, 0, 1), 40, True)
        main.add_widget(head)
        tools = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(5))
        search = TextInput(hint_text='Recherche code/client', multiline=False, size_hint_x=.52)
        f_all = btn('TOUS', (.18, .18, .30, 1), 46)
        f_active = btn('ACTIFS', (.0, .35, .12, 1), 46)
        f_block = btn('BLOQUÉS', (.55, .20, 0, 1), 46)
        tools.add_widget(search); tools.add_widget(f_all); tools.add_widget(f_active); tools.add_widget(f_block)
        main.add_widget(tools)
        sv = ScrollView(); grid = GridLayout(cols=1, spacing=dp(8), size_hint_y=None); grid.bind(minimum_height=grid.setter('height')); sv.add_widget(grid); main.add_widget(sv)
        close = btn('FERMER', (.25, .25, .25, 1), 46); main.add_widget(close)
        p = Popup(title='Codes GEOSTAR', content=main, size_hint=(.98, .94))
        state = {'filter': 'all', 'codes': None, 'sha': None}
        def load():
            grid.clear_widgets()
            try:
                codes, sha = load_codes(); state['codes'] = codes; state['sha'] = sha
                actifs = len(codes['codes_valides']); bloq = len(codes['codes_bloques'])
                head.text = 'Actifs : ' + str(actifs) + ' | Bloqués : ' + str(bloq)
                q = search.text.strip().lower()
                rows = []
                for c, info in codes['codes_valides'].items():
                    rows.append((c, info, False))
                for c in codes['codes_bloques']:
                    rows.append((c, {}, True))
                for c, info, blocked in rows:
                    if state['filter'] == 'active' and blocked: continue
                    if state['filter'] == 'blocked' and not blocked: continue
                    hay = (c + ' ' + str(info.get('client','')) + ' ' + str(info.get('expire',''))).lower()
                    if q and q not in hay: continue
                    grid.add_widget(self.code_card(c, info, codes, load, blocked))
                if not grid.children:
                    grid.add_widget(lab('Aucun code trouvé.', 14, (.8,.8,.8,1), 80))
            except Exception as e:
                grid.add_widget(lab(str(e)[:500], 12, (1, .3, .3, 1), 160))
        search.bind(text=lambda *a: load())
        f_all.bind(on_release=lambda x: (state.__setitem__('filter', 'all'), load()))
        f_active.bind(on_release=lambda x: (state.__setitem__('filter', 'active'), load()))
        f_block.bind(on_release=lambda x: (state.__setitem__('filter', 'blocked'), load()))
        close.bind(on_release=lambda x: p.dismiss())
        p.open(); load()

    def code_card(self, c, info, codes, reload, blocked):
        status_text, status_col = code_status(info, blocked)
        card = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(5), size_hint_y=None, height=dp(205 if not blocked else 155))
        title = '[b]' + c + '[/b]   [color=#FFD54F]' + status_text + '[/color]\nClient : ' + str(info.get('client','')) + '\nExpire : ' + str(info.get('expire',''))
        card.add_widget(lab(title, 13, (1,1,1,1), 72, False, 'left'))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        def save_action(message):
            _, sha = load_codes(); save_codes(codes, sha, message); reload()
        def prolonger(days=None, life=False):
            try:
                if blocked:
                    msg('Info', 'Débloque le code avant de le prolonger.'); return
                if c not in codes['codes_valides']:
                    msg('Erreur', 'Code introuvable.'); return
                if life:
                    new_exp = '2099-12-31'
                else:
                    old_exp = str(codes['codes_valides'][c].get('expire',''))
                    try: base = datetime.strptime(old_exp, '%Y-%m-%d')
                    except Exception: base = datetime.now()
                    if base < datetime.now(): base = datetime.now()
                    new_exp = (base + timedelta(days=int(days))).strftime('%Y-%m-%d')
                codes['codes_valides'][c]['expire'] = new_exp
                save_action('prolonger ' + c + ' ' + new_exp)
                msg('OK', 'Code prolongé : ' + c + '\nExpire : ' + new_exp)
            except Exception as e:
                msg('Erreur', str(e)[:400])
        def popup_prolonger(_):
            box = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
            box.add_widget(lab('[b]Prolonger ' + c + '[/b]', 18, (1,.82,0,1), 40, True))
            r1 = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
            b7 = btn('+7 JOURS', (.05,.25,.55,1), 48); b30 = btn('+1 MOIS', (.0,.35,.12,1), 48); b365 = btn('+1 AN', (.55,.28,0,1), 48)
            r1.add_widget(b7); r1.add_widget(b30); r1.add_widget(b365); box.add_widget(r1)
            custom = TextInput(hint_text='Autre durée en jours', input_filter='int', multiline=False, size_hint_y=None, height=dp(48)); box.add_widget(custom)
            r2 = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
            bok = btn('AJOUTER', (.0,.45,.05,1), 48); blife = btn('À VIE', (.15,.15,.45,1), 48); bclose = btn('FERMER', (.25,.25,.25,1), 48)
            r2.add_widget(bok); r2.add_widget(blife); r2.add_widget(bclose); box.add_widget(r2)
            p = Popup(title='Prolonger code', content=box, size_hint=(.92,.48))
            b7.bind(on_release=lambda x: (p.dismiss(), prolonger(7)))
            b30.bind(on_release=lambda x: (p.dismiss(), prolonger(30)))
            b365.bind(on_release=lambda x: (p.dismiss(), prolonger(365)))
            bok.bind(on_release=lambda x: (p.dismiss(), prolonger(int(custom.text or '0'))) if int(custom.text or '0') > 0 else msg('Erreur','Entre un nombre de jours.'))
            blife.bind(on_release=lambda x: (p.dismiss(), prolonger(life=True)))
            bclose.bind(on_release=lambda x: p.dismiss())
            p.open()
        if not blocked:
            b1 = btn('BLOQUER', (.55,.25,0,1), 44)
            b1.bind(on_release=lambda x: (codes['codes_valides'].pop(c,None), codes['codes_bloques'].append(c) if c not in codes['codes_bloques'] else None, save_action('bloquer ' + c)))
            row.add_widget(b1)
        else:
            b1 = btn('DÉBLOQUER', (0,.45,.05,1), 44)
            b1.bind(on_release=lambda x: (codes['codes_bloques'].remove(c) if c in codes['codes_bloques'] else None, codes['codes_valides'].__setitem__(c, {'client':'Débloqué','expire':'2099-12-31'}), save_action('debloquer ' + c)))
            row.add_widget(b1)
        b2 = btn('SUPPRIMER', (.5,.05,.05,1), 44)
        b2.bind(on_release=lambda x: (codes['codes_valides'].pop(c,None), codes['codes_bloques'].remove(c) if c in codes['codes_bloques'] else None, save_action('supprimer ' + c)))
        row.add_widget(b2); card.add_widget(row)
        if not blocked:
            quick = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            b7 = btn('+7J', (.05,.25,.55,1), 44); b30 = btn('+1M', (.0,.35,.12,1), 44); bpro = btn('PROLONGER / À VIE', (.15,.15,.45,1), 44)
            b7.bind(on_release=lambda x: prolonger(7)); b30.bind(on_release=lambda x: prolonger(30)); bpro.bind(on_release=popup_prolonger)
            quick.add_widget(b7); quick.add_widget(b30); quick.add_widget(bpro); card.add_widget(quick)
        return card

    def notes(self):
        main = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))
        head = lab('Chargement notes...', 16, (1,.82,0,1), 40, True); main.add_widget(head)
        tools = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(5))
        search = TextInput(hint_text='Recherche note/code/auteur', multiline=False, size_hint_x=.56)
        f_all = btn('TOUTES', (.18,.18,.30,1), 46); f_wait = btn('ATTENTE', (.55,.28,0,1), 46); f_val = btn('VALIDÉ', (0,.38,.12,1), 46)
        tools.add_widget(search); tools.add_widget(f_all); tools.add_widget(f_wait); tools.add_widget(f_val); main.add_widget(tools)
        sv = ScrollView(); grid = GridLayout(cols=1, spacing=dp(8), size_hint_y=None); grid.bind(minimum_height=grid.setter('height')); sv.add_widget(grid); main.add_widget(sv)
        close = btn('FERMER', (.25,.25,.25,1), 46); main.add_widget(close)
        p = Popup(title='Notes Supabase', content=main, size_hint=(.98,.94))
        state = {'filter': 'all'}
        def load():
            grid.clear_widgets()
            try:
                notes = fetch_notes(); head.text = 'Notes : ' + str(len(notes))
                q = search.text.strip().lower()
                shown = 0
                for n in notes:
                    st = str(n.get('statut','attente')).lower()
                    if state['filter'] == 'attente' and st != 'attente': continue
                    if state['filter'] == 'valide' and st != 'valide': continue
                    hay = json.dumps(n, ensure_ascii=False).lower()
                    if q and q not in hay: continue
                    grid.add_widget(self.note_card(n, load)); shown += 1
                if shown == 0:
                    grid.add_widget(lab('Aucune note', h=80))
            except Exception as e:
                grid.add_widget(lab(str(e)[:500], 12, (1,.3,.3,1), 160))
        search.bind(text=lambda *a: load())
        f_all.bind(on_release=lambda x: (state.__setitem__('filter','all'), load()))
        f_wait.bind(on_release=lambda x: (state.__setitem__('filter','attente'), load()))
        f_val.bind(on_release=lambda x: (state.__setitem__('filter','valide'), load()))
        close.bind(on_release=lambda x: p.dismiss())
        p.open(); load()

    def note_card(self, n, reload):
        audio_url = str(n.get('audio_url','') or '')
        st = str(n.get('statut','attente')).lower()
        st_label = st.upper()
        st_col = {'attente': '#FFD54F', 'valide': '#66FF88', 'rejete': '#FF7777'}.get(st, '#DDDDDD')
        h = 330 if audio_url else 280
        card = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(5), size_hint_y=None, height=dp(h))
        code_note = str(n.get('code_activation') or n.get('code_licence') or '')
        auteur = str(n.get('auteur','Anonyme'))
        date_txt = str(n.get('date_soumission') or n.get('created_at') or '')[:19].replace('T', ' ')
        theme = str(n.get('theme_key',''))
        text = str(n.get('texte',''))[:320]
        title = '[b]' + auteur + '[/b]   [color=' + st_col + ']' + st_label + '[/color]'
        if code_note: title += '\nCode : ' + code_note
        if date_txt: title += '\nDate : ' + date_txt
        if theme: title += '\nThème : ' + theme
        card.add_widget(lab(title, 13, (1,1,1,1), 95, False, 'left'))
        card.add_widget(lab(text if text else 'Aucun texte', 12, (.92,.92,.92,1), 80, False, 'left'))
        if audio_url:
            row_audio = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            ba = btn('▶ LECTEUR INTÉGRÉ', (.1,.35,.65,1), 44)
            ba.bind(on_release=lambda x, u=audio_url: popup_audio_player(u))
            row_audio.add_widget(ba); card.add_widget(row_audio)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        for state_txt, col in [('attente',(.55,.28,0,1)), ('valide',(0,.45,.05,1)), ('rejete',(.5,.05,.05,1)), ('supprime',(.18,.18,.18,1))]:
            if state_txt == 'supprime':
                b = btn('SUPPR.', col, 44)
                b.bind(on_release=lambda x, nn=n: (delete_note_and_audio(nn), reload()))
            else:
                b = btn(state_txt.upper(), col, 44)
                b.bind(on_release=lambda x, s=state_txt: (set_note_status(n.get('id'), s), reload()))
            row.add_widget(b)
        card.add_widget(row)
        return card



# ============================================================
# PATCH FINAL ADMIN — SUPPR. = NOTE + AUDIO, AVEC RETOUR VISUEL
# ============================================================
def _admin_final_delete_patch():
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.metrics import dp

    def _delete_note_and_audio_safe(note):
        audio_deleted = False
        note_deleted = False
        errors = []
        try:
            au = str(note.get('audio_url','') or '')
            if au:
                audio_deleted = bool(delete_audio_from_storage(au))
        except Exception as e:
            errors.append('audio: '+str(e)[:120])
        try:
            delete_note_real(note.get('id'))
            note_deleted = True
        except Exception as e:
            errors.append('note delete: '+str(e)[:120])
            # Secours : si Supabase refuse DELETE par RLS, on masque la note en statut supprime.
            try:
                set_note_status(note.get('id'), 'supprime')
                note_deleted = True
            except Exception as e2:
                errors.append('note statut: '+str(e2)[:120])
        return note_deleted, audio_deleted, errors

    def patched_note_card(self, n, reload):
        audio_url = str(n.get('audio_url','') or '')
        st = str(n.get('statut','attente')).lower()
        st_label = st.upper()
        st_col = {'attente': '#FFD54F', 'valide': '#66FF88', 'rejete': '#FF7777'}.get(st, '#DDDDDD')
        h = 315 if audio_url else 265
        card = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(5), size_hint_y=None, height=dp(h))
        code_note = str(n.get('code_activation') or n.get('code_licence') or '')
        auteur = str(n.get('auteur','Anonyme'))
        date_txt = str(n.get('date_soumission') or n.get('created_at') or '')[:19].replace('T', ' ')
        theme = str(n.get('theme_key',''))
        text = str(n.get('texte',''))[:320]
        title = '[b]' + auteur + '[/b]   [color=' + st_col + ']' + st_label + '[/color]'
        if code_note: title += '\nCode : ' + code_note
        if date_txt: title += '\nDate : ' + date_txt
        if theme: title += '\nThème : ' + theme
        card.add_widget(lab(title, 13, (1,1,1,1), 92, False, 'left'))
        card.add_widget(lab(text if text else 'Aucun texte', 12, (.92,.92,.92,1), 68, False, 'left'))
        if audio_url:
            ba = btn('▶ LECTEUR INTÉGRÉ', (.1,.35,.65,1), 44)
            ba.bind(on_release=lambda x, u=audio_url: popup_audio_player(u))
            card.add_widget(ba)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        b_wait = btn('ATTENTE', (.55,.28,0,1), 44)
        b_val = btn('VALIDE', (0,.45,.05,1), 44)
        b_rej = btn('REJETE', (.5,.05,.05,1), 44)
        b_del = btn('SUPPR.', (.18,.18,.18,1), 44)
        b_wait.bind(on_release=lambda x: (set_note_status(n.get('id'), 'attente'), reload()))
        b_val.bind(on_release=lambda x: (set_note_status(n.get('id'), 'valide'), reload()))
        b_rej.bind(on_release=lambda x: (set_note_status(n.get('id'), 'rejete'), reload()))
        def do_delete(btn):
            btn.text = 'SUPPRESSION...'
            ok, aud, errs = _delete_note_and_audio_safe(n)
            reload()
            if not ok:
                msg('Erreur suppression', '\n'.join(errs)[:500] if errs else 'Suppression impossible')
        b_del.bind(on_release=do_delete)
        row.add_widget(b_wait); row.add_widget(b_val); row.add_widget(b_rej); row.add_widget(b_del)
        card.add_widget(row)
        return card
    AdminApp.note_card = patched_note_card

_admin_final_delete_patch()


# ============================================================
# PATCH DEFINITIF ADMIN — SUPPRIMER = NOTE + AUDIO, REJETE RETIRÉ
# ============================================================
def _admin_delete_and_layout_final_patch():
    from kivy.uix.boxlayout import BoxLayout
    from kivy.metrics import dp

    def _delete_note_and_audio_safe(note):
        audio_deleted = False
        note_deleted = False
        errors = []
        au = str(note.get('audio_url','') or '')
        if au:
            try:
                audio_deleted = bool(delete_audio_from_storage(au))
            except Exception as e:
                errors.append('audio: ' + str(e)[:160])
        try:
            delete_note_real(note.get('id'))
            note_deleted = True
        except Exception as e:
            errors.append('delete: ' + str(e)[:160])
            # Si DELETE est bloqué par RLS, on masque vraiment la note côté apps.
            try:
                set_note_status(note.get('id'), 'supprime')
                note_deleted = True
            except Exception as e2:
                errors.append('statut supprime: ' + str(e2)[:160])
        return note_deleted, audio_deleted, errors

    def patched_note_card(self, n, reload):
        audio_url = str(n.get('audio_url','') or '')
        st = str(n.get('statut','attente')).lower()
        st_label = st.upper()
        st_col = {'attente': '#FFD54F', 'valide': '#66FF88', 'rejete': '#FF7777'}.get(st, '#DDDDDD')
        h = 305 if audio_url else 255
        card = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(5), size_hint_y=None, height=dp(h))
        code_note = str(n.get('code_activation') or n.get('code_licence') or '')
        auteur = str(n.get('auteur','Anonyme'))
        date_txt = str(n.get('date_soumission') or n.get('created_at') or '')[:19].replace('T', ' ')
        theme = str(n.get('theme_key',''))
        text = str(n.get('texte',''))[:320]
        title = '[b]' + auteur + '[/b]   [color=' + st_col + ']' + st_label + '[/color]'
        if code_note: title += '\nCode : ' + code_note
        if date_txt: title += '\nDate : ' + date_txt
        if theme: title += '\nThème : ' + theme
        card.add_widget(lab(title, 13, (1,1,1,1), 92, False, 'left'))
        card.add_widget(lab(text if text else 'Aucun texte', 12, (.92,.92,.92,1), 68, False, 'left'))
        if audio_url:
            ba = btn('▶ LECTEUR INTÉGRÉ', (.1,.35,.65,1), 44)
            ba.bind(on_release=lambda x, u=audio_url: popup_audio_player(u))
            card.add_widget(ba)
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        b_wait = btn('ATTENTE', (.55,.28,0,1), 46)
        b_val = btn('VALIDE', (0,.45,.05,1), 46)
        b_del = btn('SUPPRIMER', (.55,.05,.05,1), 46)
        b_wait.bind(on_release=lambda x: (set_note_status(n.get('id'), 'attente'), reload()))
        b_val.bind(on_release=lambda x: (set_note_status(n.get('id'), 'valide'), reload()))
        def do_delete(button):
            button.disabled = True
            button.text = 'SUPPRESSION...'
            ok, aud, errs = _delete_note_and_audio_safe(n)
            reload()
            if not ok:
                msg('Erreur suppression', '\n'.join(errs)[:500] if errs else 'Suppression impossible')
        b_del.bind(on_release=do_delete)
        row.add_widget(b_wait); row.add_widget(b_val); row.add_widget(b_del)
        card.add_widget(row)
        return card

    AdminApp.note_card = patched_note_card

_admin_delete_and_layout_final_patch()


# ============================================================
# PATCH FINAL DEMANDÉ — ADMIN SUPPRIMER FONCTIONNE
# SUPPRIMER = masque immédiatement par statut=supprime, puis tente DELETE réel + audio
# REJETE retiré
# ============================================================
def _admin_suppression_qui_reagit_patch():
    from kivy.uix.boxlayout import BoxLayout
    from kivy.metrics import dp
    import urllib.parse

    def _delete_note_http_raw(note_id):
        url = SUPABASE_URL + '/rest/v1/notes_communaute?id=eq.' + urllib.parse.quote(str(note_id))
        return http('DELETE', url, headers=sb_headers('return=minimal'))

    def _delete_everything(note):
        errs = []
        note_id = note.get('id')
        au = str(note.get('audio_url','') or '')

        # 1) Le plus important pour l'app : faire disparaître tout de suite.
        # PATCH fonctionne déjà avec ATTENTE/VALIDE, donc SUPPRIMER utilise la même logique fiable.
        try:
            set_note_status(note_id, 'supprime')
        except Exception as e:
            errs.append('statut supprime: ' + str(e)[:180])

        # 2) Supprimer l'audio storage si possible.
        if au:
            try:
                delete_audio_from_storage(au)
            except Exception as e:
                errs.append('audio: ' + str(e)[:180])

        # 3) Tenter le vrai DELETE de la ligne. Si Supabase/RLS refuse, la note reste masquée.
        try:
            _delete_note_http_raw(note_id)
        except Exception as e:
            # On ne bloque plus le bouton pour ça, car le masquage statut=supprime est déjà fait.
            pass

        return errs

    def patched_note_card(self, n, reload):
        audio_url = str(n.get('audio_url','') or '')
        st = str(n.get('statut','attente')).lower()
        st_label = st.upper()
        st_col = {'attente': '#FFD54F', 'valide': '#66FF88', 'rejete': '#FF7777', 'supprime':'#999999'}.get(st, '#DDDDDD')
        h = 305 if audio_url else 255
        card = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(5), size_hint_y=None, height=dp(h))
        code_note = str(n.get('code_activation') or n.get('code_licence') or '')
        auteur = str(n.get('auteur','Anonyme'))
        date_txt = str(n.get('date_soumission') or n.get('created_at') or '')[:19].replace('T', ' ')
        theme = str(n.get('theme_key',''))
        text = str(n.get('texte',''))[:320]
        title = '[b]' + auteur + '[/b]   [color=' + st_col + ']' + st_label + '[/color]'
        if code_note: title += '\nCode : ' + code_note
        if date_txt: title += '\nDate : ' + date_txt
        if theme: title += '\nThème : ' + theme
        card.add_widget(lab(title, 13, (1,1,1,1), 92, False, 'left'))
        card.add_widget(lab(text if text else 'Aucun texte', 12, (.92,.92,.92,1), 68, False, 'left'))
        if audio_url:
            ba = btn('▶ LECTEUR INTÉGRÉ', (.1,.35,.65,1), 44)
            ba.bind(on_release=lambda x, u=audio_url: popup_audio_player(u))
            card.add_widget(ba)

        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        b_wait = btn('ATTENTE', (.55,.28,0,1), 46)
        b_val = btn('VALIDE', (0,.45,.05,1), 46)
        b_del = btn('SUPPRIMER', (.55,.05,.05,1), 46)

        b_wait.bind(on_release=lambda x, nid=n.get('id'): (set_note_status(nid, 'attente'), reload()))
        b_val.bind(on_release=lambda x, nid=n.get('id'): (set_note_status(nid, 'valide'), reload()))

        def do_delete(button, note=n):
            button.text = 'SUPPRESSION...'
            button.disabled = True
            errs = _delete_everything(note)
            reload()
            if errs:
                msg('Info suppression', 'La note est masquée dans l’app.\nDétail : ' + '\n'.join(errs)[:420])
        b_del.bind(on_release=do_delete)

        row.add_widget(b_wait)
        row.add_widget(b_val)
        row.add_widget(b_del)
        card.add_widget(row)
        return card

    AdminApp.note_card = patched_note_card

_admin_suppression_qui_reagit_patch()


if __name__ == '__main__':
    AdminApp().run()
