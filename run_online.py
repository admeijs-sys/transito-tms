"""
Transito TMS - Automatische Launcher met Cloudflare Tunnel
Start server.py en cloudflared, vangt de trycloudflare link af en slaat deze op in tunnel_url.txt.
"""
import subprocess
import threading
import re
import os
import sys
import time
import webbrowser
import atexit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUDFLARED = os.path.join(BASE_DIR, "cloudflared.exe")
TUNNEL_FILE = os.path.join(BASE_DIR, "tunnel_url.txt")

# Verwijder oude tunnel link bij opstarten
if os.path.exists(TUNNEL_FILE):
    try:
        os.remove(TUNNEL_FILE)
    except Exception:
        pass

print("=" * 60)
print("  Transito TMS & SDI Facturatie - Online Launcher")
print("=" * 60)

# 1. Start Python Server
print("[1/2] Starten van de Transito Backend Server...")
server_proc = subprocess.Popen([sys.executable, "server.py"], cwd=BASE_DIR)

time.sleep(1)

cf_proc = None

def cleanup():
    if os.path.exists(TUNNEL_FILE):
        try:
            os.remove(TUNNEL_FILE)
        except Exception:
            pass
    if cf_proc and cf_proc.poll() is None:
        try:
            cf_proc.terminate()
        except Exception:
            pass
    if server_proc and server_proc.poll() is None:
        try:
            server_proc.terminate()
        except Exception:
            pass

atexit.register(cleanup)

# 2. Start Cloudflare Tunnel met automatische watchdog & herverbinding
if os.path.exists(CLOUDFLARED):
    print("[2/2] Starten van de beveiligde Cloudflare Tunnel (met 24/7 Watchdog)...")

    def run_tunnel_with_watchdog():
        global cf_proc
        url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        
        while True:
            try:
                cf_proc = subprocess.Popen(
                    [CLOUDFLARED, "tunnel", "--url", "http://127.0.0.1:8080"],
                    cwd=BASE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                    errors="replace"
                )

                url_found = False
                current_url = None
                
                # Lees stdout van cloudflared
                for line in cf_proc.stdout:
                    match = url_pattern.search(line)
                    if match and not url_found:
                        url_found = True
                        current_url = match.group(0)
                        try:
                            with open(TUNNEL_FILE, "w", encoding="utf-8") as f:
                                f.write(current_url)
                        except Exception:
                            pass
                        print("\n" + "=" * 60)
                        print("  JOUW ONLINE LINK IS NU LIVE & ACTIEF!")
                        print("=" * 60)
                        print(f"  Laptop/Kantoor:    http://127.0.0.1:8080")
                        print(f"  Mobiel Wereldwijd: {current_url}/mobile")
                        print("=" * 60)
                        print("  Open de mobiele link op je telefoon of scan de QR-code")
                        print("  in het kantoor-dashboard rechtsboven.\n")

                # Als het proces stopt (bijv. door Cloudflare sessie-verloop of slaapstand)
                ret = cf_proc.poll()
                print(f"[WATCHDOG] Cloudflare tunnelverbinding is verbroken (code {ret}). Herstarten binnen 3 seconden...")
                time.sleep(3)

            except Exception as e:
                print(f"[WATCHDOG] Fout bij tunnelproces: {e}. Opnieuw proberen over 5 seconden...")
                time.sleep(5)

    t = threading.Thread(target=run_tunnel_with_watchdog, daemon=True)
    t.start()
else:
    print("[LET OP] cloudflared.exe niet gevonden. Alleen lokaal bereikbaar.")

# Open kantoor dashboard
webbrowser.open("http://127.0.0.1:8080")

try:
    server_proc.wait()
except KeyboardInterrupt:
    print("\nAfsluiten...")
finally:
    cleanup()
