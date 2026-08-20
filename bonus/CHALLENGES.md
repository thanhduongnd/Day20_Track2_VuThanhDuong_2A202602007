# Các challenge bonus — chọn một mục và phân tích sâu

Các sweep là phần khởi động. Những challenge dưới đây có tính mở. **Hãy chọn một.**
Một bài C5 được giải thích sâu tốt hơn việc làm C1, C2 và C3 ở mức sơ sài.

C1–C7 và C10 đáp ứng tiêu chí bonus **B4**. C6, C8 và C9 cũng có thể dùng riêng để đáp ứng
**B5**. Xem [`README.md`](README.md). Trước tiên, hãy kiểm tra mọi flag trên binary của
bạn bằng `llama-server --help | grep <flag>`. llama.cpp thay đổi nhanh và tài liệu này
được cố định theo build `b10488`.

---

## C1. Speculative decoding bằng MTP head của Gemma 4

> **Yêu cầu `LAB_MODEL=gemma4-e2b`.** Qwen3.5 0.8B không phát hành MTP head, nên
> challenge này chỉ dùng được với Gemma. Nếu dùng model nhỏ, hãy chọn C2, C5, C7, C8
> hoặc C9.

Gemma 4 E2B phát hành riêng một **MTP (multi-token prediction) head** dưới dạng GGUF.
Bạn không cần tìm một draft model tương thích tokenizer vì draft khớp với target đã
được phát hành cùng model.

```bash
.venv/bin/python labs/00-setup/download-model.py --with-mtp     # ~98 MB
llama-server --help | grep -iE "draft|mtp|spec"       # find the current flag names
```

Trong build `b10488`, các draft flag là `-md/--model-draft` và `--draft-max`, **không
phải** `--draft-model`. Tên sau là cách viết của vLLM. MTP head được gắn qua `-md` hay
một flag chuyên biệt là điều bạn phải xác nhận bằng `--help` trước khi
chạy.

Đo token/giây khi bật và tắt speculative decoding ở 2–3 mức temperature. Deck nêu
EAGLE-3 đạt 3–6.5×, nhưng kết quả của bạn có thể thấp hơn nhiều. Hãy giải thích khoảng
cách dựa trên acceptance rate, tỷ lệ kích thước draft/target và ảnh hưởng của greedy
so với sampled decoding.

Speculative decoding là một tối ưu latency. Khi concurrency cao, chi phí verification
có thể làm kết quả chậm hơn. Vì vậy, production engine thường tắt cơ chế này khi batch
size vượt một threshold. Chạy `make load-50` khi bật và tắt nó để kiểm tra hiện tượng
trên máy của bạn.

## C2. Quantization cho KV cache

```bash
.venv/bin/python labs/02-serve/serve.py -- --cache-type-k q8_0 --cache-type-v q8_0
```

Đây là cách kiểm tra ý tưởng “FP8 KV cache” trong deck trên CPU, Metal hoặc Vulkan.
Đo ba yếu tố: lượng RAM giảm, thay đổi latency và thay đổi chất lượng. Theo dõi RSS của
process khi `--ctx-size` tăng. Với chất lượng, hãy tạo một eval gồm 10 prompt có thể
chấm tự động, chẳng hạn trích xuất JSON hoặc phép tính số học. Tiết kiệm bộ nhớ nhưng
làm giảm accuracy không phải là một kết quả tốt.

## C3. Phục vụ nhiều LoRA

`--lora` chấp nhận nhiều adapter. Tìm hoặc train hai LoRA nhỏ. Hugging Face có nhiều
lựa chọn, chẳng hạn một LoRA cho SQL và một LoRA cho tool calling. Phục vụ cả hai trên
cùng base weights, rồi đo chi phí chuyển adapter theo từng request. Đây là khung phục
vụ Multi-LoRA trong deck, gồm Punica và S-LoRA, ở quy mô laptop.

## C4. Lấy mẫu Best-of-N với reranker

Gửi cùng một prompt N lần song song với các seed khác nhau, sau đó dùng một reranker
nhẹ để chọn câu trả lời tốt nhất. Có thể bắt đầu bằng heuristic về độ dài hoặc mức lặp.
Đo end-to-end latency và chất lượng so với single-shot.

Mục đích là kiểm tra cách dùng throughput để tăng chất lượng cho một người dùng thay vì
phục vụ thêm người dùng. Các slot của `--parallel` không phân biệt hai cách sử dụng này.

## C5. Challenge “model nhỏ nhất vẫn hữu ích”

Nếu laptop của bạn chậm, hãy đi dần xuống dải Unsloth Dynamic:
`UD-Q8_K_XL` → `UD-Q4_K_XL` → `UD-Q2_K_XL` → `UD-IQ2_M`. Tìm mức model ngừng hữu ích,
không chỉ mức model ngừng nhanh. Tự chấm 5 prompt ở mỗi mức.

Sản phẩm cần nộp là lập luận về quantization bạn thực sự sẽ triển khai trong giới hạn
RAM của mình, kèm một failure quan sát được ở mức thấp hơn kế tiếp.

## C6. Vulkan so với CUDA trên cùng GPU *(cũng đáp ứng B5)*

Nếu có NVIDIA GPU, bạn đã có một nửa thí nghiệm. Trên Linux, prebuilt runtime của lab
là bản Vulkan vì llama.cpp **không phát hành prebuilt CUDA binary cho Linux**. Hãy build
phía CUDA:

```bash
LLAMA_CMAKE_FLAGS=-DGGML_CUDA=ON make build-llama
make compare-builds
```

