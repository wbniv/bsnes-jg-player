#!/usr/bin/env python3
"""Stage a hash-verified core and the configured demo; no Android SDK required."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "ios" / "generated"
CORE_SHA = "a8e0fd36711406198afe1110ddc6960c9d795f4ab73d0badd8878396ac3d0c42"
STAGE.mkdir(parents=True, exist_ok=True)
archive = ROOT / "vendor" / "bsnes-2.1.0.tar.gz"
if not archive.exists():
    archive.parent.mkdir(exist_ok=True)
    with urllib.request.urlopen("https://gitlab.com/jgemu/bsnes/-/archive/2.1.0/bsnes-2.1.0.tar.gz") as response:
        archive.write_bytes(response.read())
data = archive.read_bytes()
assert hashlib.sha256(data).hexdigest() == CORE_SHA, "Core archive checksum mismatch"
with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
    tar.extractall(STAGE, filter="data")
core = STAGE / "bsnes-2.1.0"
# Power reconstructs Audio; its callback must be initialized before first use.
header = core / "src/audio.hpp"
text = header.read_text()
assert "void (*audioFrame)(const void*, std::size_t);" in text
header.write_text(text.replace("void (*audioFrame)(const void*, std::size_t);",
                               "void (*audioFrame)(const void*, std::size_t) = nullptr;"))
source = core / "src/audio.cpp"
text = source.read_text()
assert "  audioFrame(udata, _spf);" in text
source.write_text(text.replace("  audioFrame(udata, _spf);", "  if (audioFrame) audioFrame(udata, _spf);"))
demo = json.loads((ROOT / "demo-rom.json").read_text())
rom = ROOT / "web/roms" / (demo["slug"] + ".sfc")
assert hashlib.sha256(rom.read_bytes()).hexdigest() == demo["sha256"], "Demo ROM checksum mismatch"
shutil.copyfile(rom, STAGE / "demo.sfc")
shutil.copyfile(ROOT / "demo-rom.json", STAGE / "demo-rom.json")
shutil.copyfile(ROOT / "LICENSE", STAGE / "LICENSE.txt")
shutil.copyfile(ROOT / "NOTICE", STAGE / "NOTICE.txt")
check = demo["selfcheck"]
(STAGE / "DemoConfig.h").write_text(
    f'#define DEMO_TITLE "{demo["title"]}"\n'
    f'#define DEMO_FRAMES {int(check["frames"])}\n'
    f'#define DEMO_OFFSET {int(check["offset"], 0)}\n'
    f'#define DEMO_WANT {int(check["want"], 0)}\n')
print(f"Staged {demo['title']} ({rom.stat().st_size} bytes); core and ROM SHA-256 verified")
