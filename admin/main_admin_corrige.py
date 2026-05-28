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
import os, json, ssl, base64, random, string, urllib.request, urllib.parse
from datetime import datetime, timedelta

Window.clearcolor = (0.04,0.04,0.06,1)
SUPABASE_URL='https://kvgjghvcptryghggzuui.supabase.co'
SUPABASE_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt2Z2pnaHZjcHRyeWdoZ2d6dXVpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk3MDkxMzcsImV4cCI6MjA5NTI4NTEzN30.IzYhPAOUv50RmCVTe8KUaM2F4efyewgmxj-D9QVVjMU'
SETTINGS_FILE='geostar_admin_settings.json'; PIN_FILE='geostar_admin_pin.json'

def ctx():
    c=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); c.check_hostname=False; c.verify_mode=ssl.CERT_NONE; return c

def rj(path, default):
    try:
        if os.path.exists(path):
            return json.load(open(path,'r',encoding='utf-8'))
    except Exception: pass
    return default

def wj(path, data): json.dump(data, open(path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
def get_pin(): return str(rj(PIN_FILE,{'pin':'1253'}).get('pin','1253'))
def set_pin(p): wj(PIN_FILE, {'pin':str(p)})
def settings(): return rj(SETTINGS_FILE, {'github_token':'','owner':'Moneymyck','repo':'geostar-android','branch':'main','codes_file':'codes_geostar.json'})
def save_settings(s): wj(SETTINGS_FILE,s)

def lab(t, size=15, color=(1,1,1,1), h=40, bold=False):
    x=Label(text=str(t),font_size=dp(size),color=color,bold=bold,markup=True,size_hint_y=None,height=dp(h),halign='center',valign='middle')
    x.bind(size=lambda a,b:setattr(a,'text_size',b)); return x

def btn(t,bg=(0.1,0.25,0.45,1),h=52): return Button(text=t,bold=True,color=(1,1,1,1),background_color=bg,size_hint_y=None,height=dp(h))
def msg(title, text):
    box=BoxLayout(orientation='vertical',padding=dp(12),spacing=dp(10)); box.add_widget(lab(text,h=220)); b=btn('OK',bg=(.25,.25,.25,1),h=48); box.add_widget(b)
    p=Popup(title=title,content=box,size_hint=(.9,.55)); b.bind(on_release=lambda x:p.dismiss()); p.open()

def http(method,url,payload=None,headers=None):
    data=json.dumps(payload).encode('utf-8') if payload is not None else None
    req=urllib.request.Request(url,data=data,method=method,headers=headers or {'User-Agent':'GEOSTAR-ADMIN/3.1'})
    with urllib.request.urlopen(req,timeout=25,context=ctx()) as res:
        raw=res.read().decode('utf-8')
    return json.loads(raw) if raw else None

def gh_headers():
    tok=settings().get('github_token','').strip()
    if not tok: raise Exception('Token GitHub vide. Va dans PARAMÈTRES.')
    return {'Authorization':'Bearer '+tok,'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'GEOSTAR-ADMIN/3.1'}
def gh_info():
    s=settings(); return s['owner'].strip(),s['repo'].strip(),s['branch'].strip(),s['codes_file'].strip()
def load_codes():
    owner,repo,branch,path=gh_info(); url=f'https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}'
    data=http('GET',url,headers=gh_headers()); sha=data.get('sha'); content=base64.b64decode(data.get('content','')).decode('utf-8')
    codes=json.loads(content) if content.strip() else {}; codes.setdefault('codes_valides',{}); codes.setdefault('codes_bloques',[]); return codes,sha
def save_codes(codes,sha,message):
    owner,repo,branch,path=gh_info(); url=f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    content=json.dumps(codes,ensure_ascii=False,indent=2)
    payload={'message':message,'content':base64.b64encode(content.encode()).decode(),'branch':branch,'sha':sha}
    return http('PUT',url,payload,gh_headers())
def make_code(): return 'GEO-'+''.join(random.choice(string.ascii_uppercase+string.digits) for _ in range(4))

def sb_headers(prefer='return=representation'):
    return {'apikey':SUPABASE_KEY,'Authorization':'Bearer '+SUPABASE_KEY,'Content-Type':'application/json','Prefer':prefer,'User-Agent':'GEOSTAR-ADMIN/3.1'}
def fetch_notes():
    data=http('GET',SUPABASE_URL+'/rest/v1/notes_communaute?select=*&statut=neq.supprime&order=date_soumission.desc',headers=sb_headers()); return data if isinstance(data,list) else []
def set_note_status(note_id,statut):
    url=SUPABASE_URL+'/rest/v1/notes_communaute?id=eq.'+urllib.parse.quote(str(note_id)); return http('PATCH',url,{'statut':statut,'date_validation':datetime.now().isoformat()},sb_headers('return=minimal'))


def delete_note_real(note_id):
    import urllib.parse
    url = SUPABASE_URL + "/rest/v1/notes_communaute?id=eq." + urllib.parse.quote(str(note_id))
    try:
        return http("DELETE", url, headers=sb_headers("return=minimal"))
    except Exception:
        try:
            return http_json("DELETE", url, headers=sb_headers("return=minimal"))
        except TypeError:
            return requests.delete(url, headers=sb_headers("return=minimal"))


class AdminApp(App):
    def build(self): self.root=BoxLayout(orientation='vertical',padding=dp(18),spacing=dp(12)); self.login_screen(); return self.root
    def clear(self): self.root.clear_widgets()
    def login_screen(self):
        self.clear(); self.root.add_widget(Label(size_hint_y=1)); self.root.add_widget(lab('GEOSTAR ADMIN',30,(1,.82,0,1),60,True))
        self.pin=TextInput(hint_text='Code PIN admin',password=True,input_filter='int',multiline=False,halign='center',font_size=dp(22),size_hint_y=None,height=dp(56)); self.root.add_widget(self.pin)
        b=btn('CONNEXION',(.0,.35,.05,1),58); b.bind(on_release=lambda x:self.do_login()); self.root.add_widget(b)
        self.info=lab('PIN par défaut : 1253',14,(.8,.8,.8,1),45); self.root.add_widget(self.info); self.root.add_widget(Label(size_hint_y=1))
    def do_login(self): self.home() if self.pin.text.strip()==get_pin() else setattr(self.info,'text','PIN incorrect')
    def home(self):
        self.clear(); top=BoxLayout(size_hint_y=None,height=dp(55),spacing=dp(8)); top.add_widget(lab('GEOSTAR ADMIN',22,(1,.82,0,1),55,True)); bs=btn('PARAMÈTRES',(.15,.15,.28,1),55); bs.bind(on_release=lambda x:self.settings_screen()); top.add_widget(bs); self.root.add_widget(top)
        for t,f,c in [('+ NOUVEAU CODE',self.create_code,(0,.45,.05,1)),('GÉRER CODES',self.manage_codes,(.55,.28,0,1)),('SYNCHRONISER GITHUB',self.sync,(.05,.25,.55,1)),('NOTES SUPABASE',self.notes,(.22,.22,.55,1)),('TESTER SUPABASE',self.test_sb,(.08,.32,.40,1)),('TESTER GITHUB',self.test_gh,(.18,.18,.35,1))]:
            b=btn(t,c,56); b.bind(on_release=lambda x,fn=f:fn()); self.root.add_widget(b)
        self.status=lab('',14,h=100); self.root.add_widget(self.status); self.root.add_widget(Label(size_hint_y=1)); out=btn('SE DÉCONNECTER',(.45,.05,.05,1),54); out.bind(on_release=lambda x:self.login_screen()); self.root.add_widget(out)
    def settings_screen(self):
        self.clear(); s=settings(); self.root.add_widget(lab('PARAMÈTRES',24,(1,.82,0,1),55,True)); self.inputs=[]
        for key,hint,pwd in [('github_token','Token GitHub',True),('owner','Propriétaire',False),('repo','Dépôt',False),('branch','Branche',False),('codes_file','Fichier codes',False)]:
            self.root.add_widget(lab(hint,12,(.75,.75,.75,1),24)); inp=TextInput(text=s.get(key,''),hint_text=hint,password=pwd,multiline=False,size_hint_y=None,height=dp(50)); self.inputs.append((key,inp)); self.root.add_widget(inp)
        b=btn('ENREGISTRER PARAMÈTRES',(.05,.25,.55,1)); b.bind(on_release=lambda x:self.save_settings_screen()); self.root.add_widget(b); bp=btn('MODIFIER CODE PIN',(.5,.25,0,1)); bp.bind(on_release=lambda x:self.change_pin()); self.root.add_widget(bp); back=btn('< RETOUR',(.25,.25,.25,1)); back.bind(on_release=lambda x:self.home()); self.root.add_widget(back)
    def save_settings_screen(self): save_settings({k:i.text.strip() for k,i in self.inputs}); msg('OK','Paramètres enregistrés.')
    def change_pin(self):
        box=BoxLayout(orientation='vertical',padding=dp(12),spacing=dp(10)); old=TextInput(hint_text='Ancien PIN',password=True,input_filter='int',multiline=False,size_hint_y=None,height=dp(50)); new=TextInput(hint_text='Nouveau PIN 4 chiffres',password=True,input_filter='int',multiline=False,size_hint_y=None,height=dp(50)); m=lab('',13,(1,.3,.3,1),35); save=btn('ENREGISTRER',(0,.45,.05,1)); box.add_widget(old); box.add_widget(new); box.add_widget(m); box.add_widget(save); p=Popup(title='Modifier PIN',content=box,size_hint=(.9,.5))
        def do(_):
            if old.text.strip()!=get_pin(): m.text='Ancien PIN incorrect'; return
            if len(new.text.strip())!=4 or not new.text.strip().isdigit(): m.text='PIN invalide'; return
            set_pin(new.text.strip()); p.dismiss(); msg('OK','PIN modifié')
        save.bind(on_release=do); p.open()
    def test_sb(self):
        try: msg('SUPABASE OK','Notes trouvées : '+str(len(fetch_notes())))
        except Exception as e: msg('ERREUR SUPABASE',str(e)[:500])
    def test_gh(self):
        try: c,sha=load_codes(); msg('GITHUB OK','Actifs : '+str(len(c.get('codes_valides',{})))+'\nBloqués : '+str(len(c.get('codes_bloques',[]))))
        except Exception as e: msg('ERREUR GITHUB',str(e)[:500])
    def sync(self):
        try: c,sha=load_codes(); save_codes(c,sha,'GEOSTAR Admin - synchronisation'); msg('SYNC OK','Synchronisation GitHub réussie.')
        except Exception as e: msg('ERREUR SYNC',str(e)[:500])
    def create_code(self):
        box=BoxLayout(orientation='vertical',padding=dp(12),spacing=dp(10)); name=TextInput(hint_text='Nom client',multiline=False,size_hint_y=None,height=dp(50)); days=TextInput(text='30',hint_text='Durée jours',input_filter='int',multiline=False,size_hint_y=None,height=dp(50)); m=lab('',h=80); create=btn('CRÉER + SYNCHRONISER',(0,.45,.05,1)); [box.add_widget(w) for w in [lab('Créer un code',18,(1,.82,0,1),40,True),name,days,m,create]]; p=Popup(title='Nouveau code',content=box,size_hint=(.92,.65))
        def do(_):
            try:
                codes,sha=load_codes(); c=make_code(); exp=(datetime.now()+timedelta(days=int(days.text or '30'))).strftime('%Y-%m-%d'); codes['codes_valides'][c]={'client':name.text.strip() or 'Client','expire':exp,'created_at':datetime.now().strftime('%Y-%m-%d %H:%M')}; save_codes(codes,sha,'GEOSTAR Admin - nouveau code '+c); m.text='CODE CRÉÉ : '+c+'\nExpire : '+exp; self.status.text=m.text
            except Exception as e: m.text='ERREUR : '+str(e)[:250]
        create.bind(on_release=do); p.open()
    def manage_codes(self):
        main=BoxLayout(orientation='vertical',padding=dp(8),spacing=dp(8)); head=lab('Chargement codes...',16,(1,.82,0,1),40,True); main.add_widget(head); sv=ScrollView(); grid=GridLayout(cols=1,spacing=dp(8),size_hint_y=None); grid.bind(minimum_height=grid.setter('height')); sv.add_widget(grid); main.add_widget(sv); close=btn('FERMER',(.25,.25,.25,1),46); main.add_widget(close); p=Popup(title='Codes GEOSTAR',content=main,size_hint=(.96,.92))
        def load():
            grid.clear_widgets()
            try:
                codes,sha=load_codes(); head.text='Actifs : '+str(len(codes['codes_valides']))+' | Bloqués : '+str(len(codes['codes_bloques']))
                for c,info in codes['codes_valides'].items(): grid.add_widget(self.code_card(c,info,codes,load,False))
                for c in codes['codes_bloques']: grid.add_widget(self.code_card(c,{},codes,load,True))
            except Exception as e: grid.add_widget(lab(str(e)[:500],12,(1,.3,.3,1),160))
        close.bind(on_release=lambda x:p.dismiss()); p.open(); load()
    def code_card(self,c,info,codes,reload,blocked):
        card=BoxLayout(orientation='vertical',padding=dp(8),spacing=dp(5),size_hint_y=None,height=dp(190))
        card.add_widget(lab('[b]'+c+'[/b]\nClient : '+str(info.get('client',''))+'\nExpire : '+str(info.get('expire','')),13,h=65))
        row=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(6))

        def save_action(message):
            _,sha=load_codes()
            save_codes(codes,sha,message)
            reload()

        def prolonger_jours(days):
            try:
                if blocked:
                    msg('Impossible','Ce code est bloqué. Débloque-le avant de le prolonger.')
                    return
                exp_txt=str(info.get('expire','')).strip() or datetime.now().strftime('%Y-%m-%d')
                try:
                    exp=datetime.strptime(exp_txt,'%Y-%m-%d')
                except Exception:
                    exp=datetime.now()
                if exp < datetime.now():
                    exp=datetime.now()
                exp=exp+timedelta(days=int(days))
                codes['codes_valides'][c]['expire']=exp.strftime('%Y-%m-%d')
                save_action('prolonger '+c+' +'+str(days)+' jours')
            except Exception as e:
                msg('Erreur prolongation',str(e)[:400])

        def popup_prolonger(_):
            box=BoxLayout(orientation='vertical',padding=dp(12),spacing=dp(8))
            box.add_widget(lab('Prolonger le code\n'+c,17,(1,.82,0,1),55,True))
            row1=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(6))
            for txt,days,col in [('+7 jours',7,(.1,.4,.7,1)),('+1 mois',30,(.1,.5,.3,1)),('+1 année',365,(.55,.32,.05,1))]:
                b=btn(txt,col,48)
                b.bind(on_release=lambda x,d=days:(p.dismiss(),prolonger_jours(d)))
                row1.add_widget(b)
            box.add_widget(row1)
            duree=TextInput(text='30',hint_text='Nombre',input_filter='int',multiline=False,size_hint_y=None,height=dp(48))
            unite=TextInput(text='jours',hint_text='jours / mois / annees',multiline=False,size_hint_y=None,height=dp(48))
            box.add_widget(duree)
            box.add_widget(unite)
            bvalid=btn('VALIDER DURÉE PERSONNALISÉE',(0,.45,.05,1),50)
            bclose=btn('ANNULER',(.25,.25,.25,1),46)
            box.add_widget(bvalid)
            box.add_widget(bclose)
            p=Popup(title='Prolonger',content=box,size_hint=(.92,.62))

            def valid(_):
                n=int(duree.text or '0')
                u=unite.text.strip().lower()
                if n<=0:
                    msg('Erreur','Entre une durée positive.')
                    return
                if u.startswith('mois') or u.startswith('m'):
                    days=n*30
                elif u.startswith('an') or u.startswith('ann') or u.startswith('a'):
                    days=n*365
                else:
                    days=n
                p.dismiss()
                prolonger_jours(days)

            bvalid.bind(on_release=valid)
            bclose.bind(on_release=lambda x:p.dismiss())
            p.open()

        if not blocked:
            b1=btn('BLOQUER',(.55,.25,0,1),44)
            b1.bind(on_release=lambda x:(codes['codes_valides'].pop(c,None), codes['codes_bloques'].append(c) if c not in codes['codes_bloques'] else None, save_action('bloquer '+c)))
            row.add_widget(b1)
        else:
            b1=btn('DÉBLOQUER',(0,.45,.05,1),44)
            b1.bind(on_release=lambda x:(codes['codes_bloques'].remove(c) if c in codes['codes_bloques'] else None, codes['codes_valides'].__setitem__(c,{'client':'Débloqué','expire':'2099-12-31'}), save_action('debloquer '+c)))
            row.add_widget(b1)

        b2=btn('SUPPRIMER',(.5,.05,.05,1),44)
        b2.bind(on_release=lambda x:(codes['codes_valides'].pop(c,None), codes['codes_bloques'].remove(c) if c in codes['codes_bloques'] else None, save_action('supprimer '+c)))
        row.add_widget(b2)
        card.add_widget(row)

        row2=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(6))
        if not blocked:
            for txt,days,col in [('+7J',7,(.1,.4,.7,1)),('+1M',30,(.1,.5,.3,1)),('+1A',365,(.55,.32,.05,1))]:
                b=btn(txt,col,44)
                b.bind(on_release=lambda x,d=days:prolonger_jours(d))
                row2.add_widget(b)
            bc=btn('AUTRE',(.22,.22,.55,1),44)
            bc.bind(on_release=popup_prolonger)
            row2.add_widget(bc)
        else:
            row2.add_widget(lab('Code bloqué : débloque avant prolongation.',12,(1,.55,.25,1),44))
        card.add_widget(row2)
        return card

    def notes(self):
        main=BoxLayout(orientation='vertical',padding=dp(8),spacing=dp(8)); head=lab('Chargement notes...',16,(1,.82,0,1),40,True); main.add_widget(head); sv=ScrollView(); grid=GridLayout(cols=1,spacing=dp(8),size_hint_y=None); grid.bind(minimum_height=grid.setter('height')); sv.add_widget(grid); main.add_widget(sv); close=btn('FERMER',(.25,.25,.25,1),46); main.add_widget(close); p=Popup(title='Notes Supabase',content=main,size_hint=(.96,.92))
        def load():
            grid.clear_widgets()
            try:
                notes=fetch_notes(); head.text='Notes : '+str(len(notes))
                if not notes: grid.add_widget(lab('Aucune note',h=80))
                for n in notes: grid.add_widget(self.note_card(n,load))
            except Exception as e: grid.add_widget(lab(str(e)[:500],12,(1,.3,.3,1),160))
        close.bind(on_release=lambda x:p.dismiss()); p.open(); load()
    def note_card(self,n,reload):
        code_user = (
            n.get('code_activation')
            or n.get('code_utilisateur')
            or n.get('user_code')
            or n.get('activation_code')
            or n.get('code')
            or 'Aucun'
        )
        audio_url = (
            n.get('audio_url')
            or n.get('vocal_url')
            or n.get('audio')
            or n.get('vocal')
            or ''
        )
        hauteur = dp(270) if audio_url else dp(225)
        card=BoxLayout(orientation='vertical',padding=dp(8),spacing=dp(4),size_hint_y=None,height=hauteur)
        txt='[b]'+str(n.get('auteur','Anonyme'))+'[/b] | '+str(n.get('statut','attente')).upper()+'\nCode utilisateur : '+str(code_user)+'\nThème : '+str(n.get('theme_key',''))+'\n\n'+str(n.get('texte',''))[:250]
        card.add_widget(lab(txt,13,h=140))
        row=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(6))

        def action_note(st):
            try:
                if st == 'supprime':
                    delete_note_real(n.get('id'))
                else:
                    set_note_status(n.get('id'),st)
                reload()
            except Exception as e:
                msg('Erreur note',str(e)[:500])

        for st,col,label in [('attente',(.55,.28,0,1),'ATTENTE'),('valide',(0,.45,.05,1),'VALIDER'),('rejete',(.5,.05,.05,1),'REJETER'),('supprime',(.18,.18,.18,1),'SUPPRIMER')]:
            b=btn(label,col,44)
            b.bind(on_release=lambda x,s=st:action_note(s))
            row.add_widget(b)
        card.add_widget(row)

        if audio_url:
            ba=btn('LIRE AUDIO',(.1,.4,.7,1),44)

            def lire_audio(_):
                try:
                    import webbrowser
                    webbrowser.open(str(audio_url))
                except Exception as e:
                    msg('Erreur audio',str(e)[:400])

            ba.bind(on_release=lire_audio)
            card.add_widget(ba)

        return card


# ============================================================
# PATCH ADMIN — SUPPRIMER = DELETE RÉEL SUPABASE
# ============================================================

def _admin_delete_real_supabase_patch():
    old_set_note = getattr(AdminApp, "set_note", None)
    old_update_note = globals().get("note_status", globals().get("update_note_status", None))

    def set_note_real(self, note_id, st, reload):
        try:
            if st == "supprime":
                delete_note_real(note_id)
                reload()
                return
            if old_set_note:
                return old_set_note(self, note_id, st, reload)
            if old_update_note:
                old_update_note(note_id, st)
            reload()
        except Exception as e:
            alert("Erreur", str(e)[:400])

    AdminApp.set_note = set_note_real

_admin_delete_real_supabase_patch()


if __name__ == '__main__':
    AdminApp().run()
