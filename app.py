import os
import json
import sys
import tempfile
import urllib.parse
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
            samples_dir = os.path.join(BASE_DIR, "asm_ropchain")
            files = []
            if os.path.exists(samples_dir):
                for f in os.listdir(samples_dir):
                    if f.endswith(".asm"):
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
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUNBUFFERED"] = "1"

                with tempfile.NamedTemporaryFile(suffix=".rsc", delete=False, dir=BASE_DIR) as tmp:
                    tmp.write(code.encode("utf-8"))
                    tmp_name = tmp.name

                from libcompiler import main as compiler_main
                import io
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()

                # Run compiler
                sys.argv = ["rac.py", "-l", "vi_VN", model, os.path.basename(tmp_name)]
                try:
                    compiler_main.main()
                except SystemExit:
                    pass

                output = sys.stdout.getvalue()
                sys.stdout = old_stdout

                try:
                    os.remove(tmp_name)
                except:
                    pass

                response = {"output": output, "notes": "", "returncode": 0, "bytes_count": len(output.split()) if output else 0}
            except Exception as e:
                response = {"error": str(e)}
                try: os.remove(tmp_name)
                except: pass

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