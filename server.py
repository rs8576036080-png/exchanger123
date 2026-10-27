import http.server
import socketserver
import json
import os
import sys
import threading
import socket

PORT = int(os.environ.get('PORT', 8000))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(DIRECTORY, 'database.json')
db_lock = threading.Lock()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def read_db():
    with db_lock:
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print("Error reading database:", e)
        return {
            "users": [], "listings": [], "requests": [], "messages": [],
            "reviews": [], "reports": [], "notifs": [], "saved": {}
        }

def write_db(data):
    with db_lock:
        temp_file = DB_FILE + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, DB_FILE)

class ExchangerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/state':
            data = read_db()
            response_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
            return

        # Special MIME type for webmanifest
        if self.path.endswith('.webmanifest'):
            self.extensions_map['.webmanifest'] = 'application/manifest+json'

        super().do_GET()

    def do_POST(self):
        if self.path == '/api/save':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length).decode('utf-8')
                payload = json.loads(body)
                
                db = read_db()
                keys = payload.get('keys', [])
                data = payload.get('data', {})
                
                for k in keys:
                    if k in data:
                        db[k] = data[k]
                
                write_db(db)
                
                res = json.dumps({"ok": True}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(res)))
                self.end_headers()
                self.wfile.write(res)
            except Exception as e:
                err = json.dumps({"ok": False, "error": str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(err)))
                self.end_headers()
                self.wfile.write(err)
            return

        self.send_response(404)
        self.end_headers()

class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def run():
    local_ip = get_local_ip()
    server_address = ('', PORT)
    with ThreadingServer(server_address, ExchangerHandler) as httpd:
        print("=" * 60)
        print("Exchanger Campus Server is Live!")
        print(f"Local Access:      http://localhost:{PORT}/")
        print(f"Same Wi-Fi Access: http://{local_ip}:{PORT}/ (Use on any phone)")
        print("=" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == '__main__':
    run()
