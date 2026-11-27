#!/usr/bin/env bash
# Sensitivity analysis (reviewer request): run both judges on the 17 refusal-type Set A claims excluded at the gold stage.
# Same prompts, seeds, parser and settings as the primary run. Run on the Mac (Metal). Output: data/runs_excl17/
set -euo pipefail
cd "$(dirname "$0")"
M=data/models
LL=$M/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf
QW=$M/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
PY=${PY:-python3}
mkdir -p data/runs_excl17
for J in llama3_8b:$LL qwen25_7b:$QW; do
  $PY code/run_judges.py --judge "${J%%:*}" --model-path "${J#*:}" --items data/items_excluded17.csv --out data/runs_excl17/${J%%:*}_sampled
  $PY code/run_judges.py --judge "${J%%:*}" --model-path "${J#*:}" --items data/items_excluded17.csv --out data/runs_excl17/${J%%:*}_greedy --arm greedy
done
cat data/runs_excl17/llama3_8b_sampled data/runs_excl17/qwen25_7b_sampled > data/runs_excl17/sampled_all.jsonl
cat data/runs_excl17/llama3_8b_greedy data/runs_excl17/qwen25_7b_greedy > data/runs_excl17/greedy_all.jsonl
wc -l data/runs_excl17/*_all.jsonl   # expect 306 and 102
