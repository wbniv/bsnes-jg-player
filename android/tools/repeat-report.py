#!/usr/bin/env python3
"""Regenerate the October 31 comparison from downloaded coordinator evidence."""
import json, statistics, html, shutil, sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
raw = root / 'docs/diagnostics/android-repeat-2026-10-31'
out = root / 'docs/performance/2026-10-31'
out.mkdir(parents=True, exist_ok=True)
ledger = [
 ('native-pair-1','J-039b0f772d6f','Cast1','Native'),
 ('wasm-pair-1','J-9aa21a23560f','Cast1','WASM'),
 ('native-pair-2','J-5e627ea361f2','Cast1','Native'),
 ('wasm-crash','J-f47fb920a3a5','Cast1','WASM'),
 ('pixel-native','J-06b35cd9d2a6','Pixel','Native'),
 ('pixel-wasm','J-e9aa930505cd','Pixel','WASM'),
 ('pixel-wasm-long','J-68b3f9bdcde1','Pixel','WASM'),
]
extra=raw/'extra-runs.json'
if extra.exists(): ledger += json.loads(extra.read_text())
saved = '--from-saved' in sys.argv or not raw.exists()
if saved:
 runs = json.loads((out/'runs.json').read_text())
else:
 runs=[]
 for folder,job,device,engine in ledger:
  d=raw/folder
  if not (d/'receipt.json').exists(): continue
  receipt=json.loads((d/'receipt.json').read_text())
  events=[]
  for line in (d/'logcat.txt').read_text(errors='replace').splitlines() if (d/'logcat.txt').exists() else []:
   if 'BJG_TV_METRIC' not in line: continue
   try: events.append(json.loads(line[line.index('{'):]))
   except (ValueError,json.JSONDecodeError): pass
  summary=json.loads((d/'run-1/summary.json').read_text()) if (d/'run-1/summary.json').exists() else {}
  windows=[e for e in events if e.get('event')=='playback_window']
  installs=json.loads((d/'apk-installations.json').read_text()) if (d/'apk-installations.json').exists() else []
  run=dict(job=job,folder=folder,device=device,engine=engine,status=receipt.get('status'),reason=receipt.get('reason'),
   compositor=summary,apk=installs,window_count=len(windows),
   correctness=[e for e in events if e.get('phase') in ('correctness','framebuffer','verification') or e.get('event') in ('reference_ready','verification_finished')])
  for key in ('emu_fps','draw_fps','core_mean_ms'):
   vals=[e[key] for e in windows if isinstance(e.get(key),(int,float))]
   run['all_logged_windows_'+key+'_median']=statistics.median(vals) if vals else None
  runs.append(run)
(out/'runs.json').write_text(json.dumps(runs,indent=2)+'\n')
(out/'correctness.json').write_text(json.dumps({r['job']: r['correctness'] for r in runs if r['correctness']},indent=2)+'\n')
# Only reviewed gameplay captures and numeric checks are published. Full device
# logs, recordings, receipts, and APKs remain in the private diagnostics folder.
evidence = out/'evidence'
if not saved:
 for r in runs:
  for name in ('screenshot.png', 'layout-check.json'):
   source = raw/r['folder']/name
   if source.exists():
    target = evidence/r['folder']/name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
 host = raw/'host-wasm-correctness.json'
 if host.exists():
  evidence.mkdir(parents=True, exist_ok=True)
  shutil.copyfile(host, evidence/host.name)
