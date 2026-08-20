# 02 — Serve

Step up from "measure a model" to "run a serving stack". Same shape as the vLLM and
SGLang setups in the deck — OpenAI-compatible HTTP, continuous batching, Prometheus
metrics — on a model small enough to fit your laptop.

There is **one** server. The prebuilt native binary gives you `/metrics`,
`--parallel` and `--cont-batching` out of the box, so nothing here needs a build.

## The run, in order

```bash
# terminal 1 — leave it running
make serve

# terminal 2
make smoke          # rubric items 6 + 7 in one screenshot
make load-10        # 10 users, 60s  -> benchmarks/locust-10_stats.csv
make load-50        # 50 users, 60s  -> benchmarks/locust-50_stats.csv

# terminal 3, WHILE load-50 is running
make metrics        # samples /metrics for 60s

# after both load runs
make load-report    # -> benchmarks/02-server-results.md
```

`make metrics` must overlap with load, or it records an idle server and the batching
gauges all read ~1. That is the single most common mistake in this track.

## What you get

| Command | Artifact | Rubric |
|---|---|---|
| `make smoke` | screenshot: a completion **and** non-zero `tokens_predicted_total` | 6, 7 |
| `make load-10` / `load-50` | locust summary screenshots + CSVs | 8 |
| `make load-report` | `benchmarks/02-server-results.md` | 10 |
| `make metrics` | `benchmarks/02-server-batching-u50.md` + CSV | 9 |

## Reading the load report

`load-report.py` computes **effective concurrency** with Little's Law — `L = λ × W`,
arrival rate times time in system — and compares it to your `--parallel` slot count:

- **Effective concurrency ≤ slots** → requests found a free slot on arrival. The
  latency you see is compute.
- **Effective concurrency > slots** → requests queued. The extra P95 is *wait* time,
  not compute time.

That gap is the whole goodput-vs-throughput argument from §8. Past saturation you buy
throughput by spending latency, and if your SLO is a P95 target, the requests you
added are no longer being served within it. Peak throughput and goodput@SLO stop being
the same number, and only one of them is what users experience.

## Reading the batching metrics

`llamacpp:n_busy_slots_per_decode` is the average number of slots doing useful work
per decode step:

- near **1** under load → requests are being serialized, not batched
- climbing toward **`--parallel`** → the scheduler is packing concurrent requests into
  shared decode steps. That is continuous batching, and it is why throughput rises
  faster than latency does.
- `requests_deferred` above 0 → more requests arrived than there were slots

## Knobs worth trying

Anything after `--` goes straight to `llama-server`:

```bash
.venv/bin/python labs/02-serve/serve.py -- --parallel 1          # batching off, for contrast
.venv/bin/python labs/02-serve/serve.py -- --parallel 8
.venv/bin/python labs/02-serve/serve.py -- --ctx-size 4096       # watch process RSS grow
.venv/bin/python labs/02-serve/serve.py -- --cache-type-k q8_0 --cache-type-v q8_0   # bonus C2
.venv/bin/python labs/02-serve/serve.py --compare                # serve the 2-bit quantization
```

| Flag | Measure this |
|---|---|
| `--parallel N` | P95 at `-u 50` for N = 1, 2, 4, 8 |
| `--ctx-size` | RAM (RSS) as context grows — that is KV cache |
| `--cache-type-k/v` | RAM saved vs quality lost |

The most instructive experiment in this track: run `make load-50` at `--parallel 1`
and again at `--parallel 4`, and compare both RPS *and* P95. One of them improves a
lot more than the other.

## Endpoints

| Path | Use |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible; works with the `openai` SDK pointed at `http://localhost:8080/v1` |
| `GET /metrics` | Prometheus text |
| `GET /slots` | per-slot state — useful for seeing batching directly |
| `GET /health` | readiness (this is what `serve_bg` polls) |
| `GET /props` | the server's active configuration |

## Next

```bash
make pipeline
```
