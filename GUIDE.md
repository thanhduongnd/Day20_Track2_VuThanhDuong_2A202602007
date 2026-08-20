# GUIDE — Làm lab Day 20 từ đầu đến cuối

Làm lần lượt theo hướng dẫn này. Mỗi bước cho biết **lệnh cần chạy**, **kết quả bạn sẽ
thấy** và **file được sinh ra**. Các file đó là bằng chứng để chấm điểm.

**Tổng thời gian:** ~2.5 giờ cho base track · +1–2 giờ nếu làm bonus.

> ### 🪟 Windows: đọc phần này trước
> Windows không có `make`. Khi hướng dẫn ghi `make <target>`, hãy dùng
> **`.\lab.ps1 <target>`** với cùng tên target.
>
> ```powershell
> powershell -ExecutionPolicy Bypass -File labs/00-setup/bootstrap.ps1   # chỉ chạy 1 lần
> .\lab.ps1                 # xem toàn bộ target
> .\lab.ps1 bench           # tương đương make bench
> ```

> ### 🐍 Về các lệnh `python` trong tài liệu
> Lab **không** dùng `python` toàn cục — mọi thứ chạy trong virtualenv mà `make setup`
> tạo ra. Vì vậy tài liệu luôn ghi đường dẫn đầy đủ:
>
> | OS | Dùng |
> |---|---|
> | macOS / Linux | `.venv/bin/python labs/...` |
> | Windows | `.venv\Scripts\python labs\...` |
>
> Trên macOS/Linux, gõ `python` trần thường báo `command not found` (chỉ có `python3`),
> và kể cả `python3` cũng thiếu package của lab. Luôn dùng `.venv/bin/python`.

```
PHASE 0  Setup                 ~20 phút
PHASE 1  Base track (100 điểm)  ~2 giờ      ← bắt buộc
PHASE 2  Bonus track (20 điểm)  ~1-2 giờ    ← optional, chỉ làm SAU khi xong base
PHASE 3  Submit                 ~5 phút
```

> **Quy tắc quan trọng:** mỗi file `benchmarks/*.md` do lab sinh ra đều có section
> **"required -- replace this line"**. Bạn **phải** thay section đó bằng nhận xét của
> mình. Nếu còn sót, `make verify` sẽ fail. Số liệu chỉ là đầu vào; phần nhận xét mới là
> nội dung được chấm.

---

# PHASE 0 — Setup

## Bước 0.1 — Kiểm tra máy

```bash
make probe
```

Bạn sẽ thấy thông tin về CPU, số core, RAM, accelerator và model dùng trong lab.

**Chọn cách chạy ngay ở bước này:**

| RAM | Cách làm |
|---|---|
| **≥ 8 GB** | Tiếp tục bước 0.2 và 0.3 trên laptop |
| **4–8 GB** | Vẫn chạy local, chỉ đổi model: `LAB_MODEL=qwen35-0.8b make setup` (xem bước 0.2). **Không mất điểm.** |
| **< 4 GB** | Mở [`cloud/README.md`](cloud/README.md) và làm trên Colab/Kaggle. **Không mất điểm.** |

→ Sinh ra: **`hardware.json`** *(rubric 1)*

→ **Chụp screenshot ngay:** `submission/screenshots/01-hardware-probe.png`

## Bước 0.2 — Chọn model

Lab có **hai** option. Cả hai Apache-2.0, **không gated** (không token, không accept license).
Chọn một, làm hết lab với nó.

| | **Gemma 4 E2B** *(mặc định)* | **Qwen3.5 0.8B** *(nhỏ, nhanh)* |
|---|---|---|
| Repo | [unsloth/gemma-4-E2B-it-GGUF](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF) | [unsloth/Qwen3.5-0.8B-GGUF](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF) |
| Tải về | ~5.2 GB | **~0.9 GB** |
| RAM tối thiểu | 8 GB | **4 GB** |
| Model load | ~6 s | **~3 s** |
| Decode (M1, Metal) | ~27 tok/s | **~42 tok/s** |
| Chất lượng câu trả lời | tốt hơn | thấp hơn (0.8B là 0.8B) |
| Bonus C1 (MTP spec-decode) | có MTP head | không có |

**Chọn thế nào:**

