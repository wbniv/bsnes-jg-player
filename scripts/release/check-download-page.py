#!/usr/bin/env python3
"""Validate the built Indri download component against a local manifest fixture."""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright
from release import ROOT, require

out=ROOT/'docs/proof/release-tooling/2026-10-31';out.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'docs/releases/current.json').read_text())
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path=='/api/bsnes-releases.json':
            data=json.dumps(manifest).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
        else:super().do_GET()
with http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT.parent/'indri.studio/dist'))) as server:
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
            for label,width in [('desktop',1280),('phone',390)]:
                page=browser.new_page(viewport={'width':width,'height':1000},device_scale_factor=1)
                page.route('**/suite/**',lambda route:route.abort())
                page.goto(f'http://127.0.0.1:{server.server_port}/apps/bsnes-jg-player/',wait_until='domcontentloaded')
                box=page.locator('[data-bsnes-releases]');box.locator('article').first.wait_for()
                require(box.locator('article').count()==4,'Current/previous must each show two APKs')
                expected={a['url'] for r in [manifest['current'],manifest['previous']] for a in r['artifacts']}
                actual=set(box.locator('article a').evaluate_all('(nodes)=>nodes.map(n=>n.href)'))
                require(actual==expected,'Rendered APK URLs differ from fixture')
                require(page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Page overflows viewport')
                box.screenshot(path=str(out/('downloads-'+label+'.png')))
                page.close()
            bad=browser.new_page()
            bad.route('**/api/bsnes-releases.json',lambda route:route.fulfill(json={'current':{'versionName':'0.1.9','artifacts':[{'url':'javascript:alert(1)'}]}}))
            bad.goto(f'http://127.0.0.1:{server.server_port}/apps/bsnes-jg-player/',wait_until='domcontentloaded')
            bad.get_by_text('Release details are temporarily unavailable.',exact=False).wait_for()
            require(bad.locator('[data-bsnes-releases] article').count()==0,'Invalid manifest rendered APK links')
            browser.close()
    finally:server.shutdown();thread.join()
(out/'download-page-check.json').write_text(json.dumps({'status':'pass','environment':'local built Indri page; repository current/previous manifest fixture','widths':[1280,390],'apkLinksPerWidth':4,'invalidManifest':'rejected','deploymentVerified':False},indent=2)+'\n')
print('Download page PASS at desktop/phone widths; invalid manifest rejected; local proof saved')
