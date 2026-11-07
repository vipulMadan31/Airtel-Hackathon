import uvicorn
import webbrowser
import sys
import socket
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    lan_ip = get_lan_ip()
    print("=" * 65)
    print("  PROJECT UDYAM DIGITAL — AIRTEL BUSINESS ONBOARDING")
    print("  Enterprise Track A: MSME Digital Acquisition & Onboarding")
    print("=" * 65)
    print("  Local Machine:  http://127.0.0.1:8000")
    print(f"  Mobile / LAN:   http://{lan_ip}:8000")
    print("=" * 65)
    print("Starting server on all network interfaces (0.0.0.0:8000)...")
    print("Press CTRL+C to stop.\n")
    
    # Run uvicorn server on 0.0.0.0 so other devices on the same network can access
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