def esc(s): return html.escape(str(s)).replace("J-", "J‑")
def fmt(n): return '—' if n is None else f'{n:.3f}'
rows=[]
for r in runs:
 rows.append('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in [r['job'],r['device'],r['engine'],r['status'],fmt(r['compositor'].get('fps')),fmt(r['all_logged_windows_emu_fps_median']),r['window_count']])+'</tr>')
parts=['<!doctype html><meta charset="utf-8"><title>Android Native / WASM — 31 October 2026</title><style>body{font:17px system-ui;background:#111820;color:#e2edf4;max-width:1200px;margin:40px auto;padding:20px}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #455}img{max-width:100%}pre{white-space:pre-wrap}a{color:#8ed4ff}</style>',
 '<h1>Android Native / WASM — 31 October 2026</h1>',
 '<p><strong>Results:</strong> two Cast1 pairs measured Native 3.8276/3.8277 FPS versus WASM 0.4487/0.4444 FPS (about 8.6×). Corrected native passes frame-5800 WRAM and canonical pixels on Pixel and Cast1. Pixel native portrait and landscape hardware screenshots match every source pixel. Android WASM passes frame-5800 WRAM; the shipped WASM core passes the canonical image check on the host.</p>',
 '<p>Evidence review, not a release acceptance. Cast1 profiles request 120 seconds warmup and 120 seconds measurement. Pixel check captures are not matched performance profiles. Exact staged APK hashes and raw correctness events are in <a href="runs.json">runs.json</a>.</p>',
 '<p>Compositor FPS is measured by SurfaceFlinger. App emulation FPS below is the median of all retained log windows, including warmup; these are different quantities. APK versions differ (Native 0.1.9, WASM 0.1.8), so this is not a controlled engine-only experiment.</p>',
 '<table><tr><th>Job</th><th>Device</th><th>Engine</th><th>Status</th><th>Compositor FPS</th><th>App emu FPS</th><th>Log windows</th></tr>'+''.join(rows)+'</table>',
 '<p>Two runs per engine are available on Cast1; this small sample does not establish statistical confidence. Performance runs use the original frozen APKs, before the native RGB correction. Corrected-build correctness evidence is listed separately.</p>',
 '<h2>Correctness and hardware captures</h2><p>Fixed native RGB channel order, the frame-check skip across multi-step callbacks, and ROM staging from the nested roms directory. Frozen layout captures deliberately show zero emulation FPS; their HUD rates and accumulated backlog are not performance measurements.</p>']
for r in runs:
 if r['correctness']: parts += ['<h3>'+esc(r['job'])+'</h3><pre>'+esc(json.dumps(r['correctness'],indent=2))+'</pre>']
 if (evidence/r['folder']/'screenshot.png').exists():
  parts += ['<p>'+esc(r['device']+' '+r['engine']+' '+r['job'])+'</p><img src="evidence/'+r['folder']+'/screenshot.png">']
host = evidence/'host-wasm-correctness.json'
if host.exists():
 parts += ['<h3>Host WASM canonical framebuffer</h3><pre>'+esc(host.read_text())+'</pre>']
for r in runs:
 check = evidence/r['folder']/'layout-check.json'
 if check.exists():
  parts += ['<h3>Frozen hardware layout: '+esc(r['job'])+'</h3><pre>'+esc(check.read_text())+'</pre>']
parts += ['<h2>Limits and excluded attempts</h2><p>The first selector profiles J-d83eab5c4cac and J-87a688dc7b4d were cancelled and excluded after launch evidence showed MainActivity. J-f47fb920a3a5 had a coordinator worker crash before any measurement. Host /tmp pressure interrupted the initial build. Readd J-4cf702d6af1b recovered Cast1. Cast2 was unavailable. Tablet hardware coverage remains unverified. Frozen Pixel orientation checks are reported separately above. The WASM canonical framebuffer check ran on the host; Android WASM supplies the WRAM verdict only.</p>',
 '<p>Regenerate: <code>python3 android/tools/repeat-report.py</code>. Use <code>--from-saved</code> to regenerate from the committed summaries and reviewed captures without private diagnostics. Full device logs, recordings and APKs remain private.</p>']
measured = [r for r in runs if r['device'] == 'Cast1' and r['status'] in ('succeeded', 'completed') and r['compositor'].get('fps') is not None]
if measured:
 maximum = max(r['compositor']['fps'] for r in measured)
 svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="'+str(90+len(measured)*55)+'" role="img" aria-label="Measured compositor frames per second"><rect width="100%" height="100%" fill="#111820"/><g fill="#e2edf4" font-family="sans-serif"><text x="20" y="30" font-size="21">Cast1 presented frames per second · 120-second measurement</text>']
 for i,r in enumerate(measured):
  y=65+i*55; value=r['compositor']['fps']; color='#74d7ae' if r['engine'].startswith('Native') else '#8cc8ff'
  svg += [f'<text x="20" y="{y+19}">{esc(r["engine"])} {esc(r["job"])}</text><rect x="350" y="{y}" width="{value/maximum*500:.1f}" height="28" fill="{color}"/><text x="865" y="{y+19}">{value:.3f} FPS</text>']
 svg += ['</g></svg>']; (out/'presented-fps.svg').write_text(''.join(svg))
 parts.insert(5, '<img src="presented-fps.svg" alt="Per-run measured compositor FPS">')
(out/'comparison.html').write_text('\n'.join(parts).replace('J-', 'J‑'))
print(f'Wrote {len(runs)} evidence records to {out}')
