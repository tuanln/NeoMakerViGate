# Qwen 2.5-VL Local Setup

Hướng dẫn cài Qwen 2.5-VL-2B local cho caption tiếng Việt trong exp06 Photo Booth.

## 1. Cài llama-cpp-python

```bash
.venv/bin/pip install llama-cpp-python
```

Trên Mac M4: dùng OpenBLAS hoặc Metal backend tuỳ chọn — default CPU OK cho 2B model.

Trên ARM64 NEO One: pin trong `requirements-arm64.txt`. Có thể cần compile từ source — xem llama-cpp-python README cho ARM build flags.

## 2. Download model

```bash
.venv/bin/python -m neo_makervigate.scripts.download_qwen
```

Files (~1.5GB) sẽ lưu tại `~/makervigate/models/qwen/`:
- `qwen2.5-vl-2b-instruct-q4_k_m.gguf` (~1.1GB) — quantized weights
- `qwen2.5-vl-2b-instruct-mmproj-f16.gguf` (~400MB) — vision projector

Nguồn: `bartowski/Qwen2.5-VL-2B-Instruct-GGUF` trên HuggingFace.

## 3. Verify

```bash
.venv/bin/python -c "
from pathlib import Path
from neo_makervigate.core.qwen_client import QwenLocalBackend
b = QwenLocalBackend()
print('Ready:', b.is_ready())
from PIL import Image
test_img = Path('/tmp/test_qwen.jpg')
Image.new('RGB', (200, 200), color='red').save(test_img)
print(b.describe_image(test_img, 'Mô tả ảnh trong 1 câu, có emoji.', max_tokens=50))
"
```

Expected: caption tiếng Việt 1 câu, < 10s trên Mac M4.

## 4. Fallback

Nếu model không có hoặc Qwen fail:
- exp06 sẽ dùng caption template từ `experiences/exp06_photo_booth/prompts.toml`
- Mỗi background có 1 template fallback caption
- User vẫn có thể chơi Photo Booth, chỉ là caption không personalized

## 5. Disk space

Model files: 1.5GB. Có thể xoá khi không cần:

```bash
rm -rf ~/makervigate/models/qwen/
```

Sau đó exp06 tự fallback template caption.
