# Phần bonus (+20 điểm, không bắt buộc)

> Chỉ bắt đầu khi bạn đã hoàn tất base track và `make verify` exit 0. Xem
> **[GUIDE.md → PHASE 2](../GUIDE.md)**.

Ở phần lab chính, bạn được cung cấp một prebuilt binary và một server hoạt động sẵn.
Trong track này, bạn đi xuống một lớp thấp hơn: tự compile llama.cpp cho CPU của mình,
chạy sweep các knob quan trọng trên phần cứng của mình và giải thích kết quả.

> **Laptop yếu hoặc chỉ có CPU thường hưởng lợi nhiều nhất ở B1.** Prebuilt binary dùng
> trong lab phải chạy được trên nhiều máy nên chỉ nhắm tới một CPU baseline chung. Bản
> build dành cho CPU thật của bạn có thể dùng đúng các vector extension mà CPU hỗ trợ.
> Vì vậy, khoảng cách thường rõ nhất trên phần cứng khiêm tốn. Đây thường là speedup lớn
> nhất có thể đạt được trong lab này.

**Thời gian dự kiến:** 60–120 phút. Riêng bước build mất 5–15 phút. Mỗi sweep mất
5–15 phút. **Không cần chạy tất cả.** Hãy chọn một hoặc hai mục phù hợp với phần cứng
và câu hỏi bạn muốn trả lời.

---

## Năm tiêu chí bonus, mỗi tiêu chí 4 điểm

| # | Được điểm khi | Lệnh | Điểm |
|--:|---|---|--:|
| B1 | Compile llama.cpp cho CPU của bạn và **so với prebuilt binary** | `make build-llama && make compare-builds` | 4 |
| B2 | Chạy ít nhất 1 sweep | `make sweep-quant` / `sweep-ctx` / `sweep-batch` / `sweep-gpu` | 4 |
| B3 | Speedup **của bonus track** có before/after rõ ràng | REFLECTION §6 (từ B1 hoặc B2, **không** phải kết quả `make tune` của base) | 4 |
| B4 | Làm ít nhất 1 challenge C1–C7 hoặc C10 | [`bonus/CHALLENGES.md`](CHALLENGES.md) | 4 |
| B5 | Một so sánh runtime/regime — **chọn 1**: MLX (Mac) · C8 semantic cache · C9 embedding serving · C6 Vulkan vs CUDA | `make mlx-compare` · `make semantic-cache` · `make embed-demo` | 4 |

**Tổng bonus: 20 điểm.**

Chi tiết từng challenge có trong [`CHALLENGES.md`](CHALLENGES.md).

B1 yêu cầu cả hai phần: build từ mã nguồn **và** so sánh với prebuilt binary bằng
`make compare-builds`. Chỉ build thành công chưa đủ để đạt B1.

B5 có bốn lựa chọn để mọi nền tảng đều có thể đạt 20/20:

| Máy của bạn | Lựa chọn B5 |
|---|---|
| Apple Silicon | `make mlx-compare` — MLX so với llama.cpp Metal trên cùng model; cần `pip install 'mlx-lm>=0.31.3' mlx` |
| NVIDIA GPU | **C6** Vulkan so với CUDA; bạn đã có phía Vulkan/prebuilt |
| Mọi nền tảng | **C8** `make semantic-cache` — cache nằm phía trên KV cache |
| Mọi nền tảng | **C9** `make serve-embed && make embed-demo` — regime bị giới hạn bởi prefill |

C8 và C9 cũng chạy được với `--offline`. Khi đó, script dùng embedding tổng hợp và
không cần server. Bạn có thể đọc, chạy và phân tích logic trong lúc chờ tải model.

Trước khi chọn, bạn cần biết hai điểm sau:

- **Model chỉ ảnh hưởng tới một challenge.** C1 về speculative decoding cần MTP head
  của Gemma 4 E2B. Qwen3.5 0.8B không phát hành MTP head. B1, B2, B3, B5 và C2–C10
  đều dùng được với cả hai model. Với model nhỏ, hãy chọn C2, C5, C7, C8 hoặc C9 thay
  cho C1. Các sweep đọc dải quantization từ model registry, nên `make sweep-quant`
  tự thích ứng với model bạn đã chọn.

- **MLX:** khi strict load, `mlx-lm` từ chối khoảng 140 parameter trong bộ Gemma 4
  MLX weights của Unsloth. Gemma 4 E2B dùng chung KV ở 20 trong số 35 layer, còn quá
  trình chuyển đổi vẫn giữ lại tất cả parameter. Script
  `compare-mlx-vs-llama-cpp.py` phát hiện trường hợp này, thử lại bằng non-strict load
  và in một sample generation. Bạn phải kiểm tra sample đó có mạch lạc trước khi
  tin vào số đo. Bài này cần `mlx-lm >= 0.31.3`.

