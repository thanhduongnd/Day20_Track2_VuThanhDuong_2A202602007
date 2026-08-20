#!/usr/bin/env python3
"""
Bonus challenge C8 — Semantic Caching  (Day 20 §5: "the stack is 3 caches deep").

  request -> [1] semantic cache (meaning-based) -> [2] prefix/KV cache -> [3] full inference

Layer 1 catches *paraphrases* of past prompts (cosine > threshold) and returns
the stored answer with ZERO compute. This builds a tiny semantic cache in front
of a chat endpoint, replays a prompt stream that includes paraphrases, and
reports hit rate + LLM calls saved. It also shows the two failure modes the deck
warns about: a too-low threshold (stale/wrong answers) and per-tenant salting
(cross-user cache leakage via timing — NDSS'25).

  # real mode — needs the chat server (:8080) and an embedding server (:8081):
  make serve &            # chat       on :8080
  make serve-embed &      # embeddings on :8081
  .venv/bin/python bonus/serving-regimes/semantic-cache-demo.py --threshold 0.85

  # logic demo / smoke test — no servers (synthetic embeddings + fake LLM):
  .venv/bin/python bonus/serving-regimes/semantic-cache-demo.py --offline --sweep
"""
from __future__ import annotations

import argparse
import re
import sys
import time

import numpy as np


# Offline-only: a crude bag-of-words stand-in for a real embedding model.
# Drops question/function words and strips a trailing "s" so paraphrases that
# share content words score high. A real embedder (Qwen3-Embedding, BGE-M3) also
# matches lexically-disjoint paraphrases (e.g. "TTFT" ~ "time to first token");
# bag-of-words cannot — that gap is itself worth noticing.
_STOPWORDS = {
    "a", "an", "the", "is", "are", "be", "do", "does", "did", "how", "what",
    "why", "can", "could", "you", "i", "me", "my", "of", "to", "at", "in", "on",
    "and", "or", "tell", "define", "describe", "explain", "mean", "means", "like",
    "it", "use", "uses", "work", "works", "different", "differently", "from",
}


def _tokens(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in _STOPWORDS:
            continue
        if len(w) > 3 and w.endswith("s"):
            w = w[:-1]
        out.append(w)
    return out

# Prompt stream: several prompts plus paraphrases of earlier ones.
STREAM = [
    "What is goodput at SLO?",
    "Explain TTFT and TPOT.",
    "Can you define goodput@SLO?",          # paraphrase of #1
    "What does time to first token mean?",  # paraphrase of #2
    "How does PagedAttention work?",
    "Tell me what goodput@SLO is.",         # paraphrase of #1
    "What is prefix caching?",
    "Describe how PagedAttention works.",   # paraphrase of #5
]

CANNED = {
    "goodput": "Goodput@SLO is requests/sec that satisfy the TTFT+TPOT latency SLO.",
    "ttft": "TTFT is time to first token; TPOT is the steady per-output-token interval.",
    "paged": "PagedAttention stores the KV cache in non-contiguous virtual-memory pages.",
    "prefix": "Prefix caching reuses the KV of a shared prompt prefix across requests.",
}


def _topic(p: str) -> str:
    pl = p.lower()
    if "goodput" in pl:
        return "goodput"
    if "first token" in pl or "ttft" in pl or "tpot" in pl:
        return "ttft"
    if "pagedattention" in pl:
        return "paged"
    if "prefix" in pl:
        return "prefix"
    return "other"


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))


def _vocab(texts: list[str]) -> dict[str, int]:
    v: dict[str, int] = {}
    for t in texts:
        for w in _tokens(t):
            v.setdefault(w, len(v))
    return v


def embed_offline(text: str, vocab: dict[str, int]) -> np.ndarray:
    v = np.zeros(len(vocab))
    for w in _tokens(text):
        if w in vocab:
            v[vocab[w]] += 1.0
    return v


def embed_remote(text: str, base_url: str) -> np.ndarray:
    import httpx

    r = httpx.post(f"{base_url}/embeddings",
                   json={"model": "local", "input": [text]}, timeout=60.0)
    r.raise_for_status()
    arr = np.asarray(r.json()["data"][0]["embedding"], dtype=float)
    return arr.mean(axis=0) if arr.ndim == 2 else arr  # pool per-token (NONE pooling) -> 1 vec


def gen_offline(prompt: str) -> str:
    time.sleep(0.25)  # simulate decode latency of a real miss
    return CANNED.get(_topic(prompt), "(generated answer)")


def gen_remote(prompt: str, base_url: str) -> str:
    import httpx

    r = httpx.post(f"{base_url}/chat/completions",
                   json={"model": "local",
                         "messages": [{"role": "user", "content": prompt}],
                         "max_tokens": 80},
                   timeout=120.0)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


class SemanticCache:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.entries: list[tuple[np.ndarray, str, str]] = []

    def lookup(self, vec: np.ndarray) -> tuple[str | None, float]:
        best, best_sim = None, 0.0
        for e in self.entries:
            s = cosine(vec, e[0])
            if s > best_sim:
                best, best_sim = e, s
        if best is not None and best_sim >= self.threshold:
            return best[2], best_sim
        return None, best_sim

    def put(self, vec: np.ndarray, prompt: str, response: str) -> None:
        self.entries.append((vec, prompt, response))