- **RAM ≥ 8 GB, muốn câu trả lời tử tế** → Gemma 4 E2B. Không cần làm gì, đây là mặc định.
- **RAM 4–8 GB, hoặc muốn chạy nhanh gấp 5 lần** → Qwen3.5 0.8B:

  ```bash
  export LAB_MODEL=qwen35-0.8b      # macOS / Linux
  $env:LAB_MODEL = 'qwen35-0.8b'    # Windows PowerShell
  ```

  Set **trước** khi chạy `make setup`. Sau đó `models/active.json` ghi lại lựa chọn, nên
  các bước sau tự dùng đúng model — bạn không cần export lại mỗi lần.

**Rubric không quan tâm bạn chọn model nào.** Cả hai đều cho đủ TTFT/TPOT/percentile,
load test, batching và tuning story. Model nhỏ thậm chí làm phần load test dễ đọc hơn vì
mỗi request xong nhanh hơn nên bạn thu được nhiều mẫu hơn trong 60 s.

### File sẽ được tải

| Vai trò | Gemma 4 E2B | Qwen3.5 0.8B |
|---|---|---|
| primary | `gemma-4-E2B-it-UD-Q4_K_XL.gguf` (2.97 GB) [tải](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-UD-Q4_K_XL.gguf) | `Qwen3.5-0.8B-Q4_K_M.gguf` (0.50 GB) [tải](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/resolve/main/Qwen3.5-0.8B-Q4_K_M.gguf) |
| compare | `gemma-4-E2B-it-UD-Q2_K_XL.gguf` (2.24 GB) [tải](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-UD-Q2_K_XL.gguf) | `Qwen3.5-0.8B-UD-Q2_K_XL.gguf` (0.39 GB) [tải](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/resolve/main/Qwen3.5-0.8B-UD-Q2_K_XL.gguf) |
| bonus C1 | `mtp-gemma-4-E2B-it.gguf` (0.09 GB) [tải](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/mtp-gemma-4-E2B-it.gguf) | — |

**Bước 0.3 (`make setup`) tự tải hai file đầu.** Bảng trên để bạn biết mình đang tải gì, và
để dùng khi mạng trường chặn Hugging Face. Nếu tải tự động fail, script in ra đúng lệnh
`curl` cần chạy — chi tiết trong
[`labs/00-setup/MANUAL-DOWNLOAD.md`](labs/00-setup/MANUAL-DOWNLOAD.md).

---

## Bước 0.3 — Cài đặt

```bash
make setup
```

Bước này mất khoảng 5–15 phút và thực hiện ba việc:

- Tạo `.venv` và cài 4 package Python.
- Tải **llama.cpp prebuilt binary** (10–35 MB, **không compile**).
- Tải **Gemma 4 E2B** với 2 quantization (~5.2 GB).

Trên Windows, bạn có thể chạy target tương ứng:

```powershell
.\lab.ps1 setup
```

Hoặc chạy bootstrap trực tiếp:

```powershell
pwsh -ExecutionPolicy Bypass -File labs/00-setup/bootstrap.ps1
```

→ Sinh ra: **`models/active.json`** *(rubric 2)*, `runtime/`, `models/*.gguf`

Nếu tải model fail do mạng trường chặn Hugging Face, xem
[`labs/00-setup/MANUAL-DOWNLOAD.md`](labs/00-setup/MANUAL-DOWNLOAD.md).

---

# PHASE 1 — Base track (100 điểm)

## Bước 1.1 — Đo baseline: TTFT / TPOT / percentiles

> 📖 Đọc [`labs/01-measure/README.md`](labs/01-measure/README.md) trước: vì sao TPOT bị
> chặn bởi **memory bandwidth** chứ không phải FLOPs, và vì sao chạy benchmark cạnh 40
> tab Chrome là đang đo Chrome. REFLECTION §2 và §5 chấm đúng phần lập luận này.

```bash
make bench
```

Script tự bật `llama-server`, gửi 10 prompt qua HTTP streaming, tắt server, rồi lặp lại
với quantization thứ hai. Bước này mất vài phút.

Bạn sẽ thấy bảng tương tự (ví dụ: Gemma 4 E2B trên M1):

```
| Quantization | Size (GB) | TTFT P50/P95 | TPOT P50/P95 | Decode (tok/s) |
| UD-Q4_K_XL   | 2.97      | 194 / 203    | 37.0 / 40.7  | 27.0           |
| UD-Q2_K_XL   | 2.24      | 202 / 479    | 33.9 / 34.9  | 29.5           |
```

