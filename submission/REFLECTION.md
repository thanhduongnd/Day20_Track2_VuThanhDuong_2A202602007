# Reflection — Day 20 Lab (Personal Report)

> **Đây là báo cáo cá nhân.** Số liệu của bạn **không** so sánh được với bạn cùng lớp
> — chỉ so **before vs after trên chính máy bạn**. Rubric chấm độ rõ ràng của setup,
> đo lường và **lập luận**, không chấm tốc độ tuyệt đối.
>
> `make verify` sẽ fail nếu còn placeholder chưa điền. Đó là cố ý.

**Họ Tên:** Vũ Thanh Dương
**Cohort:** A20-K3
**Ngày submit:** 2026-08-20

---

## 1. Hardware & runtime  *(rubric 1, 2 — 10 điểm)*

> Từ `make probe`. Paste output hoặc điền tay.

- **OS:** Ubuntu (WSL2 trên Windows), kernel 6.6.87.2-microsoft-standard-WSL2
- **CPU:** Intel Core i5-1135G7 @ 2.40GHz (11th Gen)
- **Cores:** 4 physical / 8 logical
- **CPU extensions:** AVX2, AVX-512
- **RAM:** 7.6 GB
- **Accelerator:** CPU only (không có GPU backend nào được phát hiện — Linux/WSL2 thiếu Vulkan ICD)
- **llama.cpp asset đã tải:** bản prebuilt pin ở build `b10488` (Linux x86_64, CPU)
- **Model đã dùng:** Qwen3.5 0.8B (`LAB_MODEL=qwen35-0.8b`)
- **Quantization:** Q4_K_M (primary) + UD-Q2_K_XL (compare) (từ `models/active.json`)

**Chạy ở đâu:** laptop của tôi (WSL2, RAM 7.6 GB nên chuyển sang model nhỏ
Qwen3.5 0.8B theo hướng dẫn thay vì Gemma 4 E2B mặc định).

**Setup story** (≤ 80 chữ): RAM dưới 8 GB nên đổi `LAB_MODEL=qwen35-0.8b` trước khi
`make setup` như GUIDE khuyến nghị. Không có bước nào fail — `make probe`, `make setup`
chạy suôn sẻ trên WSL2, không phát hiện GPU (bình thường trên Linux/WSL2 thiếu Vulkan
ICD), nên toàn bộ lab chạy CPU-only.

---

## 2. Đo lường  *(rubric 3, 4, 5 — 20 điểm)*

> Paste bảng từ `benchmarks/01-quickstart-results.md` (`make bench` tự sinh).

| Quantization | Size (GB) | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode (tok/s) |
|---|--:|--:|--:|--:|--:|--:|
| Q4_K_M | 0.50 | 8475 | 413 / 858 | 41.1 / 58.3 | 2967 / 4533 / 4533 | 24.3 |
| UD-Q2_K_XL | 0.39 | 7581 | 602 / 725 | 44.1 / 59.0 | 3449 / 4321 / 4321 | 22.7 |

**Quan sát** (≤ 60 chữ): Bản 2-bit nhỏ hơn 22% (0.39 vs 0.50 GB) nhưng **chậm hơn**
6.6% (22.7 vs 24.3 tok/s) và TTFT P50 cao hơn — trên máy CPU-only này việc giảm bit
không thắng vì decode bị giới hạn bởi memory bandwidth, chưa kể chi phí dequant
nặng hơn. **Không đáng dùng** trừ khi RAM là ràng buộc cứng.

Đã thử hỏi cùng một câu trên cả hai (`make serve` vs `serve.py --compare --port 8090`):
`Q4_K_M` trả lời mạch lạc và đúng khái niệm hơn hẳn; `UD-Q2_K_XL` trả lời chung
chung, mất chi tiết kỹ thuật. Chất lượng thua rõ, tốc độ cũng không hơn → 2-bit
không đáng dùng trên máy này.

---

## 3. Serving under load  *(rubric 8, 9, 10 — 20 điểm)*

> Từ `benchmarks/02-server-results.md` (`make load-report`).

| Users | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Eff. concurrency | Failures |
|--:|--:|--:|--:|--:|--:|--:|
| 10 | 0.51 | 15000 | 27000 | 30000 | 8.0 | 0.0% |
| 50 | 0.55 | 34000 | 54000 | 57000 | 17.5 | 0.0% |

- **Offered load tăng 5×, throughput thực tăng:** 1.08×
- **P95 tăng:** 2.00×
- **Effective concurrency ở 50 users:** 17.5 so với `--parallel` = 4 slots

**Peak `llamacpp:n_busy_slots_per_decode`** (từ `make metrics` khi `make load-50` đang
chạy): 3.90 / 4 slots

**Saturation reading** (≤ 80 chữ): Server bão hoà ở/trước 50 users. Bằng chứng: throughput
chỉ tăng 1.08× cho 5× offered load trong khi P95 tăng 2.00×, và busy-slots đã chạm
gần trần 4/4 với `requests_deferred` lên tới 46. Latency thêm là **queue time**, không
phải compute — biết được vì compute per-token (TPOT) không đổi giữa các mức tải, chỉ
số request chờ tăng. Tôi sẽ tăng `--parallel` trước, vì nút thắt là số slot đồng thời,
không phải tốc độ mỗi token.

---

## 4. Integration  *(rubric 12, 13 — 15 điểm)*

