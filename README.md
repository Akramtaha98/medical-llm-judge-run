# Run package for the frozen judge matrix (H200)
Contains only code, data/items.csv (MedQuAD text, no labels), FREEZE.json and model hashes. No gold labels or reviewer data.
1. `./setup_h200.sh`  2. place the 3 .gguf files in data/models/, `./get_models.sh`  3. `./run_h200.sh pilot` then `./run_h200.sh`
4. Verify: `sha256sum data/items.csv` = adbdfb0769717d28f0fc734025f9712ba8384f5ef20b5d4dfcc0cc84fdef2759
Return data/runs_h200/*, logs/, data/models/h200_*.txt to the Mac.
