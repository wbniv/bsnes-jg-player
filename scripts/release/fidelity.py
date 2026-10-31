#!/usr/bin/env python3
"""Run the real browser WRAM gate against the freshly built web core."""
import functools
import http.server
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import sys
import threading
from release import ROOT, require

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def check(dist=ROOT/'dist'):
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    require(chrome,'Chrome/Chromium required for browser fidelity gate')
    config=json.loads((ROOT/'demo-rom.json').read_text())
    harness=tempfile.TemporaryDirectory()
    web=Path(harness.name)
    shutil.copyfile(ROOT/'web/index.html',web/'index.html')
    shutil.copyfile(dist/'engine/app.js',web/'app.js')
    shutil.copytree(dist/'engine/cores',web/'cores')
    shutil.copytree(dist/'demo/roms',web/'roms')
    shutil.copytree(dist/'demo/preview',web/'preview')
    handler=functools.partial(Quiet,directory=str(web))
    with http.server.ThreadingHTTPServer(('127.0.0.1',0),handler) as server, tempfile.TemporaryDirectory() as profile:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            result=subprocess.run([chrome,'--headless=new','--disable-gpu','--no-sandbox','--user-data-dir='+profile,
                '--virtual-time-budget=120000','--dump-dom',f'http://127.0.0.1:{server.server_port}/?rom={config["slug"]}&verify=1'],capture_output=True,text=True,timeout=180)
            if result.returncode != 0 or 'badge pass' not in result.stdout:
                print('Browser gate status:', re.findall(r'id="(?:status|checkresult)"[^>]*>[^<]*', result.stdout))
            require(result.returncode==0 and re.search(r'id="checkresult"[^>]*class="badge pass"',result.stdout),'Browser demo fidelity gate did not pass')
        finally:server.shutdown();thread.join();harness.cleanup()
    print('Browser demo WRAM fidelity PASS: '+config['slug'])

if __name__=='__main__':check(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'dist')
