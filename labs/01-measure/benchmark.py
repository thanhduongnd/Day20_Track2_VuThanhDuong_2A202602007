#!/usr/bin/env python3
"""01 - Measure: TTFT, TPOT, and percentiles for both quantizations.

Starts llama-server itself, streams a fixed prompt set through the
OpenAI-compatible endpoint, and tears the server down again -- so you get real
over-the-wire latency numbers without juggling two terminals yet.

TTFT is measured client-side (what a user actually waits for). Token counts come
from llama.cpp's own `timings` block when the server reports it, so TPOT is not
guessed from chunk counts.

    make bench          # or: .venv/bin/python labs/01-measure/benchmark.py
"""
from __future__ import annotations

import json
import math
import pathlib
import statistics
import sys
import time

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402

PROMPTS = [
    "Explain TTFT and TPOT in one sentence each.",
    "Write a haiku about KV cache fragmentation.",
    "What is PagedAttention and what problem does it solve?",
    "List three reasons goodput@SLO matters more than peak throughput.",
    "Compare 4-bit and 2-bit quantization in three bullets.",
    "Why does FlashAttention need less memory than naive attention?",
    "What is the difference between continuous and static batching?",
    "Sketch the steps of speculative decoding.",
    "Explain prefix caching in two sentences.",
    "When should you use disaggregated prefill/decode serving?",
]

BENCH_PORT = 8099  # off the main :8080 so a running server is not disturbed


def pct(data: list[float], q: float) -> float:
    """Nearest-rank percentile: index = ceil(q/100 * n), 1-based.

    Honest for the small n this lab uses -- no interpolation between samples that
    were never measured. P50 of 10 values is the 5th smallest.
    """
    if not data:
        return 0.0
    s = sorted(data)
    idx = max(0, math.ceil(q / 100.0 * len(s)) - 1)
    return s[min(idx, len(s) - 1)]


def one_request(base: str, prompt: str, max_tokens: int, temperature: float) -> dict | None:
    """Stream one completion. Returns timing + token counts, or None on failure."""
    payload = {
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }
    start = time.perf_counter()
    first_at: float | None = None
    chunks = 0
    timings: dict | None = None
    try:
        with httpx.stream("POST", f"{base}/v1/chat/completions", json=payload, timeout=300.0) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line.startswith("data: "):
                    continue
                blob = line[6:].strip()
                if blob == "[DONE]":
                    break
                try:
                    obj = json.loads(blob)
                except ValueError:
                    continue
                if obj.get("timings"):
                    timings = obj["timings"]
                delta = (obj.get("choices") or [{}])[0].get("delta", {}) or {}
                if delta.get("content"):
                    if first_at is None:
                        first_at = time.perf_counter()
                    chunks += 1
    except httpx.HTTPError as exc:
        print(f"      request failed: {exc}")
        return None

    end = time.perf_counter()
    if first_at is None:
        return None

    n_out = int((timings or {}).get("predicted_n") or chunks)
    ttft_ms = (first_at - start) * 1000.0
    decode_ms = (end - first_at) * 1000.0
    return {
        "ttft_ms": ttft_ms,
        "tpot_ms": decode_ms / max(n_out - 1, 1),
        "e2e_ms": (end - start) * 1000.0,
        "n_out": n_out,
        "prompt_n": int((timings or {}).get("prompt_n") or 0),
    }


def measure(label: str, model: str, quant: str) -> dict:
    max_tokens = labkit.env_int("LAB_MAX_TOKENS", 64)
    temperature = labkit.env_float("LAB_TEMPERATURE", 0.7)

    labkit.banner(f"{label}  ({quant})")
    print(f"  model     : {pathlib.Path(model).name}")
    print(f"  threads   : {labkit.threads()}   ngl: {labkit.n_gpu_layers()}   "
          f"ctx: {labkit.n_ctx()}   max_tokens: {max_tokens}")
    print("  starting llama-server ...", flush=True)

    t_load = time.perf_counter()
    with labkit.serve_bg(model, port=BENCH_PORT) as base:
        load_ms = (time.perf_counter() - t_load) * 1000.0
        print(f"  ready in {load_ms:.0f} ms (model load + warm-up of the HTTP stack)")

        # Warm-up: never let the first, cold request into the statistics.
        one_request(base, "Hello.", 8, 0.0)

        rows = []
        for i, prompt in enumerate(PROMPTS, 1):
            r = one_request(base, prompt, max_tokens, temperature)
            if not r:
                continue
            rows.append(r)
            print(f"   [{i:2d}/{len(PROMPTS)}] ttft={r['ttft_ms']:7.1f}ms  "
                  f"tpot={r['tpot_ms']:5.1f}ms  e2e={r['e2e_ms']:8.1f}ms  out={r['n_out']}")

    if not rows:
        labkit.die(f"No successful requests for {quant}.")
    if len(rows) < len(PROMPTS):
        print(f"   !! only {len(rows)}/{len(PROMPTS)} requests succeeded — percentiles are thin.")
        print("      Check the server log before reporting these numbers.")

    ttfts = [r["ttft_ms"] for r in rows]
    tpots = [r["tpot_ms"] for r in rows]
    e2es = [r["e2e_ms"] for r in rows]
    tpot_p50 = pct(tpots, 50)
    return {
        "label": label,
        "quant": quant,
        "model_file": pathlib.Path(model).name,
        "n_requests": len(rows),
        "load_ms": round(load_ms, 1),
        "ttft_p50": round(pct(ttfts, 50), 1),
        "ttft_p95": round(pct(ttfts, 95), 1),
        "tpot_p50": round(tpot_p50, 2),
        "tpot_p95": round(pct(tpots, 95), 2),
        "e2e_p50": round(pct(e2es, 50), 1),
        "e2e_p95": round(pct(e2es, 95), 1),
        "e2e_p99": round(pct(e2es, 99), 1),
        "decode_tok_s": round(1000.0 / max(tpot_p50, 1e-6), 1),
        "size_gb": round(pathlib.Path(model).stat().st_size / 1024**3, 2),
    }


