#!/usr/bin/env python3
"""Observe the live-record self-check's retarget-once "stop" case in a real headless Firefox.

Loads the player with ?verify=1 (the gallery ROM's manifest selfcheck has mode "live-record"), waits
for the badge to say it is verifying one artwork, then sends ArrowRight twice -- two "navigations"
mid-poll.  web/app.js verifyLiveRecord must show, in order:
    verifying…  ->  verifying <A>… n/total  ->  following your navigation to <B>   (1st retarget)
    ->  fail "navigation kept restarting the check — hold on one artwork and try again"  (2nd: stop)

Usage:
  python3 -I scripts/retarget-verify.py [--out-dir DIR] [--timeout SECS] [-h]

Starts its own `serve.py` and headless Firefox (profile under /tmp, deleted on exit; nothing is
downloaded).  Writes <out-dir>/timeline.json (timestamped badge + record samples), a
screenshot of the final badge (retarget-fail.png) and prints a summary.
Exit status: 0 expected sequence observed; 1 sequence not observed; 2 the ROM never published a
non-zero `state` (no gallery_shown record -- the real page cannot reach the retarget branch).

Takes ~2.5 min: the real ROM runs ~20 frames/s in headless software rendering and the check polls
every 120 frames.  Plan: docs/plans/2026-10-31-retarget-stop-check.md.
"""
import argparse, base64, json, os, re, shutil, socket, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL_TEXT = "navigation kept restarting the check — hold on one artwork and try again"

# A MutationObserver is required: each chunk of verifyLiveRecord blocks the page's main thread for
# many seconds (it runs `poll` frames synchronously), and the "following your navigation" badge is
# overwritten by the next chunk, so sampling #checkresult from outside would miss it.
OBSERVE_JS = """
window.__badgeLog = []; window.__keyLog = [];
const el = document.getElementById('checkresult');
const push = () => window.__badgeLog.push({ms: Date.now(), badge: el.textContent, cls: el.className});
new MutationObserver(push).observe(el, {childList: true, characterData: true, subtree: true});
push();
return true;
"""

PROBE_JS = """
const M = window.__bjg; let rec = null;
try {
  const sc = window.__bjgSc;
  if (M && sc) { const base = (M._bjg_wram() >>> 0) + sc.off;
    rec = {state: M.HEAPU8[base + sc.state], work: M.HEAPU8[base + sc.work]}; }
} catch (e) { rec = {error: String(e)}; }
return {now: Date.now(), rec: rec, log: window.__badgeLog, keys: window.__keyLog};
"""

KEY_JS = """
const code = arguments[0], ms = arguments[1];
window.__keyLog.push({ms: Date.now(), key: code, hold_ms: ms});
window.dispatchEvent(new KeyboardEvent('keydown', {code: code, bubbles: true, cancelable: true}));
setTimeout(() => window.dispatchEvent(new KeyboardEvent('keyup', {code: code, bubbles: true, cancelable: true})), ms);
return true;
"""


