# Installing llama-cpp-python with CUDA Support

Since you're using Python 3.13 and prebuilt wheels only support up to Python 3.12, you need to build from source with CUDA support.

## Step 1: Install CUDA Toolkit

**On Fedora/Nobara:**
```bash
sudo dnf install cuda-toolkit
# Or download from NVIDIA: https://developer.nvidia.com/cuda-downloads
```

**Verify CUDA installation:**
```bash
nvcc --version
# Should show CUDA version (e.g., 11.8, 12.x)
```

## Step 2: Set CUDA Environment Variables

Add to your `~/.bashrc` or run before installing:
```bash
export CUDA_HOME=/usr/local/cuda  # Adjust path if different
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
```

## Step 3: Install Build Dependencies

```bash
sudo dnf install cmake gcc-c++ python3-devel
```

## Step 4: Build llama-cpp-python with CUDA

From the `ocr_project` directory:
```bash
cd /home/nico/projects/EnEx2/ocr_project

CMAKE_ARGS="-DLLAMA_CUBLAS=on" uv pip install --no-cache-dir --force-reinstall llama-cpp-python
```

## Step 5: Verify GPU Support

```bash
uv run python -c "from llama_cpp import Llama; print('CUDA support:', hasattr(Llama, '_llama_cpp'))"
```

## Alternative: Use Python 3.12

If building fails, you can use Python 3.12 which has prebuilt CUDA wheels:

```bash
cd /home/nico/projects/EnEx2/ocr_project
uv venv --python 3.12 .venv
uv sync
uv pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

