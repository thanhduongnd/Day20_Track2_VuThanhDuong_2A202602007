# 02 - Serve: load test + saturation reading

Host `Linux-x86_64` · llama.cpp `b10488` ·
`--parallel 4` · `ctx=2048` · `threads=4` ·
`ngl=0`

| Users | Reqs | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Eff. concurrency | Failures |
|:--|--:|--:|--:|--:|--:|--:|--:|
| 10 | 28 | 0.51 | 15000 | 27000 | 30000 | 8.0 | 0.0% |
| 50 | 30 | 0.55 | 34000 | 54000 | 57000 | 17.5 | 0.0% |

*Effective concurrency = RPS x average latency (Little's Law) -- how many requests were
really in flight, regardless of how many users locust simulated. It counts queued requests
too, so the occupancy/slot ratio can legitimately exceed 1.0; it is occupancy, not
utilisation. For true slot utilisation use the server's own gauges (`make metrics`).*

## What these two runs say

| Going from 10 to 50 users | |
|:--|--:|
| Offered load | 5x |
| Throughput actually delivered | **1.08x** (22% of linear) |
| P95 latency | **2.00x** |
| Effective concurrency at 50 users | 17.5 vs `--parallel 4` slots (occupancy/slot ratio 4.38) |

**Saturated.** Throughput delivered only 1.08x for 5x the offered load, and effective concurrency (17.5) is at or above all 4 decode slots. Saturation sets in somewhere at or below 50 users; the load you added beyond that point became queue time rather than throughput.

Throughput moved 1.08x while P95 moved 2.00x. That gap is the goodput argument: past saturation you buy throughput by spending latency, and if your SLO is a P95 target then the requests you added are no longer being served within it. (This lab does not fix an SLO number for you -- pick one in your write-up and state how much goodput you keep at it.)

## Your reading

Server đã bão hoà **ở hoặc trước 50 users**. Bằng chứng thuyết phục nhất là cặp số
throughput vs latency: offered load tăng 5x (10 → 50 users) nhưng throughput thực
chỉ tăng **1.08x** (0.51 → 0.55 RPS) — gần như flat — trong khi P95 tăng **2.00x**
(27000 → 54000 ms). Nếu server còn dư sức, throughput phải tăng gần tuyến tính theo
load; ở đây gần như toàn bộ load thêm vào biến thành hàng đợi chứ không phải công
việc hữu ích. Effective concurrency ở 50 users là 17.5, cao hơn nhiều so với 4 slot
của `--parallel`, và `requests_deferred` trong `make metrics` lên tới 46 — xác nhận
phần lớn request đang **chờ** chứ không chạy song song thật.

Tôi tin số `n_busy_slots_per_decode` (peak 3.90/4, từ `make metrics`) hơn số
"effective concurrency" 17.5, vì gauge của server đo trực tiếp số slot đang decode
thật tại một thời điểm — nó đã chạm trần 4 slot ngay khi có tải. Effective
concurrency (Little's Law) cố tình tính cả phần đang **chờ trong hàng đợi**, nên nó
lớn hơn số slot thật — đó là occupancy của toàn hệ thống, không phải utilization
của compute.

Nếu phải nâng goodput@SLO, knob đầu tiên tôi đổi là **`--parallel`** (tăng số slot
đồng thời, ví dụ 4 → 8), vì bằng chứng cho thấy nút thắt là **số slot decode**, không
phải compute-per-token: `n_busy_slots_per_decode` đã bão hoà ở đúng giá trị
`--parallel`, trong khi threads (`make tune`) đã ở mức tối ưu (`-t 4`) rồi. Tăng
`--parallel` cho phép nhiều request chạy song song hơn trước khi rơi vào hàng đợi,
với chi phí là mỗi slot có ít KV-cache/ctx hơn (đánh đổi RAM) — đó là knob trực tiếp
đúng với nút thắt quan sát được, thay vì đổi threads hay quantization vốn không phải
là bottleneck ở đây.
