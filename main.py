import os, socket, threading, json
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
os.environ["KIVY_NO_ENV_CONFIG"] = "1"
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.properties import BooleanProperty
CONFIG_FILE = Path("videobot_config.json")
VIDEO_DIR = Path("videos")
VIDEO_DIR.mkdir(exist_ok=True)
def cargar_config():
    d = {"bot_token": "", "web_port": "8080"}
    if CONFIG_FILE.exists():
        try: return {**d, **json.loads(CONFIG_FILE.read_text())}
        except: pass
    return d
def guardar_config(cfg): CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
def get_ip():
    try:
        s = socket.socket(); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except: return "Sin red"
BG=(0.05,0.05,0.09,1); CARD=(0.10,0.10,0.15,1); ACCENT=(0.16,0.47,1.00,1)
GREEN=(0.13,0.73,0.44,1); RED=(0.93,0.27,0.27,1); TEXT=(0.93,0.93,0.93,1); SUB=(0.55,0.55,0.65,1)
_httpd=None; _bot=None
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p=urllib.parse.unquote(self.path)
        if p in("/","/index.html"):
            exts=('.mp4','.mkv','.avi','.mov','.webm')
            vids=sorted([f for f in VIDEO_DIR.iterdir() if f.suffix.lower() in exts],key=lambda f:f.stat().st_mtime,reverse=True)
            cards=''.join(f'<div style="background:#1a1a1a;border-radius:10px;overflow:hidden;margin:10px"><video controls width=100% style="max-height:200px"><source src=/videos/{urllib.parse.quote(v.name)} type=video/mp4></video><div style="padding:10px;color:#eee">{v.name} ({v.stat().st_size/1048576:.1f}MB)</div></div>' for v in vids)
            html=f'<!DOCTYPE html><html><head><meta charset=UTF-8><meta name=viewport content=width=device-width,initial-scale=1><title>VideoBot TV</title><style>body{{background:#0d0d0d;font-family:sans-serif}}header{{background:#1a1a2e;padding:20px;color:#fff}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));padding:16px}}</style></head><body><header><h1>VideoBot TV ({len(vids)} videos)</h1></header><div class=grid>{cards if vids else "<p style=color:#666;padding:40px>Envia videos al bot de Telegram</p>"}</div></body></html>'.encode()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(html))); self.end_headers(); self.wfile.write(html)
        elif p.startswith("/videos/"):
            fp=VIDEO_DIR/p[8:]
            if fp.exists():
                data=fp.read_bytes(); self.send_response(200); self.send_header("Content-Type","video/mp4"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
            else: self.send_error(404)
        else: self.send_error(404)
    def log_message(self,*a): pass
def iniciar_bot(token):
    import subprocess,sys
    subprocess.run([sys.executable,"-m","pip","install","-q","python-telegram-bot==20.7"],check=False)
    try:
        from telegram.ext import Application,CommandHandler,MessageHandler,filters
        import asyncio
        async def start(u,c): await u.message.reply_text("Bot activo!\n/lista - ver videos\n/ip - URL para TV\n/borrar nombre.mp4")
        async def lista(u,c):
            vids=[f for f in VIDEO_DIR.iterdir() if f.suffix.lower() in('.mp4','.mkv','.avi','.mov','.webm')]
            await u.message.reply_text("Sin videos aun" if not vids else "\n".join(f"{v.name} ({v.stat().st_size/1048576:.1f}MB)" for v in vids))
        async def ip_cmd(u,c): await u.message.reply_text(f"Abre en tu TV:\nhttp://{get_ip()}:{cargar_config().get('web_port','8080')}")
        async def borrar(u,c):
            if not c.args: await u.message.reply_text("Uso: /borrar nombre.mp4"); return
            fp=VIDEO_DIR/" ".join(c.args)
            if fp.exists(): fp.unlink(); await u.message.reply_text("Borrado!")
            else: await u.message.reply_text("No encontrado")
        async def video_msg(u,c):
            vid=u.message.video or u.message.document
            if not vid: await u.message.reply_text("Envia un video"); return
            nombre=getattr(vid,"file_name",None) or f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            dest=VIDEO_DIR/nombre; av=await u.message.reply_text(f"Descargando {nombre}...")
            try:
                f=await c.bot.get_file(vid.file_id); await f.download_to_drive(str(dest))
                await av.edit_text(f"Guardado! {nombre} ({dest.stat().st_size/1048576:.1f}MB)")
            except Exception as e: await av.edit_text(f"Error: {e}")
        loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        global _bot; _bot=Application.builder().token(token).build()
        for cmd,fn in [("start",start),("lista",lista),("ip",ip_cmd),("borrar",borrar)]:
            _bot.add_handler(CommandHandler(cmd,fn))
        _bot.add_handler(MessageHandler(filters.VIDEO|filters.Document.VIDEO,video_msg))
        _bot.run_polling(drop_pending_updates=True)
    except Exception as e: print(f"[BOT ERROR] {e}")
class CardBox(BoxLayout):
    def __init__(self,**kw): super().__init__(**kw); self.bind(pos=self._d,size=self._d)
    def _d(self,*_):
        self.canvas.before.clear()
        with self.canvas.before: Color(*CARD); RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(14)])
