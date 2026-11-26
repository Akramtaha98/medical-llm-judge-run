#!/usr/bin/env bash
# One-time setup on the H200 server. Needs nvcc (CUDA toolkit) for the CUDA build.
set -euo pipefail
export PATH=$HOME/.local/bin:$PATH
rm -rf ~/venvs/medllm; uv venv ~/venvs/medllm --python 3.12 && source ~/venvs/medllm/bin/activate
# nvcc: set CUDA_HOME to a CUDA toolkit dir that contains bin/nvcc (find with: find / -name nvcc 2>/dev/null)
export CUDA_HOME=${CUDA_HOME:-/usr/local/cuda}; export PATH=$CUDA_HOME/bin:$PATH; export CUDACXX=$CUDA_HOME/bin/nvcc
CMAKE_ARGS="-DGGML_CUDA=on" uv pip install --no-cache llama-cpp-python==0.3.38 pandas numpy
uv pip freeze > data/models/h200_env_pip_freeze.txt
CUDA_VISIBLE_DEVICES=0 nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > data/models/h200_gpu.txt
python -c "import llama_cpp;print(llama_cpp.__version__)"
