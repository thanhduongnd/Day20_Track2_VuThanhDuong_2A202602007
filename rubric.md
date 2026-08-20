# Rubric — Day 20 Lab (100 điểm base + 20 bonus)

Track-2 Daily Lab, trọng số **30%**.

> **Đây là báo cáo cá nhân.** Mỗi bạn chạy trên máy mình. Số liệu của bạn **không** so
> sánh được với bạn cùng lớp — chỉ so **before vs after trên chính máy bạn**. Rubric chấm
> **độ rõ ràng của setup + đo lường + lập luận**, không chấm tốc độ tuyệt đối.
> Air M1 8 GB và RTX 5090 đều có thể đạt 100/100.
>
> **Toàn bộ 100 điểm base không cần GPU, không cần compiler, không cần Docker.**

Grader chấm **file thật trong repo của bạn**, không chấm những gì bạn nói bạn đã làm.

Cách làm từng bước: **[GUIDE.md](GUIDE.md)**

---

## Base track — 100 điểm

### Phần A · Setup (10 điểm)

| # | Được điểm khi | Lệnh sinh ra bằng chứng | Điểm |
|--:|---|---|--:|
| 1 | `hardware.json` có trong repo. Nếu bạn chạy trên Colab/Kaggle thì khai báo ở REFLECTION §1 | `make probe` | 5 |
| 2 | `models/active.json` có trong repo và hợp lệ | `make setup` | 5 |

### Phần B · Đo lường (20 điểm)

| # | Được điểm khi | Lệnh | Điểm |
|--:|---|---|--:|
| 3 | Có bảng latency cho **cả hai** quantization, đủ percentile | `make bench` | 10 |
| 4 | **TTFT và TPOT báo riêng**, không gộp thành end-to-end | `make bench` | 5 |
| 5 | Có nhận xét của bạn về 2-bit vs 4-bit — nhanh hơn bao nhiêu, **và có đáng không** | bạn viết vào `benchmarks/01-quickstart-results.md` | 5 |

### Phần C · Serving (25 điểm)

| # | Được điểm khi | Lệnh | Điểm |
|--:|---|---|--:|
| 6 | `llama-server` phục vụ được `/v1/chat/completions` | `make serve` + `make smoke` | 10 |
| 7 | `/metrics` có `llamacpp:tokens_predicted_total` **khác 0** sau request | `make smoke` (in ra sẵn) | 5 |
| 8 | Load test ở **cả** 10 và 50 users, 60s mỗi lần | `make load-10` · `make load-50` | 5 |
| 9 | **Continuous batching quan sát được** — peak `n_busy_slots_per_decode` dưới load | `make metrics` **khi** `make load-50` đang chạy | 5 |

### Phần D · Phân tích (20 điểm)

| # | Được điểm khi | Ở đâu | Điểm |
|--:|---|---|--:|
| 10 | **Saturation reading** — server bão hoà ở đâu, bằng chứng nào. RPS có plateau? P95 phồng lên bao nhiêu? Effective concurrency so với số slot? | `make load-report` → bạn viết vào `benchmarks/02-server-results.md` | 10 |
| 11 | **"Thay đổi quan trọng nhất"** — before/after thật + giải thích **cơ chế** | REFLECTION §5 | 10 |

### Phần E · Integration (15 điểm)

| # | Được điểm khi | Ở đâu | Điểm |
|--:|---|---|--:|
| 12 | `pipeline.py` chạy hết 3 query và in ra context đã retrieve | `make pipeline` | 10 |
| 13 | Khai báo **cái nào real / cái nào stub** trong N16–N19, **và** latency chia theo stage (embed / retrieve / llm) | REFLECTION §4 | 5 |

### Phần F · Submission (10 điểm)

| # | Được điểm khi | Ở đâu | Điểm |
|--:|---|---|--:|
| 14 | REFLECTION.md điền đầy đủ · `make verify` **exit 0** · 5 screenshots | `make verify` | 10 |

**Tổng base: 100 điểm**

---

## Điểm 11 — phần nặng nhất, và cách lấy nó mà **không** cần bonus

`make tune` sweep thread count bằng `llama-bench` — **không compiler, không GPU** — rồi
ghi ra `benchmarks/01-tuning-tg128.md` kèm before/after và tỉ lệ speedup. File đó là đủ
cho điểm 11.

Đổi quantization, `LAB_N_CTX`, hoặc `--parallel` rồi đo lại cũng được.

**Cái được chấm là phần giải thích, không phải độ lớn con số.** Một speedup 1.06× được
giải thích đúng cơ chế ăn điểm cao hơn 3× nhưng chỉ ghi "nó nhanh hơn".

Bám vào cơ chế cụ thể: memory bandwidth? vector width? cache residency? queueing?
**Nếu kết quả khác kỳ vọng từ deck → nói rõ và giải thích.** Đó là chỗ ăn điểm, không
phải chỗ mất điểm.

---

## Bonus track — 20 điểm (optional)

Mọi tiêu chí đều đạt được trên **bất kỳ** nền tảng. B5 có 4 lựa chọn nên Apple Silicon
là *một* option, không phải điều kiện.