class RBtn(Button):
    def __init__(self,bg=None,**kw):
        super().__init__(**kw); self._bg=bg or ACCENT
        self.background_color=(0,0,0,0); self.background_normal=""; self.color=(1,1,1,1); self.bold=True; self.font_size=dp(15); self.bind(pos=self._d,size=self._d)
    def _d(self,*_):
        self.canvas.before.clear()
        with self.canvas.before: Color(*self._bg); RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(10)])
class ConfigScreen(Screen):
    def __init__(self,**kw):
        super().__init__(**kw); cfg=cargar_config()
        root=BoxLayout(orientation="vertical",padding=dp(20),spacing=dp(14))
        with root.canvas.before: Color(*BG); self._bg=Rectangle(pos=root.pos,size=root.size)
        root.bind(pos=lambda *_:setattr(self._bg,"pos",root.pos),size=lambda *_:setattr(self._bg,"size",root.size))
        root.add_widget(Label(text="Configuracion",font_size=dp(22),bold=True,color=TEXT,size_hint_y=None,height=dp(48)))
        for label,attr,hint in [("Token Bot Telegram","tok","123456789:AAF..."),("Puerto web","port","8080")]:
            card=CardBox(orientation="vertical",padding=dp(14),spacing=dp(8),size_hint_y=None,height=dp(116))
            card.add_widget(Label(text=label,font_size=dp(13),color=SUB,size_hint_y=None,height=dp(22)))
            inp=TextInput(text=cfg.get("bot_token" if attr=="tok" else "web_port","" if attr=="tok" else "8080"),hint_text=hint,multiline=False,font_size=dp(13),background_color=(0.08,0.08,0.13,1),foreground_color=TEXT,size_hint_y=None,height=dp(44),padding=[dp(10),dp(10)])
            setattr(self,attr,inp); card.add_widget(inp); root.add_widget(card)
        root.add_widget(Label())
        b1=RBtn(text="Guardar",size_hint_y=None,height=dp(52)); b1.bind(on_press=self.save); root.add_widget(b1)
        b2=RBtn(text="Volver",bg=CARD,size_hint_y=None,height=dp(46)); b2.bind(on_press=lambda *_:setattr(self.manager,"current","panel")); root.add_widget(b2)
        self.add_widget(root)
    def save(self,*_):
        guardar_config({"bot_token":self.tok.text.strip(),"web_port":self.port.text.strip() or "8080"})
        Popup(title="Guardado",content=Label(text="Configuracion guardada.",color=TEXT),size_hint=(.75,.28)).open()
