# 02 - Continuous batching under load (u50)

Host `Linux-x86_64` · `--parallel 4` · 29 samples over
60s at 2.0s intervals · raw CSV: `02-server-metrics-u50.csv`

| Gauge | Peak observed |
|:--|--:|
| `n_busy_slots_per_decode` (avg/decode) | 3.90 of 4 slots (97%) |
| `requests_processing` | 4 |
| `requests_deferred` | 46 |
| `kv_cache_usage_ratio` | n/a — not exported by llama.cpp `b10488` |
| `tokens_predicted_total` (final) | 3400 |

Highest sampled value was **3.90 of 4** slots. Note this gauge is llama.cpp's *average* busy slots per decode step, so the number below is the highest average we sampled, not an instantaneous maximum batch width. A peak near 1 means
requests were served one at a time -- either the load was too light to overlap, or
they arrived too far apart. A peak approaching `--parallel` means the scheduler was
genuinely packing concurrent requests into shared decode steps.
`requests_deferred` went above zero: more requests arrived than there were slots, so some waited. That wait is the queue time in your P95.

## Your observation

Peak batch width quan sát được là **3.90 of 4 slots** — gần chạm trần
`--parallel 4`, tức server thực sự đang gộp nhiều request vào chung một bước decode
(continuous batching hoạt động đúng như kỳ vọng), không phải xử lý tuần tự từng
request một.

Con số này **không khớp** với effective concurrency (17.5) tính trong
`02-server-results.md`, và tôi cho là đúng — hai con số đo hai thứ khác nhau chứ
không mâu thuẫn. `n_busy_slots_per_decode` là số slot **đang thực sự decode** tại
một thời điểm, nên nó không thể vượt quá `--parallel`. Effective concurrency (Little's
Law: RPS × latency trung bình) đếm cả những request **đang nằm chờ trong hàng đợi**
(`requests_deferred` đạt tới 46 trong lần sample này), nên nó phản ánh occupancy của
toàn hệ thống chứ không phải utilization của compute.

Tôi tin `n_busy_slots_per_decode` hơn khi cần biết server có đang tận dụng hết
song song hay không (nó nói "có", đã gần no 4/4), còn effective concurrency đáng tin
hơn khi cần biết **áp lực hàng đợi** lớn cỡ nào (17.5 so với 4 slot nghĩa là tại một
thời điểm trung bình có hơn 4x số request đang chờ được phục vụ so với sức chứa —
đúng là dấu hiệu saturation, không phải mâu thuẫn với batch width).