> Từ `make pipeline`. Nói thật cái nào real, cái nào stub — stub **không** mất điểm.

| Day | Piece | Real hay stub? |
|---|---|---|
| N16 Cloud/IaC | (không dựng) | stub |
| N17 Data pipeline | `TOY_DOCS` tĩnh | stub |
| N18 Lakehouse | (không có) | stub |
| N19 Vector + features | `retrieve()` keyword overlap | stub |
| N20 Serving | `llama-server` | real |

**Latency split** (mean của 3 query, từ output của `pipeline.py`):

- embed: 0.0 ms
- retrieve: 0.1 ms
- llm: 7245.3 ms
- **stage chiếm nhiều nhất:** llm (100% của total)

**Reflection** (≤ 60 chữ): Bottleneck là stage `llm`, đúng như kỳ vọng vì đây là
stage duy nhất thật — embed/retrieve là stub gần như miễn phí (keyword match). Để
giảm 2×: cắt `max_tokens` sinh ra, và/hoặc dùng prompt caching cho phần context lặp
lại giữa các câu hỏi, vì phần lớn thời gian là decode (memory-bandwidth-bound).

---

## 5. The single change that mattered most  *(rubric 11 — 10 điểm)*

> **Phần quan trọng nhất của report.** Không cần bonus track: `make tune` đã cho bạn
> một before/after thật (`benchmarks/01-tuning-tg128.md`). Đổi quantization,
> `LAB_N_CTX`, hay `--parallel` rồi đo lại cũng được.

**Change:** hạ thread count từ mặc định thử nghiệm `-t 16` (oversubscribe 2× logical
cores) xuống `-t 4` (đúng số physical core)

```
before:  3.6 tok/s   (-t 16)
after:   29.3 tok/s  (-t 4)
speedup: 8.1×
```

**Tại sao nó work** (1–2 đoạn):

Máy này có 4 physical / 8 logical core (Intel i5-1135G7, có hyperthreading). Curve
tăng gần tuyến tính từ 1 → 4 threads (16.2 → 29.3 tok/s), rồi **flat** ở 4 → 8 threads
(29.3 → 29.4 tok/s, +0.3% không đáng kể), sau đó **sập** mạnh ở 16 threads (3.6 tok/s,
chỉ còn 12% đỉnh). Decode của llama.cpp là workload memory-bandwidth-bound — mỗi
token phải đọc lại toàn bộ trọng số qua RAM — nên hai logical thread trên cùng một
physical core (hyperthreading) chia sẻ chung băng thông và cache L1/L2, không mang
lại việc hữu ích thêm; đó là lý do `-t 8` chỉ hoà chứ không vượt `-t 4`.

Cú sập ở `-t 16` mạnh hơn kỳ vọng "oversubscribe nhẹ" trong deck — với 8 logical
core mà yêu cầu 16 thread, hệ điều hành phải liên tục context-switch, làm nguội
cache liên tục (mỗi lần switch có thể đá dữ liệu hot của thread khác ra khỏi
L1/L2), nên phần lớn thời gian CPU bị tốn vào scheduling overhead thay vì decode
thật. Kết luận: với CPU 4C/8T, đặt `-t` đúng bằng physical core count là lựa chọn
tối ưu — vừa đạt tốc độ tối đa, vừa tránh lãng phí luồng.

---

## 6. Bonus  *(optional — tối đa 20 điểm)*

> Bỏ trống nếu không làm. Xem `bonus/README.md`. Đừng làm hết — **một** finding sâu
> ăn điểm hơn năm bảng nông.

**Đã làm:** _<B1 build-compare / B2 sweep nào / B4 challenge nào / B5 lựa chọn nào>_

**Numbers:**

```
before:  <số>
after:   <số>
speedup: <X.Y>×
```

**Điều này nói lên gì mà deck chưa nói:**

_(để trống nếu bạn không làm phần này)_

---

## 7. Điều làm bạn ngạc nhiên nhất  *(optional)*

_(1–2 câu. Không bắt buộc, nhưng grader đọc hết.)_

_(để trống nếu bạn không làm phần này)_

---

## 8. Self-check trước khi push

- [ ] `hardware.json` committed
- [ ] `models/active.json` committed
- [ ] `benchmarks/01-quickstart-results.md` committed (`make bench`)
- [ ] `benchmarks/01-tuning-tg128.md` committed (`make tune`)
- [ ] `benchmarks/02-server-results.md` committed (`make load-report`)
- [ ] `benchmarks/02-server-batching-u50.md` hoặc `-metrics-u50.csv` committed (`make metrics`)
- [ ] `benchmarks/locust-10_stats.csv` + `locust-50_stats.csv` committed (`make load-10` / `load-50`)
- [ ] `benchmarks/03-integration-results.md` committed (`make pipeline`)
- [ ] Mọi section **"required — replace this line"** trong các file `benchmarks/*.md`
      đã được thay bằng nhận xét của bạn
- [ ] 5 screenshots trong `submission/screenshots/`
- [ ] `make verify` → **exit 0**
- [ ] Repo GitHub ở chế độ **public**
- [ ] Đã paste public URL vào VinUni LMS
- [ ] **Không** commit `models/*.gguf` hay `runtime/` (đã có trong `.gitignore`)

**Quan trọng:** repo phải **public** đến khi điểm được công bố. Private → grader không
xem được → 0 điểm.
