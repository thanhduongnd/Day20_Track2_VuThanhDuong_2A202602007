# 01 - Tune: thread-count sweep

Model `Qwen3.5-0.8B-Q4_K_M.gguf` · host `Linux-x86_64` · llama.cpp `b10488`
CPU: **4 physical · 8 logical** cores · `ngl=0` · metric `tg128`

| threads (-t) | tg128 (tok/s) | vs best |
|:--|--:|--:|
| 1 | 16.2 | 55% |
| 2 | 22.7 | 77% |
| 4 | 29.3 | 100% |
| 8 | 29.4 | 100% |
| 16 | 3.6 | 12% |

**Best**: `-t 8` at 29.4 tok/s
**Slowest tested**: `-t 16` at 3.6 tok/s (8.21x spread)
**Against the physical-core default** (`-t 4`, 29.3 tok/s): 1.00x

Use this in your run:

```bash
LAB_N_THREADS=8 make bench
```

## Your explanation

Curve tăng gần tuyến tính từ 1 → 4 threads (16.2 → 29.3 tok/s), sau đó **flat** ở
4 → 8 threads (29.3 → 29.4 tok/s, chỉ +0.3%) chứ không tăng thêm, rồi **sập** ở 16
threads (3.6 tok/s, còn 12% so với đỉnh). Máy này có 4 physical / 8 logical cores
(Intel i5-1135G7, có hyperthreading).

Knee thật sự nằm ở `-t 4` — đúng bằng số physical core. Việc `-t 8` không nhanh
hơn `-t 4` cho thấy hyperthreading không giúp gì cho tác vụ này: decode của
llama.cpp là workload **memory-bandwidth-bound** (mỗi token phải đọc lại toàn bộ
trọng số qua RAM), không phải compute-bound, nên 2 logical thread trên cùng một
physical core chia sẻ chung một cổng bộ nhớ và cache L1/L2 — chúng cạnh tranh
băng thông thay vì làm thêm việc hữu ích. Đó là lý do `-t 8` chỉ hoà chứ không
vượt `-t 4`.

Cú sập ở `-t 16` mạnh hơn nhiều so với kỳ vọng "oversubscribe nhẹ" — tốc độ giảm
tới 88%. Với 8 logical core mà yêu cầu 16 thread, hệ điều hành phải liên tục
context-switch giữa các thread chờ CPU, đồng thời làm nguội cache (mỗi lần
switch có thể đá dữ liệu hot ra khỏi L1/L2 của thread khác), nên phần lớn thời
gian bị tốn vào scheduling overhead thay vì decode. Kết luận: với CPU 4C/8T,
đặt `-t` bằng đúng số **physical core** (4) là lựa chọn tốt nhất — vừa đạt tốc
độ tối đa, vừa không tốn thêm luồng vô ích như `-t 8`.
