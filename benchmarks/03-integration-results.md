# 03 - Integrate: RAG pipeline run

Host `Linux-x86_64` · llama.cpp `b10488` ·
retrieval backend: **keyword overlap** · 3 queries

| Query | Contexts retrieved | embed (ms) | retrieve (ms) | llm (ms) | total (ms) |
|:--|--:|--:|--:|--:|--:|
| Why is goodput more useful than raw throughp... | goodput, paged, radix | 0.0 | 0.1 | 10804.3 | 10804.4 |
| What problem does PagedAttention actually so... | paged, radix, disagg | 0.0 | 0.1 | 3920.4 | 3920.5 |
| When does splitting prefill and decode help?... | disagg, radix, batching | 0.0 | 0.1 | 7011.1 | 7011.2 |

Mean per stage (ms): embed **0.0** · retrieve **0.1** ·
llm **7245.3** · total **7245.4**
Dominant stage: **llm** (100% of total)

## Answers returned

**Why is goodput more useful than raw throughput?**

> Based on the context provided, **goodput** is more useful than raw throughput because it accounts for the overhead and constraints inherent in the system's operation.

Here is the breakdown based on the text:

1.  **Goodput excludes saturated throughput**: The text states that "Throughput at saturation ignores SLOs" (Service Level Objectives). This means raw throughput measures how fast data moves

**What problem does PagedAttention actually solve?**

> PagedAttention solves the problem of **internal fragmentation** in GPU memory.

While the context mentions that it stores KV cache in non-contiguous pages, the primary benefit described is removing the internal fragmentation that typically wastes most GPU memory.

**When does splitting prefill and decode help?**

> Splitting prefill and decode helps when **prefill is compute-bound and decode is memory-bound**, allowing the system to prioritize compute-intensive operations (prefill) and memory-bound operations (decode) to improve overall throughput and efficiency.

This is specifically enabled by **RadixAttention**, which caches KV by token prefix in a trie. When a shared prefix is used, the engine can skip t


## Which N16-N19 pieces are real

- **N16 Cloud/IaC:** stub — không có hạ tầng cloud/IaC nào được dựng cho lab này,
  pipeline chạy hoàn toàn local.
- **N17 Data pipeline:** stub — không có data pipeline thật nạp dữ liệu; `TOY_DOCS`
  trong `pipeline.py` là danh sách tài liệu tĩnh viết sẵn.
- **N18 Lakehouse:** stub — không có lakehouse/storage layer nào được kết nối.
- **N19 Vector + features:** stub — `retrieve()` trong `pipeline.py` (đúng chỗ được
  đánh dấu `STUB 2`) dùng **keyword overlap** thay vì embedding + vector search thật;
  không có embedding server nào chạy (`embeddings: none` trong log).
- **N20 Serving:** **real** — `llama-server` thật đang chạy, phục vụ cả 3 query qua
  HTTP, có timing thật từ server (prefill/decode tok/s).

Stage chiếm nhiều nhất là **llm (100% of total)** — đúng như kỳ vọng, vì embed
(0.0 ms) và retrieve (0.1 ms) đều là stub siêu rẻ (không có mạng, không có model
embedding, chỉ so khớp từ khoá trên vài chục ký tự), trong khi llm phải chạy full
prefill + decode qua một model 0.8B trên CPU (trung bình 7245 ms/query). Nếu N19
là vector search thật với embedding server, tôi kỳ vọng embed/retrieve sẽ chiếm một
phần đáng kể hơn — con số 100% ở đây phần lớn phản ánh việc retrieval đang là stub
rẻ tiền, không phải retrieval thật sự nhanh.

Nếu phải giảm latency của pipeline này 2x, tôi sẽ tấn công **stage llm**, vì nó
chiếm gần như toàn bộ thời gian. Cách cụ thể: giảm `max_tokens` sinh ra (câu trả lời
hiện khá dài), dùng quantization nhanh hơn nếu memory-bandwidth cho phép (từ
`01-quickstart-results.md`, `Q4_K_M` đã nhanh hơn `UD-Q2_K_XL` trên máy này), hoặc
bật prompt caching cho phần context lặp lại giữa các câu hỏi — vì phần lớn latency
là decode (memory-bandwidth-bound), không phải prefill, nên giảm số token cần sinh
ra có tác động trực tiếp nhất.
