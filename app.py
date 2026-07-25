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
                # Import compiler modules
                from libcompiler import loader, handlers, utils, engine, extensions

                # Reset state
                loader.labels.clear()
                loader.global_labels.clear()
                loader.section_addresses.clear()
                loader.label_sections.clear()
                loader.aliases.clear()
                loader.result.clear()
                loader.vars_dict.clear()
                loader.commands.clear()
                loader.datalabels.clear()
                loader.disasm.clear()
                loader.deferred_evals.clear()
                loader.address_requests.clear()
                loader.relocation_expressions.clear()
                loader.sizeof_cmds.clear()
                loader.dist_cmds.clear()
                loader.pr_org_cmds.clear()
                loader.pr_backup_cmds.clear()
                loader.dynamic_macros.clear()
                loader.defined_functions.clear()
                utils._default_diagnostics.reset()

                # Load config
                config_path = os.path.join(BASE_DIR, model, "config.json")
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # Load keywords
                kw_path = os.path.join(BASE_DIR, "libcompiler", "keyword.txt")
                if os.path.exists(kw_path):
                    with open(kw_path, "r", encoding="utf-8") as f:
                        utils.setKeywords(f.read().splitlines())

                # Load model files
                gadgets_path = os.path.join(BASE_DIR, model, config["gadgets_file"])
                labels_path = os.path.join(BASE_DIR, model, config["labels_file"])
                with open(gadgets_path, "r", encoding="utf-8") as f:
                    gadgets_text = f.read()
                with open(labels_path, "r", encoding="utf-8") as f:
                    labels_text = f.read()

                loader.char_to_hex.update(config.get("char_to_hex", {}))
                loader.token_to_hex.update(config.get("token_to_hex", {}))
                handlers.init_handlers()
                loader.parse_commands(gadgets_text, labels_text)

                # Parse extensions
                ext_path = os.path.join(BASE_DIR, model, config.get("extensions_file", "extensions.txt"))
                ext_list = []
                if os.path.exists(ext_path):
                    with open(ext_path, "r", encoding="utf-8") as f:
                        ext_list = extensions.parse_extensions(f.read())

                # Expand extensions in code
                program = extensions.expand_extensions_in_program(code.split('\n'), ext_list)

                # Run compiler
                overflow_sp = config["overflow_initial_sp"]
                results = engine.process_program(program, overflow_sp)

                output = results.get("output", "")
                response = {"output": output, "notes": "", "returncode": 0, "bytes_count": len(output.split()) if output else 0}
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