| # | Được điểm khi | Lệnh | Điểm |
|--:|---|---|--:|
| B1 | Compile llama.cpp cho CPU của bạn và **so với prebuilt binary** | `make build-llama && make compare-builds` | 4 |
| B2 | Chạy ít nhất 1 sweep | `make sweep-quant` / `sweep-ctx` / `sweep-batch` / `sweep-gpu` | 4 |
| B3 | Speedup **của bonus track** có before/after rõ ràng | REFLECTION §6 (từ B1 hoặc B2, **không** phải kết quả `make tune` của base) | 4 |
| B4 | Làm ít nhất 1 challenge C1–C7 hoặc C10 | `bonus/CHALLENGES.md` | 4 |
| B5 | Một so sánh runtime/regime — **chọn 1**: MLX (Mac) · C8 semantic cache · C9 embedding serving · C6 Vulkan vs CUDA | `make mlx-compare` · `make semantic-cache` · `make embed-demo` | 4 |

**Tổng bonus: 20 điểm**

Bonus **không** làm giảm điểm base. Bỏ hẳn bonus vẫn ổn. Submission bonus **tốt** được
instructor viết review riêng, tập trung vào chất lượng lập luận.

**Đừng làm hết.** *Một* finding giải thích sâu > năm bảng số nông.

---

## 5 screenshots bắt buộc

Tất cả đều từ base track — **không cái nào cần bonus, GPU, hay compiler.**
Chi tiết + tips: [`submission/screenshots/README.md`](submission/screenshots/README.md)

> Tên file dưới đây là **gợi ý** (giữ số thứ tự để sắp đúng thứ tự chạy); grader map
> chúng qua REFLECTION của bạn. `make verify` đếm đủ 5 ảnh **đã commit**, không ép tên.

| # | File | Từ lệnh |
|--:|---|---|
| 1 | `01-hardware-probe.png` | `make probe` |
| 2 | `02-bench.png` | `make bench` (bảng kết quả) |
| 3 | `03-serve-and-smoke.png` | `make serve` + `make smoke` (điểm 6 **và** 7 trong 1 ảnh) |
| 4 | `04-locust-10.png` | `make load-10` |
| 5 | `05-locust-50.png` | `make load-50` |

---

## Những cách mất điểm hay gặp

| Mất điểm vì | Tránh bằng cách |
|---|---|
| Repo để **private** → grader không xem được | Set **public** cho tới khi có điểm. Private = **0 điểm** |
| `make metrics` chạy khi server rảnh → `busy_slots ≈ 1`, không có bằng chứng batching | Chạy `make metrics` **chồng thời gian** với `make load-50` (điểm 9) |
| Còn sót section **"required — replace this line"** trong `benchmarks/*.md` | `make verify` sẽ fail. Đọc và điền hết |
| REFLECTION còn placeholder `<Họ Tên>`, `_Answer here._` | `make verify` sẽ fail |
| §5 chỉ ghi số, không giải thích | Nói rõ cơ chế. Đây là 10 điểm |
| Số trong REFLECTION không khớp `benchmarks/*.md` | Đọc lại `benchmarks/*.md` rồi copy đúng số trước khi push |
| Commit `models/*.gguf` (5 GB) | Đã có trong `.gitignore` — đừng `git add -f` |
| Không khai báo đã dùng Colab/Kaggle | Ghi 1 dòng ở REFLECTION §1. Khai báo thì **không mất điểm**; không khai báo thì mất |
| Nói pipeline là "real" khi đang stub | Stub **không mất điểm**. Nói dối mới mất (điểm 13) |

---

## Cách submit

**KHÔNG cần PR — chỉ submit GitHub URL công khai vào VinUni LMS.**

1. Fork/copy repo này lên GitHub account của bạn, set **public**
2. Hoàn thành base track (`make verify` exit 0)
3. (Optional) làm bonus
4. Add 5 screenshots vào `submission/screenshots/`
5. Điền `submission/REFLECTION.md`
6. `make verify` → **exit 0**
7. Push, paste public URL vào ô submission Day 20 trên LMS

---

## Grader chạy repo của bạn như thế nào

```bash
git clone https://github.com/<you>/<your-repo>
cd <your-repo>
cat hardware.json models/active.json          # điểm 1, 2
cat benchmarks/01-quickstart-results.md       # điểm 3, 4, 5
cat benchmarks/02-server-results.md           # điểm 10
cat benchmarks/02-server-batching*.md         # điểm 9
ls submission/screenshots/                    # điểm 6, 7, 8
cat submission/REFLECTION.md                  # điểm 11, 12, 13
make verify                                   # điểm 14 — exit 0?
ls benchmarks/bonus-*.md                      # bonus
```

`make verify` chỉ kiểm tra **file đã commit**. Model weights và runtime binary nằm trong
`.gitignore` có chủ đích, nên việc grader không có chúng **không bao giờ** là lỗi.

---

## Late policy / regrade

Theo policy chuẩn của Track-2 — xem `INDEX-Track2.md` trong repo course material.
