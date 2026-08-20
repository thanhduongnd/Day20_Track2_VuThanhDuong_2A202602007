#!/usr/bin/env python3
"""BONUS - Batch-size sweep: llama.cpp's chunked prefill knob.

`-b` is the logical prefill batch; `-ub` is the physical micro-batch actually
handed to the kernel. Together they are the same trade-off vLLM exposes as
chunked prefill: bigger chunks amortize per-step overhead (better throughput) but
occupy the device longer per step (worse TTFT for whatever is queued behind).

    make sweep-batch
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402

GRID = [(128, 128), (256, 256), (512, 256), (512, 512), (1024, 512), (2048, 512)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Prefill batch/micro-batch sweep (bonus).")
    ap.add_argument("--prompt-len", type=int, default=512)
    ap.add_argument("--reps", type=int, default=2)
    args = ap.parse_args()

    hw = labkit.load_hardware()
    model = str(labkit.repo_root() / labkit.load_active()["primary_model"])
    threads, ngl = labkit.threads(hw), labkit.n_gpu_layers(hw)
    metric = f"pp{args.prompt_len}"

    labkit.banner(f"Batch-size sweep on {pathlib.Path(model).name}")
    print(f"  metric {metric} · threads {threads} · ngl {ngl}\n")

    rows = []
    for b, ub in GRID:
        out = labkit.run_bench([
            "-m", model, "-t", str(threads), "-ngl", str(ngl),
            "-b", str(b), "-ub", str(ub),
            "-p", str(args.prompt_len), "-n", "0", "-r", str(args.reps),
        ])
        tps = labkit.bench_metric(out, metric)
        rows.append({"batch": b, "ubatch": ub, "pp_tok_s": tps})
        print(f"   -b {b:4d}  -ub {ub:4d}   {metric} = {tps:8.1f} tok/s")

    if not any(r["pp_tok_s"] for r in rows):
        labkit.die("llama-bench produced no numbers.")

    best = max(rows, key=lambda r: r["pp_tok_s"])
    worst = min((r for r in rows if r["pp_tok_s"] > 0), key=lambda r: r["pp_tok_s"])
    table = labkit.md_table(
        ["-b (logical)", "-ub (micro)", f"{metric} (tok/s)", "vs best"],
        [[r["batch"], r["ubatch"], f"{r['pp_tok_s']:.1f}",
          f"{100 * r['pp_tok_s'] / best['pp_tok_s']:.0f}%"] for r in rows],
    )
    md = f"""# Bonus - Batch-size sweep (chunked prefill)

Host `{labkit.host_tag()}` · llama.cpp `{labkit.LLAMA_CPP_BUILD}` ·
`threads={threads}` `ngl={ngl}` · metric `{metric}`

{table}

Best: `-b {best['batch']} -ub {best['ubatch']}` at {best['pp_tok_s']:.1f} tok/s
({best['pp_tok_s'] / worst['pp_tok_s']:.2f}x the slowest point tested).

This sweep only measures the throughput half of the trade. The cost it hides is
TTFT for queued requests: a larger micro-batch holds the device longer per step,
so anything waiting behind it waits longer. To see both halves, re-run
`make load-50` with your best and worst settings via
`.venv/bin/python labs/02-serve/serve.py -- -b N -ub M` and compare P95.

## Your finding (required -- replace this line)

_Which setting would you run in production, and what would you need to measure to
be sure it does not hurt the P95 of a contended server?_
"""
    out_path = labkit.write_report("bonus-batch-size-sweep.md", md, rows)
    print("\n" + md)
    print(f"==> Wrote {out_path.relative_to(labkit.repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
