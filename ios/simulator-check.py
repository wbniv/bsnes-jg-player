#!/usr/bin/env python3
"""Boot an available iPhone, require the ROM self-check, then capture Metal UI."""
import json
from pathlib import Path
import subprocess
import shutil
import time
import os

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ios/artifacts"
OUT.mkdir(exist_ok=True)
APP = "org.bsnesjg.player.ios"
def run(*args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(f"{args!r} failed ({result.returncode}):\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()

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
    run("xcrun", "simctl", "launch", udid, APP,
        env={**os.environ, "SIMCTL_CHILD_BJG_AUDIO_OFFLINE": "1"})
    time.sleep(12)
    run("xcrun", "simctl", "io", udid, "screenshot", str(OUT / "iphone.png"))
    print("PASS", device["name"], json.dumps(proof))
    run("xcrun", "simctl", "terminate", udid, APP)
    tablets = [d for runtime, ds in devices["devices"].items() if ".iOS-" in runtime
               for d in ds if d["name"].startswith("iPad")]
    if not tablets:
        raise RuntimeError("No available iPad simulator for the required layout matrix")
    tablet = tablets[0]
    for label, target in [("iphone", device), ("ipad", tablet)]:
        target_id = target["udid"]
        if target_id != udid:
            if target["state"] != "Booted":
                run("xcrun", "simctl", "boot", target_id)
            run("xcrun", "simctl", "bootstatus", target_id, "-b", timeout=300)
        (OUT / f"{label}-device.json").write_text(json.dumps(target, indent=2))
        result_bundle = OUT / f"ui-{label}.xcresult"
        command = ["xcodebuild", "-project", str(ROOT / "ios/build/BsnesPlayer.xcodeproj"),
                   "-scheme", "BsnesPlayer", "-configuration", "Release",
                   "-destination", f"platform=iOS Simulator,id={target_id}",
                   "-parallel-testing-enabled", "NO", "-resultBundlePath", str(result_bundle),
                   "CODE_SIGNING_ALLOWED=NO", "test"]
        try:
            with (OUT / f"ui-{label}.log").open("w") as log_file:
                tested = subprocess.run(command, stdout=log_file, stderr=subprocess.STDOUT)
            subprocess.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(result_bundle),
                            "--output-path", str(OUT / f"{label}-screenshots")], check=True)
            if tested.returncode:
                print((OUT / f"ui-{label}.log").read_text()[-18000:], flush=True)
                raise RuntimeError(f"{label} UI validation failed; see ui-{label}.log and .xcresult")
            print(f"PASS {label}: touch, core input polling, audio graph, lifecycle, portrait/landscape", flush=True)
        finally:
            if target_id != udid:
                subprocess.run(["xcrun", "simctl", "shutdown", target_id], capture_output=True)
except Exception:
    # Preserve diagnostics before shutting down the ephemeral CI simulator.
    log = subprocess.run([
        "xcrun", "simctl", "spawn", udid, "log", "show", "--last", "3m",
        "--style", "compact", "--predicate", 'process == "BsnesPlayer"'
    ], text=True, capture_output=True, timeout=30)
    (OUT / "simulator-failure.log").write_text(log.stdout + log.stderr)
    for report in (Path.home() / "Library/Logs/DiagnosticReports").glob("BsnesPlayer*"):
        if report.is_file():
            shutil.copyfile(report, OUT / report.name)
    raise
finally:
    subprocess.run(["xcrun", "simctl", "terminate", udid, APP], capture_output=True)
    subprocess.run(["xcrun", "simctl", "shutdown", udid], capture_output=True)