Với Qwen3.5 0.8B trên cùng máy, con số nhanh hơn rõ rệt (~42 và ~50 tok/s). **Đừng so số
của bạn với hai bảng này** — chúng chỉ để bạn biết output trông ra sao.

→ Sinh ra: **`benchmarks/01-quickstart-results.md`** *(rubric 3, 4, 5)*

→ **Chụp screenshot:** `02-bench.png`

**Bạn cần làm:** mở file trên và thay section *"Your observation"*. Nêu rõ 2-bit nhanh
hơn bao nhiêu, nhỏ hơn bao nhiêu và **có đáng dùng không**.

Để đánh giá phần "có đáng dùng không", hãy thử chất lượng của cả hai quantization:

```bash
make serve                                      # terminal 1: bản 4-bit
.venv/bin/python labs/02-serve/serve.py --compare         # hoặc bản 2-bit
```

Đặt cùng một câu hỏi cho cả hai, đọc kết quả rồi đưa ra kết luận.

> ⚠️ Cả hai server mặc định dùng port **8080**. Bạn **phải tắt** server thứ nhất bằng
> Ctrl-C trước khi bật bản `--compare`. Cách khác là dùng port riêng:
> `.venv/bin/python labs/02-serve/serve.py --compare --port 8090`.

## Bước 1.2 — Tune thread count cho máy của bạn

```bash
make tune
```

Kết quả này là nguồn cho **REFLECTION §5**: một before/after thật, không cần compiler
hay GPU. Bước này mất vài phút.

```
| threads (-t) | tg128 (tok/s) | vs best |
| 1            | 27.7          | 96%     |
| 4            | 28.9          | 100%    |   ← best
| 8            | 27.4          | 95%     |
| 16           | 24.2          | 84%     |   ← oversubscribe, chậm hơn
```

→ Sinh ra: **`benchmarks/01-tuning-tg128.md`** *(nguồn cho rubric 11)*

→ Screenshot optional: `06-tune.png`

**Bạn cần làm:** xác định **knee** và giải thích nguyên nhân. Nếu curve không peak ở
physical core count như kỳ vọng, hãy nói rõ. Đây là dữ liệu đáng phân tích, không phải
lỗi cần che đi.

## Bước 1.3 — Dựng server và chứng minh server hoạt động

> 📖 Đọc [`labs/02-serve/README.md`](labs/02-serve/README.md) trước: continuous batching,
> cách đọc queue time vs compute time bằng Little's Law, và thí nghiệm đáng giá nhất của
> lab (`--parallel 1` so với `--parallel 4`). REFLECTION §3 chấm phần này.

Bạn cần **2 terminal**.

**Terminal 1** — giữ server chạy:

```bash
make serve
```

**Terminal 2:**

```bash
make smoke
```

`make smoke` chứng minh hai việc trong một lần chạy: server trả về một completion thật,
và `/metrics` có `llamacpp:tokens_predicted_total` khác 0.

→ *(rubric 6, 7)*

→ **Chụp screenshot:** `03-serve-and-smoke.png`. Ảnh phải có **cả** server đang listen
và output của `make smoke`. Bạn có thể chia đôi terminal hoặc chụp hai file `03a-` /
`03b-`.

## Bước 1.4 — Load test

Giữ server chạy ở terminal 1. Tại terminal 2:

```bash
make load-10       # 10 users, 60s
```

→ **Chụp screenshot:** `04-locust-10.png`. Ảnh phải thấy dòng có
`# reqs · Median · 95%ile · 99%ile`.

Tiếp theo là 50 users. Bước này cần **3 terminal**:

```bash
# terminal 2:
make load-50

# terminal 3, CHẠY NGAY KHI load-50 đang chạy:
make metrics
```

> ⚠️ **Lỗi phổ biến nhất của lab:** chạy `make metrics` khi server đang rảnh. Khi đó,
> `n_busy_slots_per_decode` sẽ ≈ 1 và không chứng minh được continuous batching.
> `make metrics` **phải chạy chồng thời gian với `make load-50`**.

→ **Chụp screenshot:** `05-locust-50.png`

