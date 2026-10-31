#!/usr/bin/env python3
"""Apply documented Android-only safety fixes to the pinned core checkout."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
header = root / "src/audio.hpp"
source = root / "src/audio.cpp"

def replace_once(path: Path, old: str, new: str, already: str) -> None:
    text = path.read_text()
    if already in text:
        return
    if text.count(old) != 1:
        raise SystemExit(f"Cannot apply pinned Android core patch to {path}: expected one match for {old!r}")
    path.write_text(text.replace(old, new, 1))

replace_once(
    header,
    "  void (*audioFrame)(const void*, std::size_t);",
    "  void (*audioFrame)(const void*, std::size_t) = nullptr;",
    "  void (*audioFrame)(const void*, std::size_t) = nullptr;",
)
replace_once(
    source,
    "  audioFrame(udata, _spf);",
    "  if (audioFrame) audioFrame(udata, _spf);",
    "  if (audioFrame) audioFrame(udata, _spf);",
)
