#!/usr/bin/env python3
"""One-shot lab setup: probe -> runtime -> model.

Cross-platform and compiler-free. The virtualenv and pip install happen before
this (Makefile on macOS/Linux, bootstrap.ps1 on Windows); everything after is
identical on every OS, so it lives here instead of in three shell scripts.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def step(title: str, script: str, *args: str) -> None:
    labkit.banner(title)
    rc = subprocess.run([sys.executable, str(HERE / script), *args], check=False).returncode
    if rc != 0:
        labkit.die(f"{script} failed (exit {rc}).", "Fix the error above and re-run: make setup")


def main() -> int:
    step("1/3  Probing hardware", "detect-hardware.py")

    hw = labkit.load_hardware()
    rec = hw["recommendation"]
    if not rec["ram_sufficient"]:
        print(f"\n  !! {hw['ram_gb']} GB RAM < {labkit.MIN_RAM_GB} GB floor.")
        print("     Setup will continue, but expect swapping. The supported path for")
        print("     this machine is cloud/Day20-lab.ipynb (Colab / Kaggle).")

    step("2/3  Fetching the llama.cpp runtime", "fetch-runtime.py")
    # Hand the probe's choice to download-model.py. Without this it resolves
    # LAB_MODEL -> models/active.json (absent on a fresh setup) -> DEFAULT_MODEL,
    # so a <8 GB laptop was told "Downloading Qwen3.5 0.8B" and got Gemma's 5.2 GB.
    #
    # Only on a FRESH setup: if active.json already records a choice, that choice
    # wins. The probe recommends purely on RAM, so overriding here would drag a
    # 16 GB student who deliberately picked the small model back to the 5.2 GB one.
    if rec.get("model_key") and not labkit.active_json().exists():
        os.environ.setdefault("LAB_MODEL", rec["model_key"])
    spec = labkit.model_spec(labkit.model_key())
    step(f"3/3  Downloading {spec['label']} (two quantizations, ~{spec['download_gb']} GB)",
         "download-model.py")

    labkit.banner("Setup complete")
    win = sys.platform == "win32"
    run = ".\\lab.ps1" if win else "make"
    print("  Next:")
    print(f"    {run} bench      # track 01 - TTFT / TPOT / percentiles, both quants")
    print(f"    {run} tune       # track 01 - find your best thread count (before/after)")
    print(f"    {run} serve      # track 02 - OpenAI-compatible server + /metrics on :8080")
    print()
    print("  Full walkthrough: GUIDE.md")
    if win:
        print("  (On Windows use .\\lab.ps1 <target> everywhere GUIDE.md says `make <target>`.)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
