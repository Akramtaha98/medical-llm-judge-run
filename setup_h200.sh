#!/usr/bin/env bash
# One-time setup on the H200 server. Needs nvcc (CUDA toolkit) for the CUDA build.
set -euo pipefail
python3 -m venv ~/venvs/medllm && source ~/venvs/medllm/bin/activate
CMAKE_ARGS="-DGGML_CUDA=on" pip install --no-cache-dir llama-cpp-python==0.3.38 pandas numpy
pip freeze > data/models/h200_env_pip_freeze.txt
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > data/models/h200_gpu.txt
python -c "import llama_cpp;print(llama_cpp.__version__)"
