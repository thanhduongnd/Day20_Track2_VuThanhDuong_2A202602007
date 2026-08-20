# Cloud fallback — Colab / Kaggle

> Các bước của lab không đổi: **[GUIDE.md](../GUIDE.md)**

Đây là **phương án fallback**, không phải cách chạy mặc định. Hãy dùng
[`Day20-lab.ipynb`](Day20-lab.ipynb) khi laptop có dưới **4 GB RAM**, hoặc khi setup local
gặp lỗi bạn không thể xử lý.

> **Thử cách này trước.** Nếu máy bạn có 4–8 GB RAM, bạn vẫn chạy được lab **local** với
> model nhỏ:
>
> ```bash
> LAB_MODEL=qwen35-0.8b make setup
> ```
>
> Qwen3.5 0.8B chỉ ~0.9 GB và cần 4 GB RAM. Chạy local luôn tốt hơn cloud vì bạn đo được
> chính máy mình — đó là mục đích của lab.

## Dùng cloud không mất điểm

Rubric chấm độ rõ ràng của setup, phép đo và lập luận. Rubric không chấm tốc độ tuyệt
đối và không giả định hai sinh viên có phần cứng giống nhau.

Tuy nhiên, bạn **bắt buộc phải khai báo** trong **REFLECTION §1** rằng mình dùng cloud
fallback và nêu lý do. Việc khai báo **không làm mất điểm**. Notebook tự ghi
`runtime_environment: "colab"` hoặc `"kaggle"` vào `hardware.json`, nên bạn chỉ cần
thêm một dòng giải thích.

## Mở notebook