Việc build với `-DGGML_CUDA=ON` và so sánh bằng `make compare-builds` đồng thời hoàn
thành challenge C6. Định lượng khoảng cách, rồi trả lời câu hỏi chính: vì sao vLLM và
SGLang dùng kernel riêng theo nhà cung cấp như FA3, FA4, FlashMLA và TRTLLM-MHA thay vì
chỉ cung cấp một đường Vulkan dùng chung. Số đo của bạn là bằng chứng cho lập luận.

## C7. Khảo sát instruction set của CPU

Build hai lần với `-DGGML_NATIVE=ON` và `-DGGML_NATIVE=OFF`. Vế thứ hai tạo một bản CPU
baseline chung. Sau đó so sánh hai bản. Kiểm tra CPU thật sự hỗ trợ gì bằng
`/proc/cpuinfo` trên Linux hoặc `sysctl -a | grep machdep.cpu` trên macOS, rồi thử bật
tường minh các extension.

Lập bảng build flag so với token/giây. Đây là cùng loại quyết định mà hệ thống cloud
đưa ra khi chọn FA3 cho Hopper hoặc FA4 cho Blackwell: kernel phải khớp với silicon.

Không bao giờ so sánh một bản Debug với một bản Release rồi gọi chênh lệch đó là
speedup.

## C8. Semantic cache — cache phía trên KV cache *(cũng đáp ứng B5)*

Deck mô tả serving stack có **ba tầng cache**:

```
request -> [1] semantic cache (meaning) -> [2] prefix/KV cache -> [3] full inference
```

Khi tầng 1 hit, hệ thống trả lại câu trả lời đã lưu cho một prompt được paraphrase mà
không tốn compute, prefill hay decode. Tầng 2 chỉ có ích khi prefix giống nhau từng byte.

```bash
make serve &            # chat       :8080
make serve-embed &      # embeddings :8081
make semantic-cache
# no servers? logic demo + threshold sweep:
.venv/bin/python bonus/serving-regimes/semantic-cache-demo.py --offline --sweep
```

**Lab không có embedding model chuyên dụng, nên `make serve-embed` chạy chat model ở
pooling mode.** Mean-pooled decoder state là một sentence encoder yếu. Paraphrase thật
có thể có điểm thấp hơn prompt không liên quan. Không báo raw hit rate như một kết quả
chất lượng. Sản phẩm cần nộp là phần chẩn đoán:

- Nêu một **false hit**, tức prompt không liên quan nhưng vẫn match, kèm similarity score.
- Nêu một **false miss**, tức paraphrase thật nhưng không match, kèm similarity score.
- Chứng minh không có một threshold duy nhất sửa được cả hai trường hợp.
- Giải thích vì sao decoder được train để dự đoán token kế tiếp không phải sentence
  encoder tốt, và embedding model chuyên dụng như Qwen3-Embedding, BGE-M3 hoặc
  EmbeddingGemma khác ở đâu.

Nếu muốn có một đường cong rõ hơn, hãy đặt `--embed-url` tới server đang chạy một GGUF
embedding model thực và so sánh hai phân phối similarity. So sánh weak embedder với
proper embedder trên cùng prompt stream là bằng chứng mạnh hơn bảng hit rate riêng lẻ.

Trong báo cáo, hãy nêu thêm rủi ro bảo mật: semantic cache và prefix cache dùng chung có
thể làm lộ thông tin giữa người dùng qua timing side channel. Hệ thống production
thường thêm salt theo từng tenant.

## C9. Phục vụ embedding và reranker — phần retrieval *(cũng đáp ứng B5)*

Embedding serving là một **regime khác**: mỗi văn bản chỉ cần một forward pass, không có
KV cache và không có vòng decode. Throughput đến từ static batch lớn, không phải
continuous batching.

```bash
make serve-embed &
make embed-demo
```

Đo cách latency thay đổi theo batch size trong trường hợp chỉ có prefill, rồi so sánh
đường cong đó với số liệu bị giới hạn bởi decode ở track 02. Giải thích vì sao chat
endpoint và embedding endpoint cần chiến lược batching trái ngược nhau, cùng hệ quả khi
phục vụ cả hai sau một autoscaler.

Demo dùng lại chat GGUF để tránh tải thêm. Retrieval thực tế cần embedding model chuyên
dụng. Hãy ghi rõ giới hạn này trong báo cáo.

## C10. Phục vụ VLM, dạng mở

Gemma 4 E2B là model đa phương thức. Repo cung cấp `mmproj-F16.gguf`, khoảng 986 MB, làm
vision projector. Deck §5 xếp VLM serving vào nhóm bài toán kiểu datacenter, nhưng bạn
vẫn có thể chạy trên máy của mình:

```bash
# fetch mmproj-F16.gguf from the same repo, then:
.venv/bin/python labs/02-serve/serve.py -- --mmproj models/mmproj-F16.gguf
```

Hãy tự thiết kế thí nghiệm. Câu hỏi chính là: một hình ảnh trong prompt thay đổi TTFT và
dung lượng KV cache như thế nào so với cùng số lượng text token. Repo không cung cấp
script cho challenge này.

---

## Cách viết báo cáo

Với challenge đã chọn, hãy viết một section trong `submission/REFLECTION.md` hoặc tạo
`bonus/<challenge>.md`:

- **Thiết lập** — phần cứng và thay đổi chính xác bạn đã thực hiện.
- **Số liệu** — bảng before/after.
- **Một đoạn phân tích** — điều bạn rút ra ngoài nội dung đã có trong deck.

Hãy ghi đúng kết quả kể cả khi nó trái kỳ vọng. Một finding bất ngờ được giải thích rõ
thường có giá trị hơn kết quả khớp kỳ vọng nhưng không được phân tích.
