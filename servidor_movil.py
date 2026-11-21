"""Calori para moviles: servidor web para que cualquier usuario la use desde su telefono.

Las claves de IA viven SOLO en el servidor (archivo .env en local, o variables de entorno en el hosting)
y nunca llegan al telefono. Los datos de cada usuario se guardan en su propio movil.

Local:  python servidor_movil.py      En un hosting: ver LEEME_HOSTING.txt
"""
import time
from collections import defaultdict, deque
import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
try:
    from dotenv import load_dotenv
except ImportError:  # en el hosting las claves son variables de entorno
    def load_dotenv(*_a, **_k):
        return False

AQUI = Path(__file__).resolve().parent
load_dotenv(AQUI / ".env")
HTML = AQUI / "calori_movil.html"
PUERTO = int(os.getenv("PORT") or os.getenv("PUERTO_MOVIL") or 8000)
LIMITE_HORA = int(os.getenv("LIMITE_HORA", "30"))      # analisis por usuario (IP) y hora
LIMITE_DIA = int(os.getenv("LIMITE_DIA_TOTAL", "1500"))  # analisis totales al dia (protege tu cuota)
_hist = defaultdict(deque)
_dia = {"fecha": "", "n": 0}


ESTATICOS = {
    "/manifest.webmanifest": "application/manifest+json",
    "/sw.js": "application/javascript",
    "/icon-192.png": "image/png",
    "/icon-512.png": "image/png",
    "/apple-touch-icon.png": "image/png",
}


def permitido(ip):
    ahora = time.time()
    h = _hist[ip]
    while h and ahora - h[0] > 3600:
        h.popleft()
    hoy = time.strftime("%Y-%m-%d")
    if _dia["fecha"] != hoy:
        _dia.update(fecha=hoy, n=0)
    if len(h) >= LIMITE_HORA:
        return "Has llegado al limite de analisis por hora. Prueba mas tarde."
    if _dia["n"] >= LIMITE_DIA:
        return "El servicio ha llegado a su limite diario. Vuelve a probar manana."
    h.append(ahora)
    _dia["n"] += 1
    return None
MODELOS_GEMINI = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash"]


def clave(base, i):  # igual que la app de escritorio
    return os.getenv(f"{base}_{i + 1}") or os.getenv(base) or os.getenv(f"{base}_1", "")


def configs():
    cs = [("gemini", clave("GEMINI_API_KEY", i), m) for i, m in enumerate(MODELOS_GEMINI)]
    cs = [c for c in cs if c[1]]
    if os.getenv("ANTHROPIC_API_KEY"):
        cs.append(("anthropic", os.environ["ANTHROPIC_API_KEY"], "claude-haiku-5-5"))
    if os.getenv("OPENAI_API_KEY"):
        cs.append(("openai", os.environ["OPENAI_API_KEY"], "gpt-4o-mini"))
    return cs


def llamar(c, prompt, b64, max_tokens):
    prov, key, modelo = c
    if prov == "gemini":
        partes = ([{"inline_data": {"mime_type": "image/jpeg", "data": b64}}] if b64 else []) + [{"text": prompt}]
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
            headers={"x-goog-api-key": key}, timeout=180,
            json={"contents": [{"parts": partes}], "generationConfig": {"responseMimeType": "application/json"}})
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    if prov == "anthropic":
        cont = ([{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}]
                if b64 else []) + [{"type": "text", "text": prompt}]
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=180,
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                          json={"model": modelo, "max_tokens": max_tokens,
                                "messages": [{"role": "user", "content": cont}]})
        r.raise_for_status()
        return r.json()["content"][0]["text"]
    cont = ([{"type": "text", "text": prompt},
             {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}}] if b64 else prompt)
    r = requests.post("https://api.openai.com/v1/chat/completions", timeout=180,
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": modelo, "max_tokens": max_tokens,
                            "messages": [{"role": "user", "content": cont}]})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


class H(BaseHTTPRequestHandler):
    def _json(self, codigo, obj):
        d = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(d)))
        self.end_headers()
        self.wfile.write(d)

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta in ESTATICOS and (AQUI / ruta.lstrip("/")).exists():
            d = (AQUI / ruta.lstrip("/")).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ESTATICOS[ruta])
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(d)))
            self.end_headers()
            self.wfile.write(d)
        elif ruta in ("/", "/calori_movil.html"):
            d = HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(d)))
            self.end_headers()
            self.wfile.write(d)
        elif self.path == "/api/estado":
            self._json(200, {"ok": True, "apis": len(configs())})
        else:
            self._json(404, {"error": "no existe"})

    def do_POST(self):
        if self.path != "/api/ia":
            return self._json(404, {"error": "no existe"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 15_000_000:
                return self._json(413, {"error": "Foto demasiado grande"})
            q = json.loads(self.rfile.read(n))
            prompt, b64 = str(q.get("prompt", "")), str(q.get("imagen", ""))
            mx = min(int(q.get("max_tokens", 1000)), 3000)
        except Exception:  # noqa: BLE001
            return self._json(400, {"error": "Peticion no valida"})
        ip = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
        aviso = permitido(ip)
        if aviso:
            return self._json(429, {"error": aviso})
        cs = configs()
        if not cs:
            return self._json(500, {"error": "El servidor no tiene claves de IA configuradas"})
        err = ""
        for c in cs:
            try:
                return self._json(200, {"texto": llamar(c, prompt, b64, mx)})
            except Exception as e:  # noqa: BLE001
                err = f"{c[0]} ({c[2]}): {str(e)[:150]}"
        self._json(502, {"error": err})

    def log_message(self, *a):
        pass


def ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    if not HTML.exists():
        raise SystemExit(f"Falta {HTML.name} en {AQUI}")
    print(f"APIs de IA encontradas: {len(configs())}")
    print(f"Puerto {PUERTO} · limite {LIMITE_HORA} analisis/hora por usuario · {LIMITE_DIA}/dia en total")
    if not os.getenv("PORT"):
        print(f"\nEn la misma WiFi:  http://{ip_local()}:{PUERTO}\nEn este PC:  http://localhost:{PUERTO}\n\nCtrl+C para parar.")
    ThreadingHTTPServer(("0.0.0.0", PUERTO), H).serve_forever()
