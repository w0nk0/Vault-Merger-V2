# Installation Instructions

## Prerequisites

- Python 3.12 (required for prebuilt CUDA wheels)
- NVIDIA GPU with CUDA support
- UV package manager

## Quick Setup

1. **Install Python 3.12 via UV:**
```bash
uv python install 3.12
```

2. **Create virtual environment:**
```bash
cd ocr_project
uv venv --python 3.12 .venv
uv sync
```

3. **Install llama-cpp-python with CUDA support:**
```bash
uv pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

## Verify GPU Support

Test that GPU is being used:
```bash
uv run python -c "
from llama_cpp import Llama
l = Llama(
    model_path='path/to/model.gguf',
    n_gpu_layers=-1,
    verbose=True
)
" | grep CUDA
```

You should see `using device CUDA0` in the output.

## CUDA Wheel Versions

If the cu121 wheel doesn't work, try other CUDA versions:
- `cu124` for CUDA 12.4
- `cu118` for CUDA 11.8

Change the URL accordingly:
```bash
uv pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124
```