def run(stream: list[str], threshold: float, offline: bool,
        chat_url: str, embed_url: str) -> tuple[int, int]:
    vocab = _vocab(stream) if offline else None
    cache = SemanticCache(threshold)
    hits, saved_ms = 0, 0.0
    print(f"{'#':>2}  {'result':<6} {'sim':>5}  {'ms':>6}  prompt")
    for i, p in enumerate(stream, 1):
        vec = embed_offline(p, vocab) if offline else embed_remote(p, embed_url)
        cached, sim = cache.lookup(vec)
        t0 = time.perf_counter()
        if cached is not None:
            result, hits = "HIT", hits + 1
            saved_ms += 250.0 if offline else 0.0  # a miss would have cost ~this
        else:
            resp = gen_offline(p) if offline else gen_remote(p, chat_url)
            cache.put(vec, p, resp)
            result = "miss"
        dt = (time.perf_counter() - t0) * 1000
        print(f"{i:>2}  {result:<6} {sim:>5.2f}  {dt:>6.0f}  {p}")
    n = len(stream)
    print(f"\nHit rate: {hits}/{n} = {100 * hits / n:.0f}%   (threshold {threshold})")
    print(f"LLM calls saved: {hits}" + (f"  (~{int(saved_ms)} ms decode skipped, offline sim)" if offline else ""))
    return hits, n


def main() -> int:
    ap = argparse.ArgumentParser(description="Semantic cache in front of a chat endpoint (Day 20 §5).")
    ap.add_argument("--threshold", type=float, default=0.80)
    ap.add_argument("--offline", action="store_true",
                    help="No servers: synthetic embeddings + fake LLM (logic demo / smoke test).")
    import os as _os
    _cp = _os.environ.get("LAB_SERVER_PORT", "8080")
    _ep = _os.environ.get("LAB_EMBED_PORT", "8081")
    ap.add_argument("--chat-url", default=f"http://localhost:{_cp}/v1")
    ap.add_argument("--embed-url", default=f"http://localhost:{_ep}/v1")
    ap.add_argument("--sweep", action="store_true",
                    help="Show hit rate across thresholds (offline only).")
    args = ap.parse_args()

    if args.sweep and args.offline:
        print("==> Threshold sweep (offline) — hit rate vs threshold:")
        vocab = _vocab(STREAM)
        for th in (0.70, 0.80, 0.85, 0.90, 0.95):
            c, h = SemanticCache(th), 0
            for p in STREAM:
                v = embed_offline(p, vocab)
                cached, _ = c.lookup(v)
                if cached is not None:
                    h += 1
                else:
                    c.put(v, p, "x")
            print(f"  threshold {th:.2f}: {h}/{len(STREAM)} hits")
        print("  Lower threshold -> more hits but more risk of returning a WRONG paraphrase's answer.")
        print("  NOTE: offline, bag-of-words similarity is almost always exactly 1.0 or 0.0, so this")
        print("  sweep comes out FLAT. That is an artifact of the stub embedder, not a finding. To see")
        print("  a real threshold curve you need real embeddings: make serve-embed, then drop --offline.\n")

    if not args.offline:
        print(f"==> chat {args.chat_url}  |  embeddings {args.embed_url}")
        print("    (start both: `make serve` on :8080 and `make serve-embed` on :8081)")
        print()
        print("    !! Your embedding server is running a CHAT model in pooling mode, because the")
        print("       lab ships one model. Mean-pooled decoder states are a WEAK embedder: expect")
        print("       every pair to land in a narrow band (~0.5-0.9), real paraphrases to miss,")
        print("       and unrelated prompts to hit. Read the table below as a diagnosis of the")
        print("       embedder, not as a cache hit rate you could quote to anyone.")
        print("       A dedicated embedding model (Qwen3-Embedding, BGE-M3, EmbeddingGemma)")
        print("       separates paraphrases from strangers by a wide margin. That is the point.\n")
    hits, n = run(STREAM, args.threshold, args.offline, args.chat_url, args.embed_url)

    if not args.offline:
        print()
        print("--- Read your table before you write anything down ---")
        print(" * Which rows are TRUE paraphrases? #3 and #6 paraphrase #1; #4 paraphrases #2;")
        print("   #8 paraphrases #5. #7 is a NEW topic and must never hit.")
        print(" * Count your false hits (a hit on #7) and your misses (#3, #4, #6, #8 not hitting).")
        print(" * A threshold that fixes one usually breaks the other. That is the finding.")

    print("\n--- Teaching notes (Day 20 §5: the stack is 3 caches deep) ---")
    print(" * request -> [1] semantic cache (meaning) -> [2] prefix/KV cache -> [3] full inference.")
    print(" * Layer 1 catches PARAPHRASES; a HIT saves 100% of compute (no prefill, no decode).")
    print(" * Realistic hit rate: 30-68% FAQ/support, 10-25% open-ended. '95%' needs heavy repetition.")
    print(" * Risk: too-low threshold returns a stale/wrong answer; SALT the cache per-tenant —")
    print("   shared semantic/KV caches can leak prompts across users via timing (NDSS'25).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
