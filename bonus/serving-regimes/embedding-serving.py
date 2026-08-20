#!/usr/bin/env python3
"""
Bonus exercise — Embedding & Reranker Serving  (Day 20 §5 Serving Regimes 2026).

Embedding serving is a DIFFERENT regime from chat/decode serving:
  * prefill-bound: one forward pass per text, NO KV cache, NO decode loop
  * throughput comes from large *static* batches, not continuous batching
  * it is the retrieval half of every RAG / agent system

This hits an OpenAI-compatible /v1/embeddings endpoint (a llama-server started
with --embedding), embeds a tiny corpus + a query, ranks the corpus by cosine
similarity, and times how throughput scales with batch size (pure prefill).

  # real mode — start a dedicated embedding server first (:8081):
  make serve-embed
  .venv/bin/python bonus/serving-regimes/embedding-serving.py

  # logic demo / smoke test — no server, deterministic bag-of-words vectors:
  .venv/bin/python bonus/serving-regimes/embedding-serving.py --offline
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

CORPUS = [
    "PagedAttention stores the KV cache in non-contiguous virtual-memory pages.",
    "Continuous batching lets requests join and leave the running batch every step.",
    "RadixAttention reuses a shared prompt prefix across requests via a radix tree.",
    "Speculative decoding drafts several tokens and verifies them in one forward pass.",
    "Embedding serving is prefill-bound: one forward pass, no KV cache, no decode loop.",
    "A cross-encoder reranker scores a (query, document) pair jointly.",
    "Tensor parallelism splits each weight matrix across multiple GPUs.",
    "Quantization to FP8 or INT4 shrinks model memory and raises throughput.",
]
QUERY = "Does embedding serving use a KV cache and a decode loop like chat serving?"


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))


def _vocab(texts: list[str]) -> dict[str, int]:
    vocab: dict[str, int] = {}
    for t in texts:
        for w in _tokens(t):
            vocab.setdefault(w, len(vocab))
    return vocab


def embed_offline(texts: list[str], vocab: dict[str, int]) -> list[np.ndarray]:
    out = []
    for t in texts:
        v = np.zeros(len(vocab))
        for w in _tokens(t):
            if w in vocab:
                v[vocab[w]] += 1.0
        out.append(v)
    return out


def embed_remote(texts: list[str], base_url: str) -> list[np.ndarray]:
    import httpx

    r = httpx.post(f"{base_url}/embeddings",
                   json={"model": "local", "input": texts}, timeout=120.0)
    r.raise_for_status()
    out = []
    for d in r.json()["data"]:
        arr = np.asarray(d["embedding"], dtype=float)
        out.append(arr.mean(axis=0) if arr.ndim == 2 else arr)  # pool per-token (NONE pooling) -> 1 vec
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Embedding & reranker serving demo (Day 20 §5).")
    import os as _os
    ap.add_argument("--base-url",
                    default=f"http://localhost:{_os.environ.get('LAB_EMBED_PORT', '8081')}/v1",
                    help="OpenAI-compatible embeddings endpoint (llama-server --embedding).")
    ap.add_argument("--offline", action="store_true",
                    help="No server: deterministic bag-of-words embeddings (logic demo / smoke test).")
    args = ap.parse_args()

    texts = CORPUS + [QUERY]
    if args.offline:
        vecs = embed_offline(texts, _vocab(texts))
        backend = "offline bag-of-words (no server)"
    else:
        try:
            vecs = embed_remote(texts, args.base_url)
        except Exception as e:  # noqa: BLE001 — student-facing, show the cause
            print(f"ERROR talking to {args.base_url}: {e}", file=sys.stderr)
            print("Start an embedding server first:  make serve-embed",
                  file=sys.stderr)
            print("Or run the logic demo offline:     --offline", file=sys.stderr)
            return 1
        backend = f"llama-server /v1/embeddings @ {args.base_url}"

    corpus_vecs, query_vec = vecs[:-1], vecs[-1]
    print(f"==> Embedding backend: {backend}")
    print(f"    dim = {len(query_vec)}   corpus = {len(CORPUS)} docs\n")
    print(f"Query: {QUERY}\n")

    ranked = sorted(range(len(CORPUS)),
                    key=lambda i: cosine(query_vec, corpus_vecs[i]), reverse=True)
    print("Top matches (cosine similarity):")
    for rank, i in enumerate(ranked[:3], 1):
        print(f"  {rank}. {cosine(query_vec, corpus_vecs[i]):.3f}  {CORPUS[i]}")

    if not args.offline:
        print("\n==> Throughput sweep (texts/sec as batch grows — prefill-bound):")
        for bs in (1, 2, 4, 8, 16):
            batch = [CORPUS[i % len(CORPUS)] for i in range(bs)]
            t0 = time.perf_counter()
            embed_remote(batch, args.base_url)
            dt = time.perf_counter() - t0
            print(f"  batch {bs:>2}: {dt * 1000:7.1f} ms  ->  {bs / dt:6.1f} texts/s")

    print("\n--- Teaching notes (Day 20 §5 Serving Regimes) ---")
    print(" * Embedding serving is PREFILL-BOUND: 1 forward pass/text, no KV cache, no decode loop.")
    print(" * Throughput comes from large STATIC batches (token-sorted), not continuous batching.")
    print(" * FP8 gives ~50% more throughput at >99% cosine similarity (Snowflake Arctic: 16x vLLM).")
    print(" * RAG/agent inference is HALF retrieval — this is the other serving discipline.")
    print(" * For real retrieval quality use a dedicated embedding model (Qwen3-Embedding, BGE-M3);")
    print("   reusing a chat GGUF here keeps the demo to zero extra downloads.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
