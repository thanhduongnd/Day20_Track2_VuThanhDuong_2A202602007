# Build llama.cpp từ mã nguồn (bonus B1)

Bạn đã có llama.cpp hoạt động. `make setup` tải prebuilt release. Vậy vì sao cần
compile?

**Prebuilt binary được compile cho một CPU có thể không giống CPU của bạn.** Binary đó
phải chạy trên mọi máy tải về nên nhắm tới một instruction set baseline thận trọng.
CPU của bạn có thể hỗ trợ AVX2, AVX-512 hoặc NEON. `-DGGML_NATIVE=ON` cho phép compiler
dùng đúng instruction set tìm thấy trên máy.

Đây là thí nghiệm cần làm: **cùng source revision, cùng model, cùng runtime flag; chỉ
khác giả định của compiler.**

```bash
make build-llama       # clone + compile (5-15 min)
make compare-builds    # benchmark both binaries, write the report
```

`compare-builds.py` ghi bảng before/after và tỷ lệ speedup vào
`benchmarks/bonus-build-compare-tg128.md`. Tệp này cùng phần giải thích của bạn đáp ứng
B1 và cũng có thể đáp ứng B3.

B1 yêu cầu bạn **build từ mã nguồn và so sánh với prebuilt binary**. Chỉ chạy
`make build-llama` là chưa đủ. Bạn phải chạy thêm `make compare-builds`.

Laptop yếu hoặc chỉ có CPU thường hưởng lợi nhiều nhất. Prebuilt binary nhắm tới một
CPU baseline chung, còn `-DGGML_NATIVE=ON` nhắm đúng CPU của bạn.

---

## 1. `make build-llama` thực hiện gì

Target này clone llama.cpp ở build được cố định là `b10488`. Đây cũng là build của
prebuilt binary, nhờ đó phép so sánh công bằng. Source nằm trong `bonus/llama.cpp/`.
Sau đó target chạy:

```bash
cmake -B build $LLAMA_CMAKE_FLAGS -DGGML_NATIVE=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build -j --config Release
```

Điều kiện cần: **cmake** và C++ toolchain.

| Hệ điều hành | Cách cài đặt |
|---|---|
| macOS | `xcode-select --install && brew install cmake` |
| Ubuntu/Debian | `sudo apt install cmake build-essential` |
| Fedora | `sudo dnf install cmake gcc-c++` |
| Windows | Visual Studio Build Tools + cmake trong PATH |

## 2. Các backend flag

Truyền flag bổ sung qua `LLAMA_CMAKE_FLAGS`. Target luôn thêm
`-DGGML_NATIVE=ON` và `-DCMAKE_BUILD_TYPE=Release`.

### Chỉ dùng CPU — trường hợp đáng đo nhất cho bonus này

```bash
make build-llama          # nothing extra needed
```

`-DGGML_NATIVE=ON` tạo ra khác biệt. Đây thường là nơi khoảng cách với prebuilt binary
rõ nhất.

### Dùng NVIDIA CUDA

```bash
LLAMA_CMAKE_FLAGS="-DGGML_CUDA=ON" make build-llama
```

Cần CUDA Toolkit 12 trở lên. Kiểm tra bằng `nvcc --version`. Trên Linux, đây là cách
duy nhất để dùng CUDA vì llama.cpp **không phát hành prebuilt CUDA binary cho Linux**.
Sinh viên Linux có NVIDIA chạy prebuilt Vulkan trong core lab. Vì vậy, build với
`-DGGML_CUDA=ON` rồi chạy `make compare-builds` tạo ra phép so sánh Vulkan với CUDA và
đồng thời hoàn thành challenge **C6**.

### Dùng Apple Metal

```bash
LLAMA_CMAKE_FLAGS="-DGGML_METAL=ON" make build-llama
```

Metal đã được bật trong prebuilt macOS-arm64 binary. Vì vậy, khoảng cách có thể nhỏ.
Nếu có cải thiện, nó thường đến từ các đường chạy phía CPU như sampling và tokenization.
Kết quả gần bằng không vẫn hợp lệ nếu bạn giải thích nguyên nhân.

### Dùng AMD ROCm trên Linux

```bash
LLAMA_CMAKE_FLAGS="-DGGML_HIPBLAS=ON -DAMDGPU_TARGETS=gfx1100 \
  -DCMAKE_C_COMPILER=hipcc -DCMAKE_CXX_COMPILER=hipcc" make build-llama
```

Thay `gfx1100` bằng target của bạn. Kiểm tra bằng `rocminfo | grep gfx`. Các target
thường gặp gồm `gfx1030` cho RX 6800/6900, `gfx1100` cho RX 7900 và `gfx90a`/`gfx942`
cho Instinct.

### Dùng Vulkan

```bash
LLAMA_CMAKE_FLAGS="-DGGML_VULKAN=ON" make build-llama
```

Cần Vulkan SDK. Lệnh `vulkaninfo --summary` phải chạy được.

## 3. Các CPU flag khác đáng thử

| Flag | Tác dụng | Khi nên dùng |
|---|---|---|
| `-DGGML_NATIVE=ON` | Dùng instruction set thật của CPU | Luôn dùng; target tự thêm |
| `-DGGML_NATIVE=OFF` | Buộc dùng bản CPU baseline chung | Challenge C7, làm vế so sánh còn lại |
| `-DGGML_LTO=ON` | Link-time optimization | Chi phí thấp, đôi khi cải thiện vài phần trăm |
| `-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS` | Dùng BLAS ngoài cho prefill | Khi đã cài OpenBLAS/MKL; thường giúp `pp`, hiếm khi giúp `tg` |
| `-DCMAKE_BUILD_TYPE=Release` | `-O3 -DNDEBUG` | Luôn dùng; target tự thêm |

Không bao giờ so sánh một bản Debug với một bản Release rồi gọi chênh lệch đó là
speedup. `make build-llama` luôn truyền Release. Nếu build thủ công, bạn phải tự kiểm
tra điều này.

## 4. Kiểm tra bản build

```bash
./bonus/llama.cpp/build/bin/llama-cli --version
./bonus/llama.cpp/build/bin/llama-bench \
    -m models/gemma-4-E2B-it-UD-Q4_K_XL.gguf -t 4 -ngl 99
```

`labkit.runtime_bin()` tự tìm `bonus/llama.cpp/` sau khi build. Vì vậy, các lab script
sẽ dùng bản này. Riêng `compare-builds.py` không dùng cơ chế tự tìm; script cố định
từng phía để giữ phép so sánh trung thực.

## 5. Chạy server bằng bản build của bạn

```bash
./bonus/llama.cpp/build/bin/llama-server \
    -m models/gemma-4-E2B-it-UD-Q4_K_XL.gguf \
    --host 127.0.0.1 --port 8080 -t <best-from-make-tune> -ngl 99 \
    --parallel 4 --cont-batching --metrics
```

Sau đó chạy lại `make load-50 && make load-report` để kiểm tra mức cải thiện khi
compile có còn giữ được dưới concurrency hay không. Kết quả không phải lúc nào cũng
giữ nguyên. Việc giải thích nguyên nhân có giá trị hơn chỉ báo token/giây.

Mọi report được sinh dưới `benchmarks/` đều kết thúc bằng một section có đánh dấu
**"required -- replace this line"**. Hãy thay dòng đó bằng nhận xét của bạn. Nếu còn
sót, `make verify` sẽ fail.