→ Sinh ra: **`benchmarks/02-server-batching-u50.md`** + `.csv` *(rubric 9)*

Bạn sẽ thấy một dòng tương tự:
`Peak n_busy_slots_per_decode = 3.79 of 4 slots`. Đây là bằng chứng continuous batching
đang hoạt động.

## Bước 1.5 — Xác định điểm saturation của server

```bash
make load-report
```

Script đọc hai load test phía trên. Nó dùng Little's Law
(`RPS × average latency`) để tính **effective concurrency**, rồi so với số slot của
`--parallel`.

→ Sinh ra: **`benchmarks/02-server-results.md`** *(rubric 10)*

**Bạn cần làm:** trả lời server saturation ở đâu và bằng chứng là gì. Nếu throughput
tăng ít nhưng P95 tăng mạnh, phần latency tăng thêm là **queue time**, không phải
compute. Đây là lập luận goodput@SLO trong deck §8.

## Bước 1.6 — Chạy RAG pipeline

> 📖 Đọc [`labs/03-integrate/README.md`](labs/03-integrate/README.md) trước: vì sao
> prefill là phần RAG thổi phồng, và prompt caching thay đổi số đo thế nào.

Giữ server chạy. Tại terminal 2:

```bash
make pipeline
```

Bạn sẽ thấy 3 query, context được retrieve và latency theo từng stage:

```
timings : {'embed': 0.0, 'retrieve': 0.3, 'llm': 1875.2, 'total': 1875.5}
Dominant stage: llm (100% of total)
```

→ Sinh ra: **`benchmarks/03-integration-results.md`** *(rubric 12, 13)* — file này có một
section **"required -- replace this line"** bạn phải thay. Screenshot optional: `08-pipeline.png`

**Bạn cần làm:** trong REFLECTION §4, khai báo rõ stage nào **real**, stage nào **stub**.
Dùng stub không mất điểm; khai báo sai mới mất điểm. Nếu có code N19, thay hai chỗ
`STUB` trong `labs/03-integrate/pipeline.py`.

## Bước 1.7 — Viết REFLECTION.md

Mở [`submission/REFLECTION.md`](submission/REFLECTION.md) và điền đủ mọi section. Đây
là file grader đọc kỹ nhất.

Phần quan trọng nhất là **§5 "The single change that mattered most"** (10 điểm). Dùng
kết quả `make tune` ở bước 1.2 và giải thích **cơ chế**: memory bandwidth, cache hay
scheduling. Không chỉ nêu cảm nhận hoặc chép lại con số.

## Bước 1.8 — Kiểm tra base track

```bash
make verify
```

Lệnh này phải **exit 0**. Nếu fail, output sẽ liệt kê file còn thiếu và lệnh cần chạy.

**Base track hoàn tất tại đây. Bạn đã có đủ bằng chứng cho 100 điểm base.**

---

# PHASE 2 — Bonus track (20 điểm, optional)

> **Chỉ bắt đầu khi PHASE 1 đã hoàn tất và `make verify` đã exit 0.** Bonus không bù
> được phần base còn thiếu.

Chi tiết: [`bonus/README.md`](bonus/README.md) ·
[`bonus/CHALLENGES.md`](bonus/CHALLENGES.md)

Chọn **1–2 mục**, không cần làm hết. Có 5 tiêu chí, mỗi tiêu chí 4 điểm:

| | Lệnh | Ghi chú |
|---|---|---|
| **B1** | `make build-llama && make compare-builds` | Compile cho CPU của bạn rồi so với prebuilt binary. **Máy yếu thường có mức cải thiện rõ nhất ở đây.** Cần `cmake`. |
| **B2** | `make sweep-quant` / `sweep-ctx` / `sweep-batch` / `sweep-gpu` | Chọn 1 sweep phù hợp với bottleneck của bạn |
| **B3** | — | Ghi before/after của B1 hoặc B2 vào REFLECTION §6 |
| **B4** | — | Chọn 1 challenge C1–C7 trong `bonus/CHALLENGES.md` |
| **B5** | `make mlx-compare` (Mac) **hoặc** `make semantic-cache` (C8) **hoặc** `make serve-embed && make embed-demo` (C9) **hoặc** C6 | 4 lựa chọn; nền tảng nào cũng có lựa chọn phù hợp |

Gợi ý theo máy và mục tiêu:

