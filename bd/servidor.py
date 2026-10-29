"""Painel local: serve o relatório e recebe aprovações. Só escuta em 127.0.0.1."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .ciclo import exportar
from .governanca import aprovar, rejeitar
from .memoria import Memoria


def servir(saida: str | Path, cfg: dict, porta: int = 8765):
    saida = Path(saida)

    class H(BaseHTTPRequestHandler):
        def _resp(self, code, corpo, tipo="text/plain; charset=utf-8"):
            dados = corpo.encode() if isinstance(corpo, str) else corpo
            self.send_response(code)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def do_GET(self):
            if self.path == "/api/ping":
                return self._resp(200, "ok")
            if self.path == "/api/descobertas":
                return self._resp(200, (saida / "descobertas.json").read_bytes(), "application/json")
            if self.path in ("/", "/index.html"):
                return self._resp(200, (saida / "relatorio.html").read_bytes(), "text/html; charset=utf-8")
            self._resp(404, "não encontrado")

        def do_POST(self):
            if self.path not in ("/api/aprovar", "/api/rejeitar"):
                return self._resp(404, "não encontrado")
            try:
                n = int(self.headers.get("Content-Length", "0"))
                corpo = json.loads(self.rfile.read(n) or b"{}")
                mem = Memoria(saida / "memoria.sqlite")
                try:
                    fn = aprovar if self.path.endswith("aprovar") else rejeitar
                    fn(mem, corpo["id"], str(corpo["por"])[:80])
                    exportar(mem, saida, cfg)
                finally:
                    mem.fechar()
                self._resp(200, "ok")
            except Exception as e:  # mensagem curta para o painel
                self._resp(400, f"{e.__class__.__name__}: {e}")

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", porta), H)
    print(f"Painel em http://127.0.0.1:{porta}  (Ctrl+C para sair)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
