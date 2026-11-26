# Protocol freeze record

Frozen: 2026-11-26. Judge outputs on test claims seen before freeze: none (only the 20 unlabelled development draft claims, Amendment 3).

Frozen inputs (hashes in data/FREEZE.json): code (prompts, parser, judge runner, analysis, label tools), data/items.csv (380 claims; sha256 adbdfb0769717d28f0fc734025f9712ba8384f5ef20b5d4dfcc0cc84fdef2759), gold.csv, gold_excluded.csv, claims_A.csv, claims_B.csv, refusal_excluded.csv, selected.csv (sha256 c75d52a9...1a49), Set A answers, model files (data/models/MODEL_SHA256.txt) and protocol_amendments.md (Amendments 1 to 5).

Judge matrix: 2 judges x 3 prompts x 3 seeds (17, 29, 43), temperature 0.3, top-p 0.9, max 8 tokens, context 4096, stop at first newline: 380 x 18 = 6,840 calls. Greedy arm (Amendment 5): 380 x 6 = 2,280 calls. Total 9,120.

Rules after freeze: no change to prompts, parser, settings, gold or items. Any deviation is logged as a new amendment with the real date. Retries of technical interruptions use the identical key and settings.

Run commands (repo root):
1. python code/run_judges.py --judge llama3_8b --model-path data/models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf --items data/items.csv --out data/runs/llama3_sampled.jsonl
2. python code/run_judges.py --judge qwen25_7b --model-path data/models/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf --items data/items.csv --out data/runs/qwen25_sampled.jsonl
3. Same two with --arm greedy and separate output files; replay once on the test claims.
4. python code/analysis.py --gold data/labels/gold.csv --runs <runs> --greedy <greedy runs> --out results.json
