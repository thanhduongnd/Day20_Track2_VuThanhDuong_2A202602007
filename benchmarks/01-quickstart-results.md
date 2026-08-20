# 01 - Measure: latency baseline

Model `Qwen3.5 0.8B` · host `Linux-x86_64` · llama.cpp `b10488`
Settings: `threads=4` `ngl=0` `ctx=2048`
`max_tokens=64` · warm-up discarded
Completed requests: `Q4_K_M` 10/10 · `UD-Q2_K_XL` 10/10

| Quantization | Size (GB) | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode (tok/s) |
| :----------- | --------: | --------: | ----------------: | ----------------: | -------------------: | -------------: |
| Q4_K_M       |      0.50 |      8475 |         413 / 858 |       41.1 / 58.3 |   2967 / 4533 / 4533 |           24.3 |
| UD-Q2_K_XL   |      0.39 |      7581 |         602 / 725 |       44.1 / 59.0 |   3449 / 4321 / 4321 |           22.7 |

- **TTFT** = prefill. Short prompts keep it small; long-context RAG is where it explodes.
- **TPOT** = per-output-token decode cost, bounded by memory bandwidth. `decode tok/s = 1000 / TPOT_p50`.
- `UD-Q2_K_XL` decodes **1.07x SLOWER** than `Q4_K_M` here, despite being 0.11 GB smaller. That is a real result, not a mistake: fewer bits only buys speed when decode is limited by memory bandwidth. On a machine that is compute-limited instead — few cores, no GPU offload — the extra dequantization work of a heavily-quantized format can cost more than the bytes it saves. Say which case yours is.

## Your observation

Quantization `UD-Q2_K_XL` nhỏ hơn `Q4_K_M` 0.11 GB, giảm kích thước từ 0.50 GB
xuống 0.39 GB, tức tiết kiệm khoảng 22%. Tuy nhiên, trên máy này bản 2-bit không nhanh hơn mà còn chậm hơn: tốc độ decode là 22.7 tok/s so với 24.3 tok/s của Q4, tương đương chậm hơn khoảng 6.6%. TTFT P50 cũng cao hơn (602 ms so với 413 ms) và E2E P50 cao hơn (3449 ms so với 2967 ms), dù thời gian load model ngắn hơn.

Vì vậy, bản 2-bit không đáng dùng nếu ưu tiên tốc độ và chất lượng câu trả lời. Nên chọn `Q4_K_M` vì nó nhanh hơn và có khả năng giữ chất lượng tốt hơn. Bản Q2 chỉ đáng dùng khi việc tiết kiệm khoảng 22% dung lượng hoặc RAM quan trọng hơn tốc độ và khả năng suy giảm chất lượng, chẳng hạn trên máy có RAM hạn chế.

**Qualitative check:** đã hỏi cùng một câu ("Explain in one sentence why increasing
--parallel on a llama.cpp server can improve throughput under load.") trên cả hai
server (`make serve` port 8080 vs `serve.py --compare --port 8090`). `Q4_K_M` trả lời
mạch lạc hơn, có nhắc đúng khái niệm cụ thể (song song hoá tính toán); `UD-Q2_K_XL`
trả lời chung chung, ít nội dung kỹ thuật hơn hẳn dù cùng độ dài. Điều này củng cố kết
luận trên: với model 0.8B vốn đã nhỏ, giảm xuống 2-bit làm mất thêm chất lượng mà
không đổi lại được tốc độ trên máy CPU-only này.
