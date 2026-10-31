#!/usr/bin/env python3
"""Compare native hardware game-rectangle pixel centers with the frozen reference."""
import argparse, json
from pathlib import Path
from PIL import Image, ImageChops
parser = argparse.ArgumentParser()
parser.add_argument('evidence', type=Path)
args = parser.parse_args()
records = []
for line in (args.evidence / 'logcat.txt').read_text().splitlines():
    if 'BJG_TV_METRIC' not in line:
        continue
    try:
        event = json.loads(line[line.index('{'):])
    except (ValueError, json.JSONDecodeError):
        continue
    if event.get('event') == 'renderer_health' and event.get('frame') == 5800:
        records.append(event)
if not records:
    raise SystemExit('No frozen frame-5800 renderer geometry in evidence')
record = records[-1]
screen = Image.open(args.evidence / 'screenshot.png').convert('RGB')
reference = Image.open(Path(__file__).resolve().parents[1] / 'fixture/reference-5800.png').convert('RGB')
# The SurfaceView may exclude a display cutout; normalized WebView coordinates
# therefore cannot be multiplied by the full screenshot dimensions. Locate the
# frozen ROM's non-black palette in the screenshot, then verify every source
# pixel, including black pixels and all four edges, inside that rectangle.
palette = set(reference.get_flattened_data()) - {(0, 0, 0)}
mask = Image.new('L', screen.size)
mask.putdata([255 if pixel in palette else 0 for pixel in screen.get_flattened_data()])
bounds = mask.getbbox()
if bounds is None:
    raise SystemExit('No canonical palette found in the hardware screenshot')
x, y, right, bottom = bounds
width, height = right - x, bottom - y
if width < reference.width or height < reference.height:
    raise SystemExit('Detected image is smaller than the source framebuffer')
actual = Image.new('RGB', reference.size)
for sy in range(reference.height):
    for sx in range(reference.width):
        px = min(screen.width - 1, int(x + (sx + .5) * width / reference.width))
        py = min(screen.height - 1, int(y + (sy + .5) * height / reference.height))
        actual.putpixel((sx, sy), screen.getpixel((px, py)))
diff = ImageChops.difference(actual, reference)
different = sum(pixel != (0, 0, 0) for pixel in diff.get_flattened_data())
result = dict(frame=5800, screen=list(screen.size), game_rect_pixels=[x,y,width,height],
              aspect=width / height, normalized_content_rect=record['game_rect'], geometry_source='canonical palette footprint in screenshot', differentPixels=different, pixels=reference.width*reference.height,
              gl_error=record['gl_error'], status='pass' if different == 0 and abs(width/height - 4/3) < .002 and record['gl_error'] == 0 else 'fail')
actual.save(args.evidence / 'sampled-frame-5800.png')
diff.save(args.evidence / 'sampled-frame-5800-diff.png')
(args.evidence / 'layout-check.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
raise SystemExit(0 if result['status'] == 'pass' else 1)