- **CPU-only** → B1 (`compare-builds`). Đây thường là speedup lớn nhất trong lab.
- **RAM hạn chế** → `make sweep-quant`.
- **Có GPU** → `make sweep-gpu`.
- **Quan tâm RAG long-context** → `make sweep-ctx`.
- **Không muốn tải thêm** → C8 hoặc C9, có thể chạy với `--offline`.

Mỗi bonus script cũng sinh file `benchmarks/bonus-*.md` có section
*"required -- replace this line"*. Bạn vẫn phải điền section này.

---

# PHASE 3 — Submit

1. Chạy `make verify` lần cuối. Kết quả phải **exit 0**.
2. Fork/copy repo lên GitHub account của bạn và set **public**.
3. Commit và push:

   ```bash
   git add -A && git commit -m "Day 20 lab submission" && git push
   ```

4. Paste public URL vào ô submission Day 20 trên VinUni LMS.

**Repo phải public cho đến khi điểm được công bố.** Nếu repo private, grader không thể
đọc bài và bạn nhận **0 điểm**.

Không commit `models/*.gguf` hoặc `runtime/`. Hai path này đã có trong `.gitignore`, và
`make verify` không yêu cầu chúng.

---

# Troubleshooting

| Triệu chứng | Cách xử lý |
|---|---|
| `unknown model architecture: 'gemma4'` | llama.cpp quá cũ. Chạy `make runtime` để tải lại bản đã pin. |
| `make probe` báo `GPU offload : OFF` dù máy có GPU | Bình thường, và **không mất điểm** — toàn bộ 100 điểm base chạy trên CPU. Upstream llama.cpp **không** phát hành bản CUDA cho Linux, nên máy Linux + NVIDIA nhận bản Vulkan; thiếu Vulkan ICD thì runtime không thấy device nào. Lab tự set `ngl=0` để report không ghi sai. Muốn dùng GPU: `LLAMA_CMAKE_FLAGS=-DGGML_CUDA=ON make build-llama` (bonus B1). |
| `make serve` báo không tìm thấy venv | Bạn chưa chạy `make setup`. |
| `couldn't bind HTTP server socket … port: 8080` | Có process khác đang giữ port 8080. Đổi port: `LAB_SERVER_PORT=8090 make serve` (và dùng cùng biến đó cho `make smoke`, `make load-10/50`, `make metrics`, `make pipeline`). Trên Colab notebook đã set sẵn. |
| `make bench` fail, câu trả lời rỗng | Gemma 4 là reasoning model; lab đã set `--reasoning off`. Nếu bạn tự bật `LAB_REASONING=on`, `content` sẽ rỗng cho đến khi model "nghĩ" xong. |
| `make metrics` báo scrape failed | Server chưa chạy. Chạy `make serve` trước. |
| `busy_slots ≈ 1` dù đã chạy metrics | Bạn chạy `make metrics` khi không có load. Phải chạy chồng với `make load-50`. |
| locust chỉ hoàn thành vài request | Bình thường trên máy yếu. Muốn thêm mẫu, dùng `-t 3m` hoặc giảm `LAB_LOAD_SHORT_TOKENS`. |
| Hugging Face bị chặn | Xem [`labs/00-setup/MANUAL-DOWNLOAD.md`](labs/00-setup/MANUAL-DOWNLOAD.md). |
| Máy < 8 GB RAM | Dùng [`cloud/README.md`](cloud/README.md). |
| `make verify` fail mà chưa rõ lý do | Output ghi đúng file còn thiếu và lệnh cần chạy. Đọc từng dòng lỗi. |
| Sau checklist có dòng `make: *** [verify] Error 1` | Bình thường. Đó chỉ là cách `make` báo rằng `verify` tìm thấy mục còn thiếu — không phải `make` bị lỗi. Đọc checklist ở trên nó. |

## Các knob có thể đổi

Không cần tạo file `.env`. Set inline:

```bash
LAB_N_THREADS=4 make bench       # dùng thread count tốt nhất từ make tune
LAB_N_CTX=4096 make serve        # context lớn hơn (tốn RAM hơn)
LAB_PARALLEL=8 make serve        # nhiều slot hơn
LAB_REASONING=on make bench      # bật thinking để đo chi phí
```

Danh sách đầy đủ: [`.env.example`](.env.example)