| Nền tảng | Cách mở |
|---|---|
| **Colab** | Mở trực tiếp: [colab.research.google.com/github/VinUni-AI20k/Day20-Track2-ModelServing/blob/main/cloud/Day20-lab.ipynb](https://colab.research.google.com/github/VinUni-AI20k/Day20-Track2-ModelServing/blob/main/cloud/Day20-lab.ipynb) — hoặc File → Open notebook → GitHub → paste URL repo |
| **Kaggle** | Mở [kaggle.com/code](https://www.kaggle.com/code) → New Notebook → File → Import Notebook → upload `cloud/Day20-lab.ipynb` |

**Trên Kaggle, phải bật Internet** trong settings sidebar trước khi chạy. Nếu Internet
tắt, notebook không thể tải model.

Cell đầu tiên đã trỏ sẵn tới repo gốc (public) nên bạn chạy được ngay. Đổi `REPO_URL`
sang fork của bạn nếu muốn — không bắt buộc, vì artifact được sinh trong VM rồi bạn
tải zip về máy.

## CPU hay GPU?

Trên VM 2 vCPU, model nhỏ là lựa chọn hợp lý hơn. Set trong cell đầu:
`LAB_MODEL = 'qwen35-0.8b'` — tải nhanh hơn ~6 lần và decode nhanh hơn, nên cả notebook
chạy xong nhanh hơn nhiều.

Notebook mặc định dùng `RUNTIME = 'cpu'`. Đây là cấu hình chủ đích và chạy được toàn bộ
base track, nhưng chậm hơn. Với 2 vCPU, mỗi benchmark có thể mất vài phút.

Notebook không mặc định dùng GPU vì llama.cpp **không cung cấp prebuilt Linux CUDA
binary**. Image Colab/Kaggle cũng **không có Vulkan driver**. Vì vậy các prebuilt asset
tăng tốc không có backend phù hợp để sử dụng.

Muốn dùng T4, bạn phải compile với `-DGGML_CUDA=ON`. Cell 4b thực hiện việc này trong
khoảng 8 phút.

Phần compile không bị lãng phí: nó đạt bonus **B1**. Khi có cả CUDA build và Vulkan
prebuilt trên cùng một máy, bạn cũng có sẵn điều kiện cho challenge **C6**.

## Artifact và filename không đổi

Notebook chạy cùng các script với cách làm trên laptop, nên sinh đúng các file sau:

```
hardware.json
models/active.json
benchmarks/01-quickstart-results.md
benchmarks/01-tuning-tg128.md
benchmarks/02-server-results.md
benchmarks/02-server-batching-u50.md  +  02-server-metrics-u50.csv
benchmarks/locust-10_stats.csv  ·  locust-50_stats.csv
```

`scripts/verify.py` không cần nhánh xử lý riêng cho cloud.

## Hoàn tất bài trên máy local

Cell cuối cùng nén các file bằng chứng, không nén model weights. Download file zip, giải
nén vào clone local của bạn, rồi làm lần lượt:

1. Thay mọi section **"required -- replace this line"** trong `benchmarks/*.md` bằng
   nhận xét của bạn. Nếu còn bất kỳ section nào, `make verify` sẽ fail.
2. Điền `submission/REFLECTION.md`, gồm cả khai báo cloud trong §1.
3. Thêm 5 screenshots từ output của các notebook cell.
4. Chạy `make verify` và bảo đảm lệnh **exit 0**. Sau đó push lên repo **public** và
   submit URL.

## Lỗi thường gặp

| Vấn đề | Cách xử lý |
|---|---|
| Session ngắt giữa chừng | Chạy lại từ section 3. Bước clone và download sẽ bỏ qua phần đã có trên disk. |
| Kaggle báo "no internet" | Settings sidebar → Internet → On. |
| Colab free tier hết thời gian | Rút ngắn load test: set `LOAD_DURATION = '30s'` trong cell 1. |
| `unknown model architecture: 'gemma4'` | Bước tải runtime đã bị bỏ qua hoặc fail. Chạy lại section 4. |
| `couldn't bind HTTP server socket ... port: 8080` | Colab đã chiếm port 8080. Notebook đã set `LAB_SERVER_PORT = '8090'` sẵn — nếu bạn sửa dòng đó thì chọn port còn trống khác. |
| Hết disk | Free tier thường đủ cho 5.2 GB. Nếu buộc phải xóa, xóa `models/*Q2*`; bạn sẽ mất hàng quantization thứ hai của rubric 3–5. |

## Số đo thật trên Colab (đã kiểm chứng)

Toàn bộ base track đã được chạy end-to-end trên một Colab CPU runtime. Đây là kết quả
thật, để bạn biết trước cái gì là bình thường:

| | Colab CPU runtime |
|---|--:|
| CPU | Intel Xeon @ 2.20 GHz, **1 physical / 2 logical** core, AVX2 |
| RAM | 12.7 GB |
| Model load (Qwen3.5 0.8B Q4_K_M) | ~3.5 s |
| Decode | **~8–10 tok/s** |
| 1 request 48 token | **~6–7 s** |
| Trần throughput | **~0.15 request/s** — chỉ 1 core, thêm slot không giúp |
| Request hoàn thành trong 1 phút load | **~7–10** |
| `requests_deferred` lúc 50 user | **46** |

Hai điều rút ra:

1. **Percentile sẽ mỏng.** Ít mẫu thì percentile không chắc, và `load-report` tự cảnh báo
   điều đó. Muốn số chắc hơn thì đặt `LOAD_DURATION = '3m'` ở cell 1.
2. **Bằng chứng saturation lại rõ hơn trên máy chậm.** `processing=4` cùng với
   `deferred=46` là hình ảnh trực tiếp của queue time — đúng chỗ goodput bị mất mà deck
   §8 nói tới. Trên laptop nhanh, gauge này thường bằng 0 và bài học khó thấy hơn.

Trên Colab, `verify` cũng báo `hardware.json` và các file `locust-*_stats.csv` là
`NOT committed`. Bình thường: clone trong VM không phải repo của bạn. Sau khi giải nén
zip vào clone local và `git add`, các dòng đó sẽ hết.

Thread sweep (`tune`) trên VM 1 core cho grid rất ngắn — thường chỉ `[1, 2]` với spread
~1.07x. Vẫn hợp lệ; phần giải thích mới là chỗ được chấm.

## Giới hạn cần nêu trong REFLECTION

Cloud VM không phải laptop của bạn. VM có core count và memory bandwidth khác, chạy
qua hypervisor, và có thể chia sẻ host với workload của người khác. Vì vậy, kết quả
tuning mô tả **VM được cấp**, không mô tả laptop của bạn. Thread-count curve cũng có
thể rất khác máy vật lý.

Hãy nêu giới hạn này trong **REFLECTION §5**. Đây là một phần quan trọng khi diễn giải
số liệu, đặc biệt nếu bạn dùng cloud fallback.
