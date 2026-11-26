#!/usr/bin/env bash
# Runs the 4 (judge x arm) jobs in parallel on the H200. Each job is resumable; rerun to resume.
set -euo pipefail
cd "$(dirname "$0")"; source ~/venvs/medllm/bin/activate
M=data/models; OUT=data/runs_h200; mkdir -p $OUT logs
LL=$M/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf; QW=$M/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
if [ "${1:-}" = "pilot" ]; then
  python3 code/run_judges.py --judge llama3_8b --model-path $LL --items data/items.csv --out /tmp/h200_pilot_l --limit 5; exit; fi
run(){ python3 code/run_judges.py --judge "$1" --model-path "$2" --items data/items.csv --out "$OUT/$1_$3" ${4:+--arm greedy} > logs/$1_$3.log 2>&1; }
run llama3_8b $LL sampled & run llama3_8b $LL greedy g & run qwen25_7b $QW sampled & run qwen25_7b $QW greedy g &
wait
cat $OUT/llama3_8b_sampled $OUT/qwen25_7b_sampled > $OUT/sampled_all.jsonl
cat $OUT/llama3_8b_greedy $OUT/qwen25_7b_greedy > $OUT/greedy_all.jsonl
wc -l $OUT/sampled_all.jsonl $OUT/greedy_all.jsonl   # expect 6840 and 2280
