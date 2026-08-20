# Day 20 — Model Serving & Inference Optimization (Track 2)

Lab cho **AICB-P2T2 · Ngày 20**.

Bạn dựng một inference stack thật trên laptop của mình, đo **TTFT / TPOT / P50 / P95 /
P99**, đẩy nó tới điểm bão hoà bằng load test, rồi tune một knob và viết report về thay
đổi tạo ra speedup lớn nhất **trên chính máy bạn**.

> ### 👉 Bắt đầu ở đây: **[GUIDE.md](GUIDE.md)**
> Hướng dẫn từng bước, có lệnh cụ thể và checkpoint. Đọc [`rubric.md`](rubric.md) trước
> để biết grader chấm gì.

---

## Lab này chạy trên máy nào cũng được

| | |
|---|---|
| **Model** | Chọn **một** trong hai (cả hai Apache-2.0, không gated): |
| | **Gemma 4 E2B** — [unsloth/gemma-4-E2B-it-GGUF](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF) · ~5.2 GB · cần 8 GB RAM · *mặc định* |
| | **Qwen3.5 0.8B** — [unsloth/Qwen3.5-0.8B-GGUF](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF) · ~0.9 GB · cần 4 GB RAM · nhanh hơn, nhẹ hơn |
| **Runtime** | **llama.cpp prebuilt binary** — tải 11–33 MB (bản Windows CUDA 140–240 MB), **không compile** |
| **Cần** | Python ≥ 3.10 · **8 GB RAM** (hoặc **4 GB** với Qwen3.5 0.8B) · 3–10 GB đĩa |
| **Không cần** | GPU · compiler · Docker · API key · tài khoản trả phí |
| **OS** | Windows · macOS (Intel + Apple Silicon) · Linux |
| **Windows** | Không có `make` → dùng **`.\lab.ps1 <target>`** (tên target giống hệt) |
| **RAM < 8 GB?** | `LAB_MODEL=qwen35-0.8b make setup` — chạy local với model nhỏ |
| **RAM < 4 GB?** | Dùng [`cloud/`](cloud/README.md) — Colab/Kaggle, **điểm không đổi** |

> **Số liệu của bạn không so sánh được với bạn cùng lớp.** Chỉ so **before vs after trên
> chính máy bạn**. Rubric chấm độ rõ ràng của setup + đo lường + **lập luận**, không chấm
> tốc độ tuyệt đối. Một bạn dùng Air M1 8 GB và một bạn dùng RTX 5090 đều có thể đạt
> 100/100. Toàn bộ 100 điểm base **không cần GPU, không cần compiler**.

---

## Luồng làm lab

Làm **theo đúng thứ tự này**. Đừng nhảy vào bonus trước khi base xong.

```
┌─ 1 ─ BASE TRACK ────────────────── 100 điểm · bắt buộc · ~2 giờ ─┐
│                                                                  │
│   make probe                 hardware.json                       │
│   make setup                 runtime + Gemma 4 E2B               │
│   make bench                 TTFT / TPOT / percentiles, 2 quant  │
│   make tune                  thread sweep → before/after của bạn │
│   make serve   + make smoke  OpenAI-compat API + /metrics        │
│   make load-10 / load-50     load test                           │
│   make metrics               continuous batching (chạy CÙNG load)│
│   make load-report           server bão hoà ở đâu                │
│   make pipeline              RAG → llama-server                  │
│   viết submission/REFLECTION.md                                  │
│   make verify                phải exit 0                         │
└──────────────────────────────────────────────────────────────────┘
                                 │
                    base xong, verify exit 0
                                 ▼
┌─ 2 ─ BONUS TRACK ──────────── +20 điểm · optional · ~1-2 giờ ────┐
│                                                                  │
│   B1  make build-llama && make compare-builds                    │
│       compile cho CPU của bạn → so với prebuilt binary           │
│       (máy yếu thắng đậm nhất ở đây)                             │
│   B2  make sweep-quant / sweep-ctx / sweep-batch / sweep-gpu     │
│   B3  ghi before/after vào REFLECTION §6                         │
│   B4  1 challenge trong bonus/CHALLENGES.md (C1–C7)              │
│   B5  make mlx-compare  ·  make semantic-cache  ·  make embed-demo│
│       (4 lựa chọn — mọi nền tảng đều đạt được)                   │
│                                                                  │
│   Chọn 1-2 cái. MỘT insight giải thích rõ > năm bảng số nông.     │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─ 3 ─ SUBMIT ──────────────────────────────────────── ~5 phút ────┐
│   make verify → exit 0  ·  repo PUBLIC  ·  paste URL vào LMS      │
└──────────────────────────────────────────────────────────────────┘
```

Chạy `make` để xem toàn bộ target.

---

## Vì sao lab không dùng vLLM / SGLang

Những engine đó cần CUDA GPU + 16 GB VRAM trở lên. Đẹp trên slide, không chạy được trên
một lớp 30 laptop hỗn hợp. llama.cpp cho bạn **cùng teaching surface** — GGUF
quantization, paged KV cache, continuous batching, OpenAI-compat API, Prometheus
`/metrics` — trên bất cứ phần cứng nào bạn đang có.

**Và vì sao prebuilt binary, không phải `llama-cpp-python`:** Gemma 4 dùng architecture
`gemma4` (4/2026). Wheel `llama-cpp-python` trên PyPI vendor một bản llama.cpp cũ hơn và
sẽ báo `unknown model architecture: 'gemma4'`. Prebuilt release binary không có vấn đề
đó, tải nhanh hơn, **và** cho bạn `/metrics` + `--parallel` + `--cont-batching` ngay từ
đầu — những thứ bản Python không có.
