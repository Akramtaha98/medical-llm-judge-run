#!/usr/bin/env bash
# Copy the three .gguf files into data/models/ (scp from the Mac, or download), then verify.
set -euo pipefail
cd data/models
sha256sum Meta-Llama-3-8B-Instruct-Q4_K_M.gguf qwen2.5-7b-instruct-q4_k_m-0000*-of-00002.gguf | tee /tmp/h200_hashes.txt
for h in $(awk '{print $1}' /tmp/h200_hashes.txt); do grep -q "$h" MODEL_SHA256.txt && echo "OK $h" || { echo "HASH MISMATCH $h"; exit 1; }; done
