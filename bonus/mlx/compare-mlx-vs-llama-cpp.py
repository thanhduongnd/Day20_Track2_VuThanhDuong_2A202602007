#!/usr/bin/env python3
"""BONUS B5 (Apple Silicon) - MLX vs llama.cpp Metal, same model, same prompts.

Gemma 4 E2B ships in both formats from Unsloth, so this is a genuine runtime
comparison rather than a model comparison:

    llama.cpp   the GGUF from models/active.json          (Metal)
    MLX         the matching MLX repo for that model      (unified memory)

Works with either lab model (Gemma 4 E2B or Qwen3.5 0.8B).

Both sides stream, so both TTFT numbers are measured the same way: wall-clock to
the first decoded token, client-side.

    pip install mlx mlx-lm
    make mlx-compare
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import platform
import statistics
import sys
import time

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402

if sys.platform != "darwin" or platform.machine() not in ("arm64", "aarch64"):
    print("This bonus needs Apple Silicon macOS.", file=sys.stderr)
    print("Cross-platform alternatives worth the same 4 points: bonus C8 (semantic cache),",
          file=sys.stderr)
    print("C9 (embedding serving), or C6 (Vulkan vs CUDA). See bonus/CHALLENGES.md.",
          file=sys.stderr)
    sys.exit(1)

PROMPTS = [
    "Define TTFT in one sentence.",
    "Why is FlashAttention IO-aware?",
    "Compare 4-bit and 2-bit quantization in three bullets.",
    "What is goodput@SLO and why does it matter?",
    "When would you use disaggregated prefill/decode serving?",
    "How does PagedAttention avoid KV-cache fragmentation?",
    "What does a --parallel slot do in a serving engine?",
    "Explain prefix caching in two sentences.",
    "Why does long context make TTFT worse super-linearly?",
    "Name two reasons unified memory helps on Apple Silicon.",
]
MAX_TOKENS = 64
PORT = 8098


def pctl(xs: list[float], q: float) -> float:
    """Nearest-rank percentile: index = ceil(q/100 * n), 1-based."""
    if not xs:
        return 0.0
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, math.ceil(q / 100.0 * len(s)) - 1))]


def bench_llama_cpp(model: str) -> dict:
    labkit.banner("llama.cpp (Metal) via llama-server")
    ttfts, rates = [], []
    with labkit.serve_bg(model, port=PORT) as base:
        for prompt in ["warm-up"] + PROMPTS:
            payload = {"model": "local", "stream": True, "max_tokens": MAX_TOKENS,
                       "temperature": 0.5,
                       "messages": [{"role": "user", "content": prompt}]}
            t0 = time.perf_counter()
            first, n, timings = None, 0, {}
            with httpx.stream("POST", f"{base}/v1/chat/completions",
                              json=payload, timeout=300.0) as r:
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
                    if ((obj.get("choices") or [{}])[0].get("delta") or {}).get("content"):
                        first = first or time.perf_counter()
                        n += 1
            end = time.perf_counter()
            if prompt == "warm-up" or not first:
                continue
            n_out = int(timings.get("predicted_n") or n)
            ttfts.append((first - t0) * 1000)
            rates.append((n_out - 1) / max(end - first, 1e-6))
            print(f"   ttft={ttfts[-1]:7.1f} ms   decode={rates[-1]:6.1f} tok/s")
    return {"runtime": "llama.cpp (Metal)", "ttft_p50": round(pctl(ttfts, 50), 1),
            "ttft_p95": round(pctl(ttfts, 95), 1),
            "decode_tok_s": round(statistics.median(rates), 1) if rates else 0.0}


def load_mlx(repo_id: str):
    """Load the MLX weights, working around a known Gemma 4 mismatch.

    Gemma 4 E2B shares KV across 20 of its 35 layers (`num_kv_shared_layers: 20`).
    mlx-lm builds only the tensors it needs for the unshared layers, but Unsloth's
    conversion retained the full set -- so a strict load rejects ~140 "extra"
    parameters that the model genuinely does not use.

    Loading non-strictly is correct here, but we do NOT do it silently: the script
    prints a sample generation so you can confirm the output is coherent before you
    report any numbers. Weights loading is exactly the place a silent regression
    hides.
    """
    from mlx_lm import load, utils

    try:
        return load(repo_id)
    except ValueError as exc:
        if "not in model" not in str(exc):
            raise
        from pathlib import Path

        from huggingface_hub import snapshot_download
        from transformers import AutoTokenizer

        n = str(exc).split("Received ", 1)[-1].split(" ", 1)[0]
        print(f"   note: mlx-lm rejected {n} parameters this model does not use.")
        print("         Gemma 4 E2B shares KV across 20 layers; mlx-lm builds only the")
        print("         unshared tensors while the conversion kept all of them.")
        print("         Retrying with a non-strict load, then sanity-checking the output.")
        path = Path(snapshot_download(repo_id))
        model, _ = utils.load_model(path, strict=False)
        return model, AutoTokenizer.from_pretrained(str(path))


def bench_mlx(repo_id: str) -> dict:
    try:
        from mlx_lm import stream_generate
    except ImportError:
        labkit.die("mlx-lm not installed.", "Run: pip install mlx mlx-lm")
    labkit.banner(f"MLX-LM  ({repo_id})")
    print("   loading (first run downloads the MLX weights) ...", flush=True)
    model, tokenizer = load_mlx(repo_id)

    def run(prompt: str) -> tuple[float, float, str] | None:
        text = prompt
        if getattr(tokenizer, "chat_template", None):
            text = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True
            )
        t0 = time.perf_counter()
        first, n, out = None, 0, []
        for resp in stream_generate(model, tokenizer, prompt=text, max_tokens=MAX_TOKENS):
            if getattr(resp, "text", ""):
                first = first or time.perf_counter()
                n += 1
                out.append(resp.text)
        end = time.perf_counter()
        if first is None or n < 2:
            return None
        return (first - t0) * 1000.0, (n - 1) / max(end - first, 1e-6), "".join(out)

    warm = run("Define TTFT in one sentence.")
    if not warm:
        labkit.die("MLX produced no tokens -- check the repo id with --mlx-repo.")
    print("\n   sanity check -- is this coherent English?")
    print(f'   "{warm[2].strip()[:180]}"')
    print("   If that is garbage, the non-strict load dropped something it needed:")
    print("   stop here and use a different B5 option (C6 / C8 / C9) instead.\n")

    ttfts, rates = [], []
    for prompt in PROMPTS:
        r = run(prompt)
        if not r:
            continue
        ttfts.append(r[0])
        rates.append(r[1])
        print(f"   ttft={r[0]:7.1f} ms   decode={r[1]:6.1f} tok/s")
    return {"runtime": "MLX-LM", "ttft_p50": round(pctl(ttfts, 50), 1),
            "ttft_p95": round(pctl(ttfts, 95), 1),
            "decode_tok_s": round(statistics.median(rates), 1) if rates else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser(description="MLX vs llama.cpp Metal (bonus B5).")
    ap.add_argument("--mlx-repo", default=None, help="Override the MLX repo id")
    args = ap.parse_args()

    active = labkit.load_active()
    gguf = str(labkit.repo_root() / active["primary_model"])
    mlx_repo = args.mlx_repo or active.get("mlx_repo") or labkit.mlx_repo()

    # Check the optional dependency BEFORE benchmarking. bench_mlx() dies on a missing
    # mlx-lm, and it runs second — so without this the student sits through the whole
    # llama.cpp half and then loses it to an install message.
    try:
        import mlx_lm  # noqa: F401
    except ImportError:
        labkit.die("mlx-lm not installed.",
                   "Run: .venv/bin/pip install mlx mlx-lm   (Apple Silicon only)")

    a = bench_llama_cpp(gguf)
    b = bench_mlx(mlx_repo)

    ratio = (b["decode_tok_s"] / a["decode_tok_s"]) if a["decode_tok_s"] else 0.0
    # Same 10% band the report text tells the student to apply -- the two quantization
    # schemes are not byte-identical, so a smaller gap is not a runtime finding.
    if ratio > 1.10:
        winner = "MLX"
    elif ratio < 0.90:
        winner = "llama.cpp"
    else:
        winner = "neither -- inside the 10% noise band"

    table = labkit.md_table(
        ["Runtime", "Weights", "TTFT P50 (ms)", "TTFT P95 (ms)", "Decode (tok/s)"],
        [[a["runtime"], f"`{pathlib.Path(gguf).name}`", a["ttft_p50"], a["ttft_p95"],
          a["decode_tok_s"]],
         [b["runtime"], f"`{mlx_repo}`", b["ttft_p50"], b["ttft_p95"], b["decode_tok_s"]]],
    )
    md = f"""# Bonus B5 - MLX vs llama.cpp Metal

Host `{labkit.host_tag()}` · {platform.processor() or "Apple Silicon"} ·
llama.cpp `{labkit.LLAMA_CPP_BUILD}` · {len(PROMPTS)} prompts,
`max_tokens={MAX_TOKENS}`, warm-up discarded on both sides

{table}

MLX decode is **{ratio:.2f}x** llama.cpp Metal here. Faster on decode: **{winner}**.

Both sides run the same model at 4-bit and stream token by token, so the gap is a
runtime difference, not a model difference. The quantization schemes are not
byte-identical, though (Unsloth Dynamic GGUF vs MLX 4-bit), so treat a gap under
~10% as noise rather than a finding.

## Your finding (required -- replace this line)

_Which runtime would you ship on this Mac, and why? Consider more than tok/s:
which one starts faster, which one is easier to deploy, and which one still works
when you have to move off Apple hardware._
"""
    out = labkit.write_report("bonus-mlx-vs-llama-cpp.md", md, {"llama_cpp": a, "mlx": b})
    print("\n" + md)
    print(f"==> Wrote {out.relative_to(labkit.repo_root())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