class PanelScreen(Screen):
    srv_on=BooleanProperty(False); bot_on=BooleanProperty(False)
    def __init__(self,**kw): super().__init__(**kw); self._build(); Clock.schedule_interval(self._refresh,3)
    def _build(self):
        root=BoxLayout(orientation="vertical",padding=dp(14),spacing=dp(10))
        with root.canvas.before: Color(*BG); self._bg=Rectangle(pos=root.pos,size=root.size)
        root.bind(pos=lambda *_:setattr(self._bg,"pos",root.pos),size=lambda *_:setattr(self._bg,"size",root.size))
        hdr=BoxLayout(size_hint_y=None,height=dp(50),spacing=dp(8))
        hdr.add_widget(Label(text="VideoBot",font_size=dp(22),bold=True,color=TEXT))
        cfg_btn=RBtn(text="Cfg",size_hint_x=None,width=dp(60),bg=(0.15,0.15,0.22,1)); cfg_btn.bind(on_press=lambda *_:setattr(self.manager,"current","config")); hdr.add_widget(cfg_btn); root.add_widget(hdr)
        ip_c=CardBox(orientation="vertical",padding=dp(12),spacing=dp(4),size_hint_y=None,height=dp(76))
        ip_c.add_widget(Label(text="URL Smart TV",font_size=dp(12),color=SUB,size_hint_y=None,height=dp(20)))
        self.lbl_ip=Label(text="Inicia servidor para ver URL",font_size=dp(14),bold=True,color=ACCENT,size_hint_y=None,height=dp(26)); ip_c.add_widget(self.lbl_ip); root.add_widget(ip_c)
        for title,dot_attr,lbl_attr,btn_attr,toggle in [("Servidor Web","dot_s","lbl_s","btn_s","_toggle_srv"),("Bot Telegram","dot_b","lbl_b","btn_b","_toggle_bot")]:
            card=CardBox(orientation="vertical",padding=dp(12),spacing=dp(8),size_hint_y=None,height=dp(124))
            row=BoxLayout(size_hint_y=None,height=dp(26),spacing=dp(8))
            row.add_widget(Label(text=title,font_size=dp(14),bold=True,color=TEXT))
            dot=Label(text="●",font_size=dp(18),color=RED,size_hint_x=None,width=dp(22)); setattr(self,dot_attr,dot); row.add_widget(dot); card.add_widget(row)
            lbl=Label(text="Detenido",font_size=dp(12),color=SUB,size_hint_y=None,height=dp(18)); setattr(self,lbl_attr,lbl); card.add_widget(lbl)
            btn=RBtn(text=f"Iniciar {title.lower()}",size_hint_y=None,height=dp(44)); btn.bind(on_press=getattr(self,toggle)); setattr(self,btn_attr,btn); card.add_widget(btn); root.add_widget(card)
        vc=CardBox(orientation="vertical",padding=dp(12),spacing=dp(8))
        rh=BoxLayout(size_hint_y=None,height=dp(26))
        rh.add_widget(Label(text="Videos guardados",font_size=dp(14),bold=True,color=TEXT))
        self.cnt=Label(text="0",font_size=dp(14),bold=True,color=ACCENT,size_hint_x=None,width=dp(30)); rh.add_widget(self.cnt); vc.add_widget(rh)
        sv=ScrollView(); self.vlist=BoxLayout(orientation="vertical",spacing=dp(5),size_hint_y=None); self.vlist.bind(minimum_height=self.vlist.setter("height")); sv.add_widget(self.vlist); vc.add_widget(sv); root.add_widget(vc); self.add_widget(root)
    def _toggle_srv(self,*_):
        global _httpd
        if not self.srv_on:
            try: _httpd=HTTPServer(("0.0.0.0",int(cargar_config().get("web_port","8080"))),Handler); threading.Thread(target=_httpd.serve_forever,daemon=True).start(); self.srv_on=True
            except Exception as e: Popup(title="Error",content=Label(text=str(e),color=TEXT),size_hint=(.8,.3)).open()
        else:
            if _httpd: _httpd.shutdown(); _httpd=None
            self.srv_on=False
    def _toggle_bot(self,*_):
        global _bot
        if not self.bot_on:
            token=cargar_config().get("bot_token","")
            if not token: Popup(title="Falta token",content=Label(text="Configura el token primero",color=TEXT),size_hint=(.8,.3)).open(); return
            threading.Thread(target=iniciar_bot,args=(token,),daemon=True).start(); self.bot_on=True
        else:
            if _bot:
                try:
                    import asyncio; asyncio.get_event_loop().run_until_complete(_bot.stop())
                except: pass
                _bot=None
            self.bot_on=False
    def _refresh(self,*_):
        port=cargar_config().get("web_port","8080")
        if self.srv_on:
            self.lbl_ip.text=f"http://{get_ip()}:{port}"; self.dot_s.color=GREEN; self.lbl_s.text=f"Activo puerto {port}"; self.btn_s.text="Detener servidor"; self.btn_s._bg=RED; self.btn_s._d()
        else:
            self.lbl_ip.text="Inicia servidor para ver URL"; self.dot_s.color=RED; self.lbl_s.text="Detenido"; self.btn_s.text="Iniciar servidor"; self.btn_s._bg=ACCENT; self.btn_s._d()
        if self.bot_on:
            self.dot_b.color=GREEN; self.lbl_b.text="Escuchando mensajes"; self.btn_b.text="Detener bot"; self.btn_b._bg=RED; self.btn_b._d()
        else:
            self.dot_b.color=RED; self.lbl_b.text="Detenido"; self.btn_b.text="Iniciar bot"; self.btn_b._bg=ACCENT; self.btn_b._d()
        exts=('.mp4','.mkv','.avi','.mov','.webm')
        vids=sorted([f for f in VIDEO_DIR.iterdir() if f.suffix.lower() in exts],key=lambda f:f.stat().st_mtime,reverse=True)
        self.cnt.text=str(len(vids)); self.vlist.clear_widgets()
        for v in vids[:20]:
            row=BoxLayout(size_hint_y=None,height=dp(40),spacing=dp(8),padding=[dp(6),dp(2)])
            with row.canvas.before: Color(0.12,0.12,0.18,1); RoundedRectangle(pos=row.pos,size=row.size,radius=[dp(8)])
            row.add_widget(Label(text=v.name,font_size=dp(11),color=TEXT,halign="left",text_size=(None,None)))
            row.add_widget(Label(text=f"{v.stat().st_size/1048576:.0f}MB",font_size=dp(11),color=SUB,size_hint_x=None,width=dp(48)))
            self.vlist.add_widget(row)
class VideoBotApp(App):
    title="VideoBot"
    def build(self):
        Window.clearcolor=BG; sm=ScreenManager(transition=SlideTransition()); sm.add_widget(PanelScreen(name="panel")); sm.add_widget(ConfigScreen(name="config")); return sm
if __name__=="__main__": VideoBotApp().run()