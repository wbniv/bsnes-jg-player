#!/usr/bin/env python3
"""Drive a headless Firefox over Marionette (no geckodriver): load the player with ?verify=1 and wait for the fidelity badge.

Usage:
  python3 serve.py -p 8123 &
  firefox --headless --no-remote --marionette --profile "$(mktemp -d)" &
  python3 -I scripts/firefox-verify.py http://127.0.0.1:8123/?verify=1 out.png
Prints the badge text, whether the page is cross-origin isolated and whether SharedArrayBuffer exists,
and saves a screenshot. Waits up to 15 min (headless software rendering is slow).
"""
import base64, json, socket, sys, time

URL, OUT = sys.argv[1], sys.argv[2]
s = socket.create_connection(("127.0.0.1", 2828), timeout=900)
buf = b""
def recv():
    global buf
    while b":" not in buf:
        buf += s.recv(65536)
    n, rest = buf.split(b":", 1)
    n = int(n)
    while len(rest) < n:
        rest += s.recv(65536)
    msg, buf = rest[:n], rest[n:]
    return json.loads(msg)
mid = 0
def cmd(name, params=None):
    global mid
    mid += 1
    body = json.dumps([0, mid, name, params or {}]).encode()
    s.sendall(str(len(body)).encode() + b":" + body)
    while True:
        r = recv()
        if isinstance(r, list) and r[1] == mid:
            if r[2]:
                raise RuntimeError(r[2])
            return r[3]
recv()  # hello
cmd("WebDriver:NewSession", {"capabilities": {}})
cmd("WebDriver:SetTimeouts", {"script": 60000, "pageLoad": 120000})
cmd("WebDriver:Navigate", {"url": URL})
js = """
const b = document.getElementById('checkresult');
return {badge: b ? b.textContent : null, cls: b ? b.className : null,
        ua: navigator.userAgent, coi: window.crossOriginIsolated,
        sab: typeof SharedArrayBuffer, title: document.title};
"""
last = None
for _ in range(900):
    r = cmd("WebDriver:ExecuteScript", {"script": js, "args": []})["value"]
    last = r
    if r["badge"] and ("FIDELITY" in r["badge"] or "✓" in r["badge"] or "✗" in r["badge"] or "FAIL" in r["badge"].upper()):
        break
    time.sleep(1)
print(json.dumps(last, ensure_ascii=False, indent=1))
png = cmd("WebDriver:TakeScreenshot", {"full": False})["value"]
open(OUT, "wb").write(base64.b64decode(png))
cmd("Marionette:Quit", {"flags": ["eForceQuit"]})
