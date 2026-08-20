#!/usr/bin/env python3
"""01 - Tune: find the thread count that actually wins on YOUR machine.

This is the core lab's before/after engine, and the source of the
"single change that mattered most" paragraph in REFLECTION.md section 5.
It needs no compiler and no GPU: `llama-bench` ships in the prebuilt runtime.

The expected shape: decode throughput climbs to roughly your *physical* core
count, then flattens or drops. Decode is memory-bandwidth-bound, so extra
threads past that point fight each other for the same memory channels instead
of adding useful work. Whether your machine follows that curve -- and where its
knee sits -- is the thing worth reporting.

    make tune                      # threads sweep (default)
    .venv/bin/python labs/01-measure/tune.py --metric pp512    # tune prefill instead of decode
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402


def thread_grid(hw: dict) -> list[int]:
    physical = hw.get("cpu", {}).get("cores_physical") or 4
    logical = hw.get("cpu", {}).get("cores_logical") or physical
    grid = {1, max(physical // 2, 1), physical}
    if logical > physical:
        grid.add(logical)          # hyperthreads: usually flat or worse
    if logical >= 8:
        grid.add(logical * 2)      # deliberate oversubscription, to show the drop
    return sorted(t for t in grid if t > 0)


def main() -> int:
    ap = argparse.ArgumentParser(description="Thread-count tuning sweep (core lab).")
    ap.add_argument("--metric", default="tg128",
                    help="llama-bench metric: tg128 = decode (default), pp512 = prefill")
    ap.add_argument("--reps", type=int, default=2, help="llama-bench repetitions per point")
    args = ap.parse_args()

    hw = labkit.load_hardware()
    active = labkit.load_active()
    model = str(labkit.repo_root() / active["primary_model"])
    ngl = labkit.n_gpu_layers(hw)
    grid = thread_grid(hw)
    physical = hw.get("cpu", {}).get("cores_physical")
    logical = hw.get("cpu", {}).get("cores_logical")

    labkit.banner(f"Thread sweep on {pathlib.Path(model).name}")
    print(f"  cores   : {physical} physical · {logical} logical")
    print(f"  grid    : {grid}")
    print(f"  metric  : {args.metric}   ngl: {ngl}")
    print("  (each point runs llama-bench -- a few minutes total)\n")

    is_prefill = args.metric.startswith("pp")
    bench_shape = ["-p", args.metric[2:], "-n", "0"] if is_prefill else ["-p", "0", "-n", "128"]

    rows: list[dict] = []
    for t in grid:
        out = labkit.run_bench(
            ["-m", model, "-t", str(t), "-ngl", str(ngl), *bench_shape, "-r", str(args.reps)]
        )
        tps = labkit.bench_metric(out, args.metric)
        rows.append({"threads": t, "tok_s": tps})
        print(f"   -t {t:3d}   {args.metric} = {tps:7.1f} tok/s")

    if not any(r["tok_s"] for r in rows):
        labkit.die(
            "llama-bench returned no numbers.",
            "Run it by hand to see the error:",
            f"  {labkit.runtime_bin('llama-bench')} -m {model} -t {grid[0]} -ngl {ngl}",
        )

    best = max(rows, key=lambda r: r["tok_s"])
    baseline = next((r for r in rows if r["threads"] == (physical or grid[0])), rows[0])
    gain = (best["tok_s"] / baseline["tok_s"]) if baseline["tok_s"] else 1.0
    worst = min((r for r in rows if r["tok_s"] > 0), key=lambda r: r["tok_s"])
    spread = (best["tok_s"] / worst["tok_s"]) if worst["tok_s"] else 1.0

    table = labkit.md_table(
        ["threads (-t)", f"{args.metric} (tok/s)", "vs best"],
        [[r["threads"], f"{r['tok_s']:.1f}",
          f"{100 * r['tok_s'] / best['tok_s']:.0f}%" if best["tok_s"] else "-"] for r in rows],
    )

    md = f"""# 01 - Tune: thread-count sweep

Model `{pathlib.Path(model).name}` · host `{labkit.host_tag()}` · llama.cpp `{labkit.LLAMA_CPP_BUILD}`
CPU: **{physical} physical · {logical} logical** cores · `ngl={ngl}` · metric `{args.metric}`

{table}

**Best**: `-t {best['threads']}` at {best['tok_s']:.1f} tok/s
**Slowest tested**: `-t {worst['threads']}` at {worst['tok_s']:.1f} tok/s ({spread:.2f}x spread)
**Against the physical-core default** (`-t {baseline['threads']}`, {baseline['tok_s']:.1f} tok/s): {gain:.2f}x

Use this in your run:

```bash
LAB_N_THREADS={best['threads']} make bench
```

## Your explanation (required -- replace this line)

_Where is the knee, and why there? If the peak sits at your physical core count
and drops above it, say what the extra threads are competing for. If your curve
does something else -- flat, or still climbing at 2x logical cores -- say that
instead and reason about why. A result that contradicts the expected shape is
worth more than one that matches it, as long as you explain it._
"""
    out = labkit.write_report(f"01-tuning-{args.metric}.md", md,
                              {"metric": args.metric, "cores": {"physical": physical,
                               "logical": logical}, "rows": rows, "best": best})
    print("\n" + md)
    print(f"==> Wrote {out.relative_to(labkit.repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
