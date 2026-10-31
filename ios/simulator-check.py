#!/usr/bin/env python3
"""Boot an available iPhone, require the ROM self-check, then capture Metal UI."""
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ios/artifacts"
OUT.mkdir(exist_ok=True)
APP = "org.bsnesjg.player.ios"
def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs).stdout.strip()

devices = json.loads(run("xcrun", "simctl", "list", "devices", "available", "--json"))
choices = [d for runtime, ds in devices["devices"].items() if ".iOS-" in runtime
           for d in ds if d["name"].startswith("iPhone")]
if not choices:
    raise SystemExit("No available iPhone simulator runtime on the pinned Xcode image")
device = next((d for d in choices if d["name"] == "iPhone 16"), choices[0])
udid = device["udid"]
(OUT / "simulator.json").write_text(json.dumps(device, indent=2))
try:
    if device["state"] != "Booted":
        run("xcrun", "simctl", "boot", udid)
    run("xcrun", "simctl", "bootstatus", udid, "-b", timeout=180)
    run("xcrun", "simctl", "install", udid, str(ROOT / "ios/build/Release-iphonesimulator/BsnesPlayer.app"))
    container = Path(run("xcrun", "simctl", "get_app_container", udid, APP, "data"))
    result = container / "Documents/selfcheck.json"
    result.unlink(missing_ok=True)
    run("xcrun", "simctl", "launch", udid, APP, "--self-test")
    deadline = time.monotonic() + 120
    while not result.exists() and time.monotonic() < deadline:
        time.sleep(1)
    if not result.exists():
        raise RuntimeError("Self-check timed out (possible core crash); no PASS recorded")
    proof = json.loads(result.read_text())
    (OUT / "selfcheck.json").write_text(json.dumps(proof, indent=2))
    assert proof["pass"], proof
    run("xcrun", "simctl", "launch", udid, APP)
    time.sleep(12)
    run("xcrun", "simctl", "io", udid, "screenshot", str(OUT / "iphone.png"))
    print("PASS", device["name"], json.dumps(proof))
finally:
    subprocess.run(["xcrun", "simctl", "terminate", udid, APP], capture_output=True)
    subprocess.run(["xcrun", "simctl", "shutdown", udid], capture_output=True)
