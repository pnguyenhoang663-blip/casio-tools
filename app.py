import os
import json
import sys
import tempfile
import urllib.parse
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

MIME_MAP = {
    ".html": "text/html", ".js": "application/javascript", ".css": "text/css",
    ".json": "application/json", ".txt": "text/plain; charset=utf-8", ".asm": "text/plain; charset=utf-8",
    ".ico": "image/x-icon", ".png": "image/png",
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.unquote(self.path)
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        callback = params.get("callback", [None])[0]

        if path == "/":
            self.serve(os.path.join(BASE_DIR, "index.html"))
        elif path.startswith("/compiler"):
            rel = path[len("/compiler"):].lstrip("/") or "index.html"
            self.serve(os.path.join(BASE_DIR, "compiler", rel))
        elif path.startswith("/raw-file/"):
            parts = path.split("/")
            if len(parts) >= 4:
                model = parts[2]
                filename = "/".join(parts[3:]).split("?")[0]
                fp = os.path.join(BASE_DIR, model, filename)
                if os.path.isfile(fp):
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    if callback:
                        content = callback + "(" + json.dumps(content) + ");"
                    self.send_response(200)
                    self.send_header("Content-Type", "application/javascript" if callback else "text/plain")
                    self.end_headers()
                    self.wfile.write(content.encode())
                else:
                    self.send_error(404)
            else:
                self.send_error(400)
        elif path.startswith("/samples/"):
            model = path.split("/")[2].split("?")[0] if len(path.split("/")) > 2 else "580vnx"
            samples_dir = os.path.join(BASE_DIR, "rsc_ropchain" if model == "580vnx" else "asm_ropchain")
            files = []
            if os.path.exists(samples_dir):
                for f in os.listdir(samples_dir):
                    if f.endswith(".asm") or f.endswith(".rsc"):
                        with open(os.path.join(samples_dir, f), "r", encoding="utf-8") as fh:
                            files.append({"name": f, "content": fh.read()})
            result = json.dumps(files)
            if callback:
                result = callback + "(" + result + ");"
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript" if callback else "application/json")
            self.end_headers()
            self.wfile.write(result.encode())
        else:
            clean = path.lstrip("/")
            for folder in [BASE_DIR, os.path.join(BASE_DIR, "compiler")]:
                fp = os.path.join(folder, clean)
                if os.path.isfile(fp):
                    self.serve(fp)
                    return
            self.serve(os.path.join(BASE_DIR, "index.html"))

    def do_POST(self):
        if self.path == "/compile":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            if self.headers.get("Content-Type", "").startswith("application/x-www-form-urlencoded"):
                parsed = urllib.parse.parse_qs(raw)
                data = json.loads(parsed.get("data", [""])[0])
            else:
                data = json.loads(raw)

            code = data.get("code", "")
            model = data.get("model", "580vnx")
            callback = data.get("cb", "cb")

            try:
                # Write code to temp file
                tmp = tempfile.NamedTemporaryFile(suffix=".rsc", delete=False, dir=BASE_DIR)
                tmp.write(code.encode("utf-8"))
                tmp_name = tmp.name
                tmp.close()

                cmd = [sys.executable, os.path.join(BASE_DIR, "rac.py")]
                cmd.extend(["-l", "vi_VN", model, os.path.basename(tmp_name)])
                res = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR, encoding="utf-8")

                try: os.remove(tmp_name)
                except: pass

                response = {
                    "output": res.stdout,
                    "notes": res.stderr or "",
                    "returncode": res.returncode,
                    "bytes_count": len(res.stdout.split()) if res.stdout else 0,
                }
            except Exception as e:
                import traceback
                response = {"error": traceback.format_exc()}

            html = '<html><body><script>window.parent.postMessage(JSON.stringify({cb:"' + callback + '",data:' + json.dumps(response) + '}),"*");</script></body></html>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

    def serve(self, path):
        try:
            with open(path, "rb") as f:
                c = f.read()
            ext = os.path.splitext(path)[1].lower()
            self.send_response(200)
            self.send_header("Content-Type", MIME_MAP.get(ext, "application/octet-stream"))
            self.end_headers()
            self.wfile.write(c)
        except:
            self.send_error(404)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Server running on port {port}")
    server.serve_forever()