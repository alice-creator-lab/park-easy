"""Minimal Chrome DevTools Protocol client (stdlib only).

Only what tools/shot.py needs: navigate, evaluate, screenshot. Chrome is
launched separately with --remote-debugging-port=<port>; this connects to the
first page target over HTTP + a hand-rolled WebSocket client.
"""
import base64
import json
import os
import socket
import struct
import time
import urllib.request


class _WS:
    def __init__(self, url, timeout=30):
        assert url.startswith("ws://"), url
        rest = url[5:]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port or 80)), timeout=timeout)
        self.sock.settimeout(1.0)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("ws handshake closed")
            buf += chunk
        if b" 101 " not in buf.split(b"\r\n")[0]:
            raise RuntimeError("ws handshake failed: " + buf[:200].decode("latin1"))
        self.buf = buf.split(b"\r\n\r\n", 1)[1]

    def _recv(self, n, deadline=None):
        while len(self.buf) < n:
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                if deadline and time.time() > deadline:
                    raise
                continue
            if not chunk:
                raise RuntimeError("ws closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        data = text.encode()
        head = bytearray([0x81])
        n = len(data)
        mask = os.urandom(4)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += struct.pack(">H", n)
        else:
            head.append(0x80 | 127)
            head += struct.pack(">Q", n)
        head += mask
        self.sock.sendall(bytes(head) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self, deadline=None):
        payload = b""
        while True:
            b1, b2 = self._recv(2, deadline)
            fin, opcode = b1 & 0x80, b1 & 0x0F
            ln = b2 & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", self._recv(2, deadline))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._recv(8, deadline))[0]
            if b2 & 0x80:
                mask = self._recv(4, deadline)
                payload += bytes(c ^ mask[i % 4] for i, c in enumerate(self._recv(ln, deadline)))
            else:
                payload += self._recv(ln, deadline)
            if opcode == 0x9:  # ping
                continue
            if fin:
                return payload.decode("utf-8", "replace")


class Page:
    def __init__(self, port, match=None):
        targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10))
        pages = [t for t in targets if t.get("type") == "page"]
        if match:
            pages = [t for t in pages if match in t.get("url", "")] or pages
        self.ws = _WS(pages[0]["webSocketDebuggerUrl"])
        self.id = 0

    def send(self, method, params=None, timeout=60):
        self.id += 1
        mid = self.id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = json.loads(self.ws.recv(deadline))
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
        raise RuntimeError(f"{method}: timeout")

    def nav(self, url, timeout=60):
        self.send("Page.enable")
        self.send("Page.navigate", {"url": url})
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                st = self.eval("document.readyState")
            except Exception:
                time.sleep(0.3)
                continue
            if st == "complete":
                return
            time.sleep(0.3)

    def eval(self, expr, timeout=60, await_promise=False):
        r = self.send("Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": await_promise,
        }, timeout=timeout)
        if r.get("exceptionDetails"):
            raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description")
                               or str(r["exceptionDetails"]))
        return r.get("result", {}).get("value")

    # alias used by tools/shot.py
    def js(self, expr, timeout=60):
        return self.eval(expr, timeout=timeout)

    def close(self):
        try:
            self.ws.sock.close()
        except Exception:
            pass

    def shot(self, path, tries=5):
        last = None
        for _ in range(tries):
            try:
                r = self.send("Page.captureScreenshot",
                              {"format": "png", "captureBeyondViewport": False})
                with open(path, "wb") as f:
                    f.write(base64.b64decode(r["data"]))
                return
            except Exception as e:      # noqa: BLE001  (renderer busy → retry)
                last = e
                time.sleep(1.0)
        raise last
