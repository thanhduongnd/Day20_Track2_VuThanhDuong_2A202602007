"""Locust load test against llama-server's OpenAI-compat endpoint.

80% short prompts (chat-style), 20% long prompts (RAG-style with a fake context).
80/20 is the point: a real endpoint serves a mix, and the long RAG-shaped
requests are the ones that stretch P95 for everybody else sharing the slots.

Run with (the Makefile does this for you, plus --csv):
    locust -f labs/02-serve/load-test.py --headless \
        -u 10 -r 1 -t 1m --host http://localhost:8080
"""
from __future__ import annotations

import os
import random

from locust import HttpUser, between, task

# Output length drives how long each request occupies a decode slot, which drives how
# many requests a 60s run can finish. These defaults are sized so that even a
# CPU-only laptop at ~5 tok/s completes enough requests for the percentiles to mean
# something. Raise them on faster hardware for a heavier test:
#   LAB_LOAD_SHORT_TOKENS=128 LAB_LOAD_LONG_TOKENS=256 make load-50
SHORT_TOKENS = int(os.environ.get("LAB_LOAD_SHORT_TOKENS") or 48)
LONG_TOKENS = int(os.environ.get("LAB_LOAD_LONG_TOKENS") or 96)

SHORT_PROMPTS = [
    "Define TTFT in one sentence.",
    "What's the difference between throughput and goodput?",
    "Why is FlashAttention IO-aware?",
    "When would you use Q4_K_M over Q8_0?",
    "Explain continuous batching to a junior.",
    "What is PagedAttention's main contribution?",
    "Name two reasons to enable prefix caching.",
    "What does --parallel do in a serving engine?",
]

LONG_CONTEXT = """
You are a model-serving expert. Below is documentation about KV cache memory layouts:
PagedAttention (vLLM, 2023) treats the KV cache like virtual-memory pages so that
sequences don't need a contiguous physical block. Before it, ~60-80% of GPU memory
was wasted on internal fragmentation when sequences had variable length. RadixAttention
(SGLang, 2024) extends this idea by storing the KV cache in a radix tree keyed by
token sequence, so a cache hit on a shared prefix lets the engine skip prefill
entirely. vLLM v1 (Jan 2025) ships Automatic Prefix Caching (APC) on by default and
unifies the memory pool used for activations and KV. Disaggregated prefill/decode
(Mooncake, llm-d, NVIDIA Dynamo, 2025) runs the prefill phase on a dedicated GPU
pool and streams the resulting KV across NVLink/InfiniBand to a separate decode pool,
because prefill is compute-bound and decode is memory-bandwidth-bound and contend on
the same GPU when colocated.
""".strip()

LONG_PROMPTS = [
    "Summarize the document above in three bullet points.",
    "Based on the document above, when does disaggregated serving NOT help?",
    "Given the doc above, explain APC to a backend engineer who knows caches.",
]


class LlamaServerUser(HttpUser):
    wait_time = between(0.2, 1.5)

    @task(4)
    def short_prompt(self):
        msg = random.choice(SHORT_PROMPTS)
        self._chat([{"role": "user", "content": msg}], max_tokens=SHORT_TOKENS, name="short")

    @task(1)
    def long_prompt_rag(self):
        msg = random.choice(LONG_PROMPTS)
        messages = [
            {"role": "system", "content": "You answer using the document provided."},
            {"role": "user", "content": LONG_CONTEXT + "\n\nQuestion: " + msg},
        ]
        self._chat(messages, max_tokens=LONG_TOKENS, name="long-rag")

    def _chat(self, messages, max_tokens: int, name: str) -> None:
        self.client.post(
            "/v1/chat/completions",
            json={
                "model": "local",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.5,
            },
            timeout=120,
            name=name,
        )
