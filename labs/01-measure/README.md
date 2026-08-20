# 01 — Measure

Two commands. The first tells you where you stand; the second gives you something to
write about.

```bash
make bench      # TTFT / TPOT / P50-P95-P99, both quantizations
make tune       # thread sweep -> your before/after speedup
```

## `make bench` — the baseline

Starts `llama-server` on a scratch port (8099), streams 10 prompts through
`/v1/chat/completions`, tears the server down, then repeats for the second
quantization. You measure real over-the-wire latency without managing two terminals.

Writes **`benchmarks/01-quickstart-results.md`** — rubric items 3, 4 and 5.

```
TTFT P50/P95   128 / 190 ms     <- prefill: how long until the first token
TPOT P50/P95    34 / 41  ms     <- decode: cost of each token after that
Decode           29 tok/s       <- 1000 / TPOT_p50
E2E P50/P95/P99  1210 / 1450 / 1620 ms
```

- **TTFT** is dominated by prefill compute. Short prompts hide it; long-context RAG
  does not. Bonus `make sweep-ctx` shows exactly how badly.
- **TPOT** is dominated by memory bandwidth, not FLOPs. That is why a smaller
  quantization decodes faster: fewer bytes to move per token.

Token counts come from llama.cpp's own `timings` block, so TPOT is not inferred from
counting SSE chunks.

**The first run is not the fast run.** Model load is excluded from the percentiles and
a warm-up request is discarded, but the OS page cache still matters: the second time
you run this, the weights are already in RAM. Know which number you are reporting.

## `make tune` — the change that mattered most

Sweeps thread counts through `llama-bench` (no server, no compiler, no GPU needed) and
writes **`benchmarks/01-tuning-tg128.md`** with a table, a winner, and a speedup ratio
against the physical-core default.

This is enough for **rubric item 11** on its own. No bonus work required.

The expected shape: throughput climbs to roughly your *physical* core count, then
flattens or drops. Decode is bandwidth-bound, so threads past that point compete for
the same memory channels. **If your curve does something else, that is the more
interesting report** — say what happened and reason about why.

```bash
LAB_N_THREADS=<winner> make bench     # re-measure with your best setting
.venv/bin/python labs/01-measure/tune.py --metric pp512   # tune prefill instead of decode
```

## Knobs

| Variable | Default | What it changes |
|---|---|---|
| `LAB_N_THREADS` | physical cores | Threads. More is not faster. |
| `LAB_N_CTX` | 2048 | Context window per slot → KV cache size |
| `LAB_N_GPU_LAYERS` | 99 if any accelerator, else 0 | Layers on the GPU |
| `LAB_MAX_TOKENS` | 64 | Tokens generated per request |
| `LAB_TEMPERATURE` | 0.7 | Sampling temperature |

## Before you benchmark

Close the browser, the IDE and Slack. They compete for exactly the resource decode is
bound by. A benchmark run next to 40 Chrome tabs measures Chrome.

## Next

```bash
make serve
```
