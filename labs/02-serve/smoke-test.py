#!/usr/bin/env python3
"""02 - Smoke-test the running server: OpenAI-compat call + /metrics proof.

Produces the evidence for rubric items 6 and 7 in one run. Screenshot this.

    make serve      # terminal 1
    make smoke      # terminal 2
"""
from __future__ import annotations

import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import labkit  # noqa: E402

METRICS_OF_INTEREST = (
    "llamacpp:tokens_predicted_total",
    "llamacpp:prompt_tokens_total",
    "llamacpp:n_decode_total",
    "llamacpp:requests_processing",
    "llamacpp:n_busy_slots_per_decode",
)


def read_metrics(base: str) -> dict[str, float]:
    out: dict[str, float] = {}
    try:
        text = httpx.get(f"{base}/metrics", timeout=5.0).text
    except httpx.HTTPError:
        return out
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) == 2 and parts[0] in METRICS_OF_INTEREST:
            try:
                out[parts[0]] = float(parts[1])
            except ValueError:
                pass
    return out


def main() -> int:
    port = labkit.server_port()
    base = f"http://localhost:{port}"

    labkit.banner(f"Smoke test against {base}")

    before = read_metrics(base)
    if before:
        print(f"  /metrics before : tokens_predicted_total = "
              f"{before.get('llamacpp:tokens_predicted_total', 0):.0f}")

    print(f"\n==> POST {base}/v1/chat/completions")
    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": "You are a model-serving tutor. Be concise."},
            {"role": "user", "content": "Define goodput@SLO in one sentence."},
        ],
        "max_tokens": 80,
        "temperature": 0.3,
    }
    try:
        r = httpx.post(f"{base}/v1/chat/completions", json=payload, timeout=300.0)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        labkit.die(f"{exc}", f"Is llama-server running on :{port}?  Start it with: make serve")
    body = r.json()
    print(f"\n{body['choices'][0]['message']['content'].strip()}\n")

    t = body.get("timings") or {}
    if t:
        print(f"  server timings: prompt {t.get('prompt_n', 0):.0f} tok in "
              f"{t.get('prompt_ms', 0):.0f} ms  ->  {t.get('prompt_per_second', 0):.1f} tok/s prefill")
        print(f"                  decode {t.get('predicted_n', 0):.0f} tok in "
              f"{t.get('predicted_ms', 0):.0f} ms  ->  "
              f"{t.get('predicted_per_second', 0):.1f} tok/s")

    print(f"\n==> GET {base}/metrics   (rubric item 7 -- screenshot this)")
    after = read_metrics(base)
    if not after:
        labkit.die(
            "/metrics returned nothing.",
            "The prebuilt server is started with --metrics by make serve; if you launched",
            "llama-server by hand, add --metrics.",
        )
    for name in METRICS_OF_INTEREST:
        if name in after:
            delta = after[name] - before.get(name, 0.0)
            mark = f"   (+{delta:.0f})" if delta > 0 else ""
            print(f"   {name:42s} {after[name]:12.2f}{mark}")

    predicted = after.get("llamacpp:tokens_predicted_total", 0)
    if predicted <= 0:
        labkit.die("tokens_predicted_total is still 0 -- the request did not decode anything.")
    print(f"\nOK -- served a completion and tokens_predicted_total is {predicted:.0f} (non-zero).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