- **C8 semantic cache:** lab không có embedding model chuyên dụng. Vì vậy,
  `make serve-embed` chạy chat model ở pooling mode. Đây là một sentence encoder yếu;
  paraphrase thật có thể nhận điểm thấp hơn prompt không liên quan. Bài làm không yêu
  cầu báo hit rate. Bạn phải chẩn đoán vấn đề: nêu một false hit và một false miss kèm
  điểm số, rồi chứng minh không có một threshold duy nhất sửa được cả hai. Hãy đọc C8
  trước khi bắt đầu.

---

## Nên chạy sweep nào

| Trường hợp | Nên chạy | Lý do |
|---|---|---|
| Chỉ có CPU | **B1** `compare-builds`, rồi khảo sát thread kỹ hơn | Compile flag và số thread là hai knob chính của bạn |
| RAM hạn chế | `make sweep-quant` | Đo trực tiếp đánh đổi giữa kích thước, tốc độ và chất lượng |
| Có GPU | `make sweep-gpu` | Tìm điểm partial offload không còn cải thiện |
| Làm RAG với context dài | `make sweep-ctx` | Quan sát chi phí prefill tăng phi tuyến và tác động lên TTFT |
| Phục vụ nhiều người dùng | `make sweep-batch` | Đo cách chunked prefill đổi throughput lấy TTFT |

Cấu trúc thư mục:

```
bonus/
├── 01-build-from-source.md   ← per-OS, per-backend build guide
├── compare-builds.py         ← B1: prebuilt vs your build, same model, same workload
├── CHALLENGES.md             ← C1-C10, pick one and go deep
├── sweeps/
│   ├── quant-sweep.py        ← Unsloth Dynamic ladder, UD-IQ2_M -> UD-Q8_K_XL
│   ├── ctx-len-sweep.py      ← prefill cost vs prompt length
│   ├── batch-size-sweep.py   ← -b / -ub, chunked prefill
│   └── gpu-offload-sweep.py  ← -ngl 0..99
├── serving-regimes/
│   ├── embedding-serving.py  ← C9, prefill-bound regime
│   └── semantic-cache-demo.py ← C8, meaning-based cache
└── mlx/
    └── compare-mlx-vs-llama-cpp.py   ← B5 on Apple Silicon
```

Các report được ghi vào `benchmarks/bonus-*.md` ở thư mục gốc của repo. Hãy commit
những tệp này.

---

## Liên hệ với nội dung trong deck

Deck trình bày FlashAttention, PagedAttention, cách chọn kernel FA3 so với FA4 và MLA.
Đó là các quyết định trên GPU datacenter. Bạn không chạy được FA3 trên laptop, nhưng
vẫn có thể đo cùng một loại đánh đổi ở quy mô nhỏ:

| Knob trên laptop | Trường hợp tương ứng ở datacenter |
|---|---|
| Số thread `-t` | Độ rộng parallelism / kích thước TP |
| `-b` / `-ub` | Lập lịch chunked prefill |
| Lựa chọn quantization | Ma trận quyết định FP8 / INT4 / NVFP4 |
| Layer offload `-ngl` | Phần chạy trên accelerator so với host |
| `-DGGML_NATIVE=ON` | Chọn FA3 cho Hopper so với FA4 cho Blackwell |

Sau khi tự đo, bạn có thể xem `--gpu-memory-utilization` của vLLM như một đánh đổi cần
kiểm chứng, không phải một con số mặc định áp dụng cho mọi máy.

---

## Cách viết báo cáo

Trong `submission/REFLECTION.md`, dùng **§6**. §5 dành cho thay đổi của base track;
B3 phải dùng kết quả của bonus track.

```
Change:  <e.g. rebuilt llama.cpp with -DGGML_NATIVE=ON on a CPU with AVX-512>
Before:  <number + units>
After:   <number + units>
Speedup: <X.Y>x
Why it worked (1-2 paragraphs): <a mechanism, not vibes -- memory bandwidth?
                                 vector width? cache residency? scheduling?>
```

Mọi report được sinh dưới `benchmarks/` đều kết thúc bằng một section có đánh dấu
**"required -- replace this line"**. Bạn phải thay dòng đó bằng nhận xét của mình.
Nếu còn sót, `make verify` sẽ fail. Số liệu chỉ là đầu vào; phần giải thích mới là nội
dung được chấm.

Hãy trung thực khi kết quả trái với kỳ vọng. Một finding được giải thích kỹ có giá trị
hơn năm bảng số liệu nông. Kết quả đi ngược deck nhưng được phân tích rõ thường được
chấm cao hơn kết quả đúng kỳ vọng mà không có giải thích.

## Không so sánh giữa các laptop

Số liệu của bạn không so sánh được với số liệu của bạn cùng lớp. So sánh hợp lệ là
before và after trên cùng máy của bạn.
