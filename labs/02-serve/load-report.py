#!/usr/bin/env python3
"""02 - Load report: turn two locust runs into the saturation story.

Reads the CSVs written by `make load-10` and `make load-50` and answers the
question the deck actually cares about: what happened to latency when you asked
the same server to do 5x the work?

Effective concurrency comes from Little's Law -- L = lambda * W (arrival rate x
time in system). Compare it to the server's --parallel slot count: if it exceeds
the slots, requests are queueing, and the P95 inflation you see is queue time,
not compute time. That is the whole goodput-vs-throughput argument in one number.

    make load-10 && make load-50 && make load-report
"""
from __future__ import annotations

import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402


def read_locust(prefix: pathlib.Path) -> dict | None:
    """Pull the Aggregated row out of a locust --csv stats file."""
    path = prefix.with_name(prefix.name + "_stats.csv")
    if not path.exists():
        return None
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    agg = next((r for r in rows if r.get("Name") in ("Aggregated", "")), None)
    if agg is None:
        return None

    def num(*keys: str) -> float:
        for k in keys:
            v = (agg.get(k) or "").strip()
            if v and v.upper() != "N/A":
                try:
                    return float(v)
                except ValueError:
                    continue
        return 0.0

    reqs = num("Request Count")
    fails = num("Failure Count")
    return {
        "requests": int(reqs),
        "failures": int(fails),
        "fail_pct": (100.0 * fails / reqs) if reqs else 0.0,
        "rps": num("Requests/s"),
        "avg_ms": num("Average Response Time"),
        "p50_ms": num("50%", "Median Response Time"),
        "p95_ms": num("95%"),
        "p99_ms": num("99%"),
        "max_ms": num("Max Response Time"),
    }


