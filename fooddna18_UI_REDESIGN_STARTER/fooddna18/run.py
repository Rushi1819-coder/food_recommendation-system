import functools
import http.server
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

project_root = Path(__file__).resolve().parent
backend_path = project_root / "backend"
frontend_path = project_root / "frontend"

# Automatically use project virtualenv if running outside it
venv_python = project_root / "venv" / "Scripts" / "python.exe"
if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app import create_app

app = create_app()


def is_port_in_use(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


class QuietHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(frontend_path), **kwargs)

    def log_message(self, format, *args):
        # Keep console output clean: only log 4xx/5xx errors
        if args and len(args) > 1 and str(args[1]).startswith(("4", "5")):
            super().log_message(format, *args)


def start_frontend_server(port=5500):
    if is_port_in_use(port):
        print(f"[*] Frontend is already active at http://127.0.0.1:{port}")
        return

    class ReusableServer(socketserver.TCPServer):
        allow_reuse_address = True

    try:
        with ReusableServer(("127.0.0.1", port), QuietHTTPHandler) as httpd:
            httpd.serve_forever()
    except Exception as exc:
        print(f"[!] Frontend server notice: {exc}")


def open_browser():
    time.sleep(1.2)
    try:
        webbrowser.open("http://127.0.0.1:5500")
    except Exception:
        pass


def print_banner():
    print("\n" + "=" * 62)
    print("               FOOD DNA - ALL-IN-ONE RUNNER               ")
    print("=" * 62)
    print("  [+] Frontend URL : http://127.0.0.1:5500")
    print("  [+] Backend API  : http://127.0.0.1:5000")
    print("  [+] Database     : MySQL (fooddna)")
    print("-" * 62)
    print("  Demo Accounts (Password: Password123!):")
    print("    - Customer        : customer@gmail.com")
    print("    - Restaurant Admin: restaurant@gmail.com")
    print("    - Kitchen Staff   : staff@gmail.com")
    print("    - Delivery Partner: delivery@gmail.com")
    print("    - Super Admin     : admin@gmail.com")
    print("=" * 62)
    print("  Press Ctrl+C in this terminal to stop the application.\n")


if __name__ == "__main__":
    is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    if not is_reloader_child:
        print_banner()
        # 1. Start Frontend Server in background thread
        t_front = threading.Thread(target=start_frontend_server, daemon=True)
        t_front.start()

        # 2. Open browser automatically
        t_browser = threading.Thread(target=open_browser, daemon=True)
        t_browser.start()

    # 3. Start Flask Backend API
    try:
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=os.getenv("FLASK_DEBUG", "0") == "1",
            use_reloader=False,
        )
    except KeyboardInterrupt:
        print("\n[!] Shutting down Food DNA servers...")
        sys.exit(0)