class Marionette:
    def __init__(self, port=2828, timeout=900):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        self.buf, self.mid = b"", 0
        self._recv()  # hello

    def _recv(self):
        while b":" not in self.buf:
            self.buf += self.s.recv(65536)
        n, rest = self.buf.split(b":", 1)
        n = int(n)
        while len(rest) < n:
            rest += self.s.recv(65536)
        msg, self.buf = rest[:n], rest[n:]
        return json.loads(msg)

    def cmd(self, name, params=None):
        self.mid += 1
        body = json.dumps([0, self.mid, name, params or {}]).encode()
        self.s.sendall(str(len(body)).encode() + b":" + body)
        while True:
            r = self._recv()
            if isinstance(r, list) and r[1] == self.mid:
                if r[2]:
                    raise RuntimeError(r[2])
                return r[3]

    def js(self, script, args=None):
        return self.cmd("WebDriver:ExecuteScript", {"script": script, "args": args or []})["value"]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_port(port, secs=60):
    end = time.time() + secs
    while time.time() < end:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError("port %d never opened" % port)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "docs/plans/screenshots"))
    ap.add_argument("--timeout", type=int, default=900, help="overall seconds (default 900)")
    ap.add_argument("--no-state-secs", type=int, default=90,
                    help="give up (exit 2) if the record's state stays 0 this long (default 90)")
    ap.add_argument("--hold-ms", type=int, default=120, help="key hold time per navigation")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    prefix = "retarget"

    port = free_port()
    prof = tempfile.mkdtemp(prefix="retarget-ff-", dir="/tmp")
    srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "serve.py"), "-p", str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ff = None
    probes, t0, rc = [], time.time(), 1
    t0_ms = int(t0 * 1000)
    try:
        wait_port(port)
        env = dict(os.environ, MOZ_HEADLESS="1")
        ff = subprocess.Popen(["/usr/bin/firefox", "--headless", "--no-remote", "--marionette",
                               "--profile", prof], env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_port(2828)
        m = Marionette(timeout=a.timeout)
        m.cmd("WebDriver:NewSession", {"capabilities": {}})
        m.cmd("WebDriver:SetTimeouts", {"script": 60000, "pageLoad": 120000})
        url = "http://127.0.0.1:%d/?rom=lzss-gallery&verify=1" % port
        m.cmd("WebDriver:Navigate", {"url": url})
        m.js(OBSERVE_JS)
        m.js("""fetch('roms/manifest.json').then(r=>r.json()).then(j=>{
                 const sc=j.roms.find(x=>x.id==='lzss-gallery').selfcheck;
                 window.__bjgSc={off:Number(sc.off),state:sc.record.state,work:sc.record.work};});
               return true;""")

        def sample():
            r = m.js(PROBE_JS)
            probes.append({"t": round((r["now"] - t0_ms) / 1000, 2), "rec": r["rec"]})
            return r

        presses, saw_state = 0, False
        end = time.time() + a.timeout
        while time.time() < end:
            r = sample()
            rec = r["rec"] or {}
            if rec.get("state"):
                saw_state = True
            texts = [e["badge"] for e in r["log"]]
            if FAIL_TEXT in texts:
                rc = 0
                break
            if not saw_state and time.time() - t0 > a.no_state_secs:
                rc = 2
                break
            if any(t[:1] in ("✓", "✗", "⏱") or "still verifying" in t for t in texts):
                break  # the check finished (or timed out) without reaching the stop branch
            if saw_state and presses == 0 and any(re.match(r"verifying .+… \d+/\d+", t) for t in texts):
                m.js(KEY_JS, ["ArrowRight", a.hold_ms]); presses = 1
            elif presses == 1 and any(t.startswith("following your navigation to") for t in texts):
                m.js(KEY_JS, ["ArrowRight", a.hold_ms]); presses = 2
            time.sleep(0.25)
        r = sample()
        timeline = [{"t": round((e["ms"] - t0_ms) / 1000, 2), "badge": e["badge"],
                     "cls": e["cls"].replace("badge", "").strip()} for e in r["log"]]
        timeline += [{"t": round((k["ms"] - t0_ms) / 1000, 2), "key": k["key"], "hold_ms": k["hold_ms"]}
                     for k in r["keys"]]
        timeline.sort(key=lambda x: x["t"])
        final = r["log"][-1] if r["log"] else {"badge": None, "cls": ""}
        m.js("document.getElementById('checkresult').scrollIntoView({block: 'center'}); return true;")
        png = m.cmd("WebDriver:TakeScreenshot", {"full": False})["value"]
        shot = os.path.join(a.out_dir, prefix + "-fail.png")
        open(shot, "wb").write(base64.b64decode(png))
        try:
            m.cmd("Marionette:Quit", {"flags": ["eForceQuit"]})
        except Exception:
            pass
        seq = [t["badge"] for t in timeline if "badge" in t]
        order = [r"^verifying…( \d+/\d+( frames)?)?$", r"^verifying .+… \d+/\d+$",
                 r"^following your navigation to .+$", "^" + re.escape(FAIL_TEXT) + "$"]
        i = 0
        for b in seq:
            if i < len(order) and re.match(order[i], b or ""):
                i += 1
        ok = (i == len(order)) and "fail" in final["cls"]
        out = {"url": url, "exit": 0 if ok else (2 if rc == 2 else 1), "presses": presses,
               "matched_steps": i, "of": len(order), "final": final["badge"], "screenshot": os.path.relpath(shot, ROOT),
               "record_probes": probes, "timeline": timeline}
        jpath = os.path.join(a.out_dir, prefix + "-timeline.json")
        json.dump(out, open(jpath, "w"), ensure_ascii=False, indent=1)
        for t in timeline:
            if "badge" in t:
                print("%7.2fs  [%s] %s" % (t["t"], t["cls"], t["badge"]))
            else:
                print("%7.2fs  KEY %s (held %d ms)" % (t["t"], t["key"], t["hold_ms"]))
        print("record probes (t, state/work):", " ".join(
            "%s:%s/%s" % (p["t"], (p["rec"] or {}).get("state"), (p["rec"] or {}).get("work")) for p in probes[::6]))
        print("matched %d/%d expected steps; presses=%d; exit=%d" % (i, len(order), presses, out["exit"]))
        if out["exit"] == 2:
            print("ROM never published a non-zero state: no gallery_shown record", file=sys.stderr)
        return out["exit"]
    finally:
        for p in (ff, srv):
            if p and p.poll() is None:
                p.terminate()
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    p.kill()
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
