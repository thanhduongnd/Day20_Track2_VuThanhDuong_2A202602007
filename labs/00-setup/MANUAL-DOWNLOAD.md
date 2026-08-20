# Tải model thủ công

Dùng trang này khi `make setup` không tải được model (mạng trường chặn Hugging Face,
captive portal, mạng quá chậm).

## Chọn model trước

Lab có hai option — tải đúng bộ của model bạn chọn (xem [GUIDE.md](../../GUIDE.md) Bước 0.2):

| `LAB_MODEL=` | Model | Tổng tải |
|---|---|--:|
| `gemma4-e2b` *(mặc định)* | Gemma 4 E2B | ~5.2 GB |
| `qwen35-0.8b` | Qwen3.5 0.8B | ~0.9 GB |

## Option A — Gemma 4 E2B (mặc định)

**[unsloth/gemma-4-E2B-it-GGUF](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF)**
— Apache-2.0, **không gated**: không cần login, không cần token, không cần accept license.

Xem toàn bộ file: **[tree/main](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/tree/main)**

| Vai trò | File | Size |
|---|---|--:|
| primary (bắt buộc) | `gemma-4-E2B-it-UD-Q4_K_XL.gguf` | 2.97 GB |
| compare (bắt buộc) | `gemma-4-E2B-it-UD-Q2_K_XL.gguf` | 2.24 GB |
| bonus C1 (optional) | `mtp-gemma-4-E2B-it.gguf` | 0.09 GB |

Bạn cần **hai file đầu**. Thiếu file `compare` thì mất hàng thứ hai của rubric 3–5.

## Option B — Qwen3.5 0.8B (nhỏ, ~0.9 GB)

**[unsloth/Qwen3.5-0.8B-GGUF](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF)** — Apache-2.0, không gated.
Xem file: [tree/main](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/tree/main)

| Vai trò | File | Size |
|---|---|--:|
| primary | `Qwen3.5-0.8B-Q4_K_M.gguf` | 0.50 GB |
| compare | `Qwen3.5-0.8B-UD-Q2_K_XL.gguf` | 0.39 GB |

```bash
mkdir -p models
curl -L -o models/Qwen3.5-0.8B-Q4_K_M.gguf \
  https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/resolve/main/Qwen3.5-0.8B-Q4_K_M.gguf
curl -L -o models/Qwen3.5-0.8B-UD-Q2_K_XL.gguf \
  https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/resolve/main/Qwen3.5-0.8B-UD-Q2_K_XL.gguf
```

Rồi ghi manifest với **cùng** `LAB_MODEL` bạn dùng:

```bash
LAB_MODEL=qwen35-0.8b .venv/bin/python labs/00-setup/download-model.py --skip-download
```

---

## Cách 1 — curl / wget (cho Gemma 4 E2B)

Chạy ở **repo root**:

```bash
mkdir -p models

curl -L -o models/gemma-4-E2B-it-UD-Q4_K_XL.gguf \
  https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-UD-Q4_K_XL.gguf

curl -L -o models/gemma-4-E2B-it-UD-Q2_K_XL.gguf \
  https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-UD-Q2_K_XL.gguf
```

`-L` là bắt buộc — Hugging Face redirect sang CDN. Nếu bị ngắt giữa đường, thêm `-C -`
để tiếp tục thay vì tải lại từ đầu:

```bash
curl -L -C - -o models/gemma-4-E2B-it-UD-Q4_K_XL.gguf \
  https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-UD-Q4_K_XL.gguf
```

Windows PowerShell:

```powershell
mkdir models -Force
curl.exe -L -o models\gemma-4-E2B-it-UD-Q4_K_XL.gguf `
  https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-UD-Q4_K_XL.gguf
curl.exe -L -o models\gemma-4-E2B-it-UD-Q2_K_XL.gguf `
  https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-UD-Q2_K_XL.gguf
```

## Cách 2 — mirror (khi Hugging Face bị chặn hẳn)

`hf-mirror.com` dùng **đúng đường dẫn**, chỉ đổi hostname:

```bash
curl -L -o models/gemma-4-E2B-it-UD-Q4_K_XL.gguf \
  https://hf-mirror.com/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-UD-Q4_K_XL.gguf
```

Hoặc set biến môi trường rồi để script tự tải như bình thường:

```bash
HF_ENDPOINT=https://hf-mirror.com make setup
```

## Cách 3 — browser

Mở [tree/main](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/tree/main), bấm icon ⬇
cạnh hai file, rồi copy chúng vào `models/` trong repo. Thư mục con thoải mái — script
tìm đệ quy.

## Sau khi có file: ghi manifest

```bash
.venv/bin/python labs/00-setup/download-model.py --skip-download                    # Gemma
LAB_MODEL=qwen35-0.8b .venv/bin/python labs/00-setup/download-model.py --skip-download   # Qwen
```

Lệnh này không tải gì, chỉ tìm file và ghi `models/active.json` (rubric item 2). Thêm
`--with-mtp` nếu bạn cũng tải MTP head.

Kiểm tra:

```bash
make verify      # mục "Model manifest" phải PASS
```

## Kiểm tra file có nguyên vẹn không

Nếu server báo lỗi lạ khi load model, khả năng cao file bị tải thiếu. So size:

```bash
ls -l models/*.gguf
```

Phải khớp bảng của model bạn chọn (Gemma: 2.97 + 2.24 GB · Qwen: 0.50 + 0.39 GB).
File nhỏ hơn đáng kể = tải dở, xoá và tải lại.

## Nếu tên file không khớp

`--skip-download` tìm đúng tên trong bảng trên. Unsloth đôi khi re-upload với nhãn quant
khác. Khi đó: đổi tên file cho khớp, **hoặc** sửa tuple `primary` / `compare` trong dict `MODELS` ở
[`lib/labkit.py`](../../lib/labkit.py) và ghi lại việc đó trong REFLECTION §1.

## Runtime binary cũng bị chặn?

`fetch-runtime.py` tải từ GitHub Releases, thường thông khi Hugging Face bị chặn. Nếu cả
GitHub cũng bị chặn:

```bash
.venv/bin/python labs/00-setup/fetch-runtime.py --list      # in ra tên các asset
```

Tải asset đúng platform của bạn từ
<https://github.com/ggml-org/llama.cpp/releases/tag/b10488> rồi giải nén vào
`runtime/b10488/`. Layout bên trong không quan trọng — lab tìm binary bằng glob.

## Vẫn không được?

Máy dưới 8 GB RAM: thử `LAB_MODEL=qwen35-0.8b` trước — chỉ ~0.9 GB.
Dưới 4 GB RAM hoặc mạng không thông: dùng [`cloud/`](../../cloud/README.md)
(Colab / Kaggle). Điểm không bị ảnh hưởng, chỉ cần khai báo ở REFLECTION §1.
