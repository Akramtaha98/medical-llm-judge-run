#!/usr/bin/env bash
# Run on the Mac (Metal), not in the Linux VM. Usage: ./run_pilot_and_full.sh pilot|full
set -euo pipefail
cd "$(dirname "$0")"
M=data/models
LL=$M/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf
QW=$M/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
if [ "${1:-}" = "pilot" ]; then
  mkdir -p /tmp/pilot
  for J in llama3_8b:$LL qwen25_7b:$QW; do
    python3 code/run_judges.py --judge "${J%%:*}" --model-path "${J#*:}" --items data/items.csv --out /tmp/pilot/${J%%:*}_s --limit 5
  done
  python3 code/run_judges.py --judge llama3_8b --model-path $LL --items data/items.csv --out /tmp/pilot/llama3_8b_g --limit 5 --arm greedy
  echo "Pilot done: check latency_s in /tmp/pilot/*"
else
  mkdir -p data/runs
  for J in llama3_8b:$LL qwen25_7b:$QW; do
    python3 code/run_judges.py --judge "${J%%:*}" --model-path "${J#*:}" --items data/items.csv --out data/runs/${J%%:*}_sampled
    python3 code/run_judges.py --judge "${J%%:*}" --model-path "${J#*:}" --items data/items.csv --out data/runs/${J%%:*}_greedy --arm greedy
  done
  cat data/runs/llama3_8b_sampled data/runs/qwen25_7b_sampled > data/runs/sampled_all.jsonl
  cat data/runs/llama3_8b_greedy data/runs/qwen25_7b_greedy > data/runs/greedy_all.jsonl
  wc -l data/runs/sampled_all.jsonl data/runs/greedy_all.jsonl   # expect 6840 and 2280
fi