def main() -> int:
    bench = labkit.bench_dir()
    runs: list[tuple[int, dict]] = []
    for users in (10, 50):
        data = read_locust(bench / f"locust-{users}")
        if data:
            runs.append((users, data))
        else:
            print(f"    (no CSV for {users} users at benchmarks/locust-{users}_stats.csv)")

    if not runs:
        labkit.die(
            "No locust CSVs found.",
            "Run the load tests first:  make load-10   then   make load-50",
        )

    slots = labkit.parallel_slots()
    rows = []
    for users, d in runs:
        # Little's Law: requests in the system = arrival rate x time in system.
        concurrency = d["rps"] * (d["avg_ms"] / 1000.0)
        rows.append([
            users, d["requests"], f"{d['rps']:.2f}", f"{d['p50_ms']:.0f}",
            f"{d['p95_ms']:.0f}", f"{d['p99_ms']:.0f}",
            f"{concurrency:.1f}", f"{d['fail_pct']:.1f}%",
        ])

    table = labkit.md_table(
        ["Users", "Reqs", "RPS", "P50 (ms)", "P95 (ms)", "P99 (ms)", "Eff. concurrency", "Failures"],
        rows,
    )

    analysis = ""
    thin_sample = min((d["requests"] for _, d in runs), default=0) < 20
    if len(runs) == 2:
        (u1, a), (u2, b) = runs
        user_ratio = u2 / u1
        rps_ratio = (b["rps"] / a["rps"]) if a["rps"] else 0.0
        p95_ratio = (b["p95_ms"] / a["p95_ms"]) if a["p95_ms"] else 0.0
        conc = b["rps"] * (b["avg_ms"] / 1000.0)
        efficiency = (rps_ratio / user_ratio) if user_ratio else 0.0
        slot_util = (conc / slots) if slots else 0.0

        # Two independent signals. Throughput scaling is the reliable one; slot
        # utilisation corroborates it by naming *what* ran out.
        flat_throughput = efficiency < 0.5
        slots_pegged = slot_util >= 0.85

        if flat_throughput and slots_pegged:
            verdict = "**Saturated.**"
            because = (
                f"Throughput delivered only {rps_ratio:.2f}x for {user_ratio:.0f}x the offered "
                f"load, and effective concurrency ({conc:.1f}) is at or above all {slots} decode "
                f"slots. Saturation sets in somewhere at or below {u2} users; the load you added "
                f"beyond that point became queue time rather than throughput."
            )
        elif flat_throughput:
            verdict = "**Saturated.**"
            because = (
                f"Throughput stopped scaling ({rps_ratio:.2f}x delivered for {user_ratio:.0f}x "
                f"offered, {efficiency * 100:.0f}% of linear) even though effective concurrency "
                f"({conc:.1f}) sits below {slots} slots. Something other than decode-slot count "
                f"is the limit -- look at memory bandwidth, or context/KV pressure."
            )
        elif slots_pegged:
            verdict = "**At capacity, still scaling.**"
            because = (
                f"All {slots} decode slots are busy (effective concurrency {conc:.1f}) but "
                f"throughput still rose {rps_ratio:.2f}x. You are at the knee -- the next "
                f"increment of load is where P95 starts to run away."
            )
        else:
            verdict = "**Not saturated.**"
            because = (
                f"Throughput scaled {rps_ratio:.2f}x and effective concurrency ({conc:.1f}) is "
                f"below {slots} slots. Push the user count higher until RPS flattens, and report "
                f"where that knee sits."
            )

        goodput = (
            f"Throughput moved {rps_ratio:.2f}x while P95 moved {p95_ratio:.2f}x. That gap is the "
            f"goodput argument: past saturation you buy throughput by spending latency, and if "
            f"your SLO is a P95 target then the requests you added are no longer being served "
            f"within it. (This lab does not fix an SLO number for you -- pick one in your "
            f"write-up and state how much goodput you keep at it.)"
            if p95_ratio > rps_ratio else
            f"P95 grew no faster than throughput ({p95_ratio:.2f}x vs {rps_ratio:.2f}x), so this "
            f"server still has headroom at {u2} users."
        )

        analysis = f"""
## What these two runs say

| Going from {u1} to {u2} users | |
|:--|--:|
| Offered load | {user_ratio:.0f}x |
| Throughput actually delivered | **{rps_ratio:.2f}x** ({efficiency * 100:.0f}% of linear) |
| P95 latency | **{p95_ratio:.2f}x** |
| Effective concurrency at {u2} users | {conc:.1f} vs `--parallel {slots}` slots (occupancy/slot ratio {slot_util:.2f}) |

{verdict} {because}

{goodput}
"""
        if thin_sample:
            analysis += f"""
> **Small sample.** Only {min(a['requests'], b['requests'])} requests completed in the
> shorter run, so these percentiles are indicative rather than solid. Note also that
> locust averages only *completed* requests: when the run ends with requests still
> queued, effective concurrency is an **under**-estimate. Trust the throughput-scaling
> row over the concurrency row here, and run longer (`-t 3m`) if you want firmer numbers.
"""

    md = f"""# 02 - Serve: load test + saturation reading

Host `{labkit.host_tag()}` · llama.cpp `{labkit.LLAMA_CPP_BUILD}` ·
`--parallel {slots}` · `ctx={labkit.n_ctx()}` · `threads={labkit.threads()}` ·
`ngl={labkit.n_gpu_layers()}`

{table}

*Effective concurrency = RPS x average latency (Little's Law) -- how many requests were
really in flight, regardless of how many users locust simulated. It counts queued requests
too, so the occupancy/slot ratio can legitimately exceed 1.0; it is occupancy, not
utilisation. For true slot utilisation use the server's own gauges (`make metrics`).*
{analysis}
## Your reading (required -- replace this line)

_Where does your server saturate, and what is the evidence? Name the number that
convinced you. Then say what you would change first to raise goodput at your SLO --
and why that knob and not another._
"""
    out = labkit.write_report("02-server-results.md", md,
                              {"slots": slots, "runs": [{"users": u, **d} for u, d in runs]})
    print("\n" + md)
    print(f"==> Wrote {out.relative_to(labkit.repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