def main() -> int:
    active = labkit.load_active()
    hw = labkit.load_hardware(required=False)

    root = labkit.repo_root()
    primary = str(root / active["primary_model"])
    compare = str(root / active["compare_model"])

    a = measure("primary", primary, active.get("primary_quant", "primary"))
    b = measure("compare", compare, active.get("compare_quant", "compare"))

    rows = [
        [r["quant"], f"{r['size_gb']:.2f}", f"{r['load_ms']:.0f}",
         f"{r['ttft_p50']:.0f} / {r['ttft_p95']:.0f}",
         f"{r['tpot_p50']:.1f} / {r['tpot_p95']:.1f}",
         f"{r['e2e_p50']:.0f} / {r['e2e_p95']:.0f} / {r['e2e_p99']:.0f}",
         f"{r['decode_tok_s']:.1f}"]
        for r in (a, b)
    ]
    table = labkit.md_table(
        ["Quantization", "Size (GB)", "Load (ms)", "TTFT P50/P95 (ms)",
         "TPOT P50/P95 (ms)", "E2E P50/P95/P99 (ms)", "Decode (tok/s)"],
        rows,
    )
    # Ratio of decode rates: >1 means the compare quant is faster, <1 means slower.
    ratio = (b["decode_tok_s"] / a["decode_tok_s"]) if a["decode_tok_s"] else 0.0
    if ratio > 1.02:
        verdict = (f"`{b['quant']}` decodes **{ratio:.2f}x faster** than `{a['quant']}` here, "
                   f"for {a['size_gb'] - b['size_gb']:.2f} GB less on disk.")
    elif ratio < 0.98:
        verdict = (f"`{b['quant']}` decodes **{1 / ratio:.2f}x SLOWER** than `{a['quant']}` here, "
                   f"despite being {a['size_gb'] - b['size_gb']:.2f} GB smaller. That is a real "
                   f"result, not a mistake: fewer bits only buys speed when decode is limited by "
                   f"memory bandwidth. On a machine that is compute-limited instead — few cores, "
                   f"no GPU offload — the extra dequantization work of a heavily-quantized format "
                   f"can cost more than the bytes it saves. Say which case yours is.")
    else:
        verdict = (f"`{b['quant']}` and `{a['quant']}` decode within 2% of each other here, "
                   f"for {a['size_gb'] - b['size_gb']:.2f} GB difference on disk.")

    md = f"""# 01 - Measure: latency baseline

Model `{active['model']}` · host `{labkit.host_tag()}` · llama.cpp `{labkit.LLAMA_CPP_BUILD}`
Settings: `threads={labkit.threads(hw)}` `ngl={labkit.n_gpu_layers(hw)}` `ctx={labkit.n_ctx()}`
`max_tokens={labkit.env_int("LAB_MAX_TOKENS", 64)}` · warm-up discarded
Completed requests: `{a['quant']}` {a['n_requests']}/{len(PROMPTS)} · `{b['quant']}` {b['n_requests']}/{len(PROMPTS)}

{table}

- **TTFT** = prefill. Short prompts keep it small; long-context RAG is where it explodes.
- **TPOT** = per-output-token decode cost, bounded by memory bandwidth. `decode tok/s = 1000 / TPOT_p50`.
- {verdict}

## Your observation (required -- replace this line)

_Is the smaller quantization worth it on your machine? Compare the numbers above,
then judge the answer quality yourself: run `make serve` on each and ask the same
question twice. Size and speed are measurable; usefulness is your call._
"""
    out = labkit.write_report("01-quickstart-results.md", md, {"primary": a, "compare": b})
    print("\n" + md)
    print(f"==> Wrote {out.relative_to(labkit.repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
