#!/usr/bin/env python3
"""02 - Record /metrics during a load run, and report the batching peaks.

This is the continuous-batching evidence (rubric item 9). The gauge that matters
is `llamacpp:n_busy_slots_per_decode`: the average number of slots doing useful
work per decode step. At one concurrent request it sits near 1. Under load it
should climb toward your `--parallel` count -- that climb *is* continuous
batching, and it is why throughput rises without latency rising as fast.

    make serve          # terminal 1
    make load-50        # terminal 2
    make metrics        # terminal 3, while the load is running
"""
from __future__ import annotations

import argparse
import csv
import pathlib
import re
import sys
import time

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402

TRACKED = (
    "llamacpp:n_busy_slots_per_decode",
    "llamacpp:requests_processing",
    "llamacpp:requests_deferred",
    "llamacpp:n_decode_total",
    "llamacpp:tokens_predicted_total",
    "llamacpp:prompt_tokens_total",
    "llamacpp:kv_cache_usage_ratio",
)

LINE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{[^}]*\})?\s+([0-9eE.+-]+)$")


def scrape(url: str) -> dict[str, float]:
    out: dict[str, float] = {}
    try:
        text = httpx.get(url, timeout=3.0).text
    except httpx.HTTPError:
        return out
    for raw in text.splitlines():
        if raw.startswith("#"):
            continue
        m = LINE.match(raw.strip())
        if m and m.group(1) in TRACKED:
            try:
                out[m.group(1)] = float(m.group(2))
            except ValueError:
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    port = labkit.server_port()
    ap.add_argument("--url", default=f"http://localhost:{port}/metrics")
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--label", default="", help="Tag the report, e.g. --label u50")
    args = ap.parse_args()

    labkit.banner(f"Recording {args.url} for {args.duration}s")
    print("  Drive load in another terminal (make load-50) or these will all read idle.\n")

    deadline = time.time() + args.duration
    rows: list[dict] = []
    misses = 0
    while time.time() < deadline:
        sample = scrape(args.url)
        if sample:
            sample["t"] = round(time.time(), 1)
            rows.append(sample)
            print(f"   busy_slots={sample.get('llamacpp:n_busy_slots_per_decode', 0):5.2f}  "
                  f"processing={sample.get('llamacpp:requests_processing', 0):3.0f}  "
                  f"deferred={sample.get('llamacpp:requests_deferred', 0):3.0f}  "
                  + (f"kv={sample['llamacpp:kv_cache_usage_ratio']:4.2f}  "
                     if 'llamacpp:kv_cache_usage_ratio' in sample else "") +
                  f"tok_pred={sample.get('llamacpp:tokens_predicted_total', 0):8.0f}")
        else:
            misses += 1
            print("   (scrape failed)")
            if not rows and misses >= 3:
                labkit.die(
                    f"Nothing at {args.url} after 3 tries.",
                    "Start the server first: make serve   (it enables --metrics by default)",
                )
        time.sleep(args.interval)

    if not rows:
        labkit.die(f"No samples collected from {args.url}.")

    suffix = f"-{args.label}" if args.label else ""
    csv_path = labkit.bench_dir() / f"02-server-metrics{suffix}.csv"
    fields = ["t"] + [k for k in TRACKED if any(k in r for r in rows)]
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    def peak(name: str) -> float:
        return max((r.get(name, 0.0) for r in rows), default=0.0)

    def peak_or_na(name: str, fmt: str = "{:.2f}") -> str:
        """Never render a gauge this build does not export as a measured value.

        `.get(name, 0)` turns "llama.cpp has no such metric" into a confident 0.00
        that is indistinguishable from a real reading, in a file the grader reads.
        kv_cache_usage_ratio is exactly that case on some builds.
        """
        if not any(name in r for r in rows):
            return f"n/a — not exported by llama.cpp `{labkit.LLAMA_CPP_BUILD}`"
        return fmt.format(peak(name))

    slots = labkit.parallel_slots()
    busy_peak = peak("llamacpp:n_busy_slots_per_decode")
    util = (100.0 * busy_peak / slots) if slots else 0.0
    md = f"""# 02 - Continuous batching under load{f" ({args.label})" if args.label else ""}

Host `{labkit.host_tag()}` · `--parallel {slots}` · {len(rows)} samples over
{args.duration}s at {args.interval}s intervals · raw CSV: `{csv_path.name}`

{labkit.md_table(["Gauge", "Peak observed"], [
    ["`n_busy_slots_per_decode` (avg/decode)", f"{busy_peak:.2f} of {slots} slots ({util:.0f}%)"],
    ["`requests_processing`", f"{peak('llamacpp:requests_processing'):.0f}"],
    ["`requests_deferred`", f"{peak('llamacpp:requests_deferred'):.0f}"],
    ["`kv_cache_usage_ratio`", peak_or_na("llamacpp:kv_cache_usage_ratio")],
    ["`tokens_predicted_total` (final)", f"{rows[-1].get('llamacpp:tokens_predicted_total', 0):.0f}"],
])}

Highest sampled value was **{busy_peak:.2f} of {slots}** slots. Note this gauge is llama.cpp's *average* busy slots per decode step, so the number below is the highest average we sampled, not an instantaneous maximum batch width. A peak near 1 means
requests were served one at a time -- either the load was too light to overlap, or
they arrived too far apart. A peak approaching `--parallel` means the scheduler was
genuinely packing concurrent requests into shared decode steps.
{"`requests_deferred` went above zero: more requests arrived than there were slots, so some waited. That wait is the queue time in your P95." if peak("llamacpp:requests_deferred") > 0 else "`requests_deferred` stayed at zero: every request found a free slot on arrival."}

## Your observation (required -- replace this line)

_What was the peak batch width, and does it match the effective concurrency in
`02-server-results.md`? If the two disagree, which do you trust and why?_
"""
    out = labkit.write_report(f"02-server-batching{suffix}.md", md)
    print(f"\n==> Wrote {csv_path.relative_to(labkit.repo_root())}")
    print(f"==> Wrote {out.relative_to(labkit.repo_root())}")
    print(f"\n  Highest sampled n_busy_slots_per_decode = {busy_peak:.2f} of {slots} slots")
    return 0


if __name__ == "__main__":
    sys.exit(main())
