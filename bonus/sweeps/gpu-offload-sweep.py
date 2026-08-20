#!/usr/bin/env python3
"""BONUS - GPU offload sweep: how many layers should live on the accelerator?

`-ngl N` puts N transformer layers on the GPU and leaves the rest on the CPU.
The interesting region is partial offload: when a model does not fit in VRAM,
where is the best split? The curve also flattens once N passes the model's actual
layer count, which is a useful sanity check that you are reading the right knob.

Needs CUDA / Metal / Vulkan / ROCm. On a CPU-only machine, run
`make tune` (thread sweep) instead -- that is where your speedup lives.

    make sweep-gpu
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="GPU layer-offload sweep (bonus).")
    ap.add_argument("--grid", default="0,8,16,24,32,99")
    ap.add_argument("--metric", default="tg128")
    ap.add_argument("--reps", type=int, default=2)
    args = ap.parse_args()

    hw = labkit.load_hardware()
    if not labkit.any_gpu(hw):
        print("No accelerator detected in hardware.json -- nothing to sweep.")
        print("On a CPU-only machine the equivalent exercise is: make tune")
        return 1

    model = str(labkit.repo_root() / labkit.load_active()["primary_model"])
    threads = labkit.threads(hw)
    grid = [int(x) for x in args.grid.split(",") if x.strip()]
    active = [k for k, v in hw["gpu"]["backends"].items() if v and k != "cpu_only"]
    is_prefill = args.metric.startswith("pp")
    shape = ["-p", args.metric[2:], "-n", "0"] if is_prefill else ["-p", "0", "-n", "128"]

    labkit.banner(f"GPU offload sweep on {pathlib.Path(model).name}")
    print(f"  backend(s): {', '.join(active)} · threads {threads} · grid {grid}\n")

    rows = []
    for ngl in grid:
        out = labkit.run_bench(["-m", model, "-t", str(threads), "-ngl", str(ngl),
                                *shape, "-r", str(args.reps)])
        tps = labkit.bench_metric(out, args.metric)
        rows.append({"ngl": ngl, "tok_s": tps})
        print(f"   -ngl {ngl:3d}   {args.metric} = {tps:8.1f} tok/s")

    if not any(r["tok_s"] for r in rows):
        labkit.die("llama-bench produced no numbers.")

    cpu_only = next((r["tok_s"] for r in rows if r["ngl"] == 0), 0.0)
    best = max(rows, key=lambda r: r["tok_s"])
    table = labkit.md_table(
        ["-ngl", f"{args.metric} (tok/s)", "vs -ngl 0", "vs best"],
        [[r["ngl"], f"{r['tok_s']:.1f}",
          f"{r['tok_s'] / cpu_only:.2f}x" if cpu_only else "-",
          f"{100 * r['tok_s'] / best['tok_s']:.0f}%"] for r in rows],
    )
    speedup = (best["tok_s"] / cpu_only) if cpu_only else 0.0
    md = f"""# Bonus - GPU offload sweep

Host `{labkit.host_tag()}` · backend(s) `{', '.join(active)}` ·
llama.cpp `{labkit.LLAMA_CPP_BUILD}` · `threads={threads}` · metric `{args.metric}`

{table}

Best: `-ngl {best['ngl']}` at {best['tok_s']:.1f} tok/s
{f"-- {speedup:.2f}x faster than CPU-only." if speedup else ""}

Where the curve flattens tells you the model ran out of layers to move. Where it
*peaks below* full offload tells you something did not fit and the accelerator
started paying to fetch weights it could not hold.

## Your finding (required -- replace this line)

_Is full offload best on your machine? If the curve peaked at a partial value,
what ran out first -- VRAM, or bandwidth between host and device?_
"""
    out_path = labkit.write_report("bonus-gpu-offload-sweep.md", md, rows)
    print("\n" + md)
    print(f"==> Wrote {out_path.relative_to(labkit.repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
