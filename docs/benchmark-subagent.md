# Representative subagent benchmark

Issue #4 compares the existing generation-throughput tuning objective with the latency of a representative repository task. The tuning rule must not change until target-PC measurements show a repeatable end-to-end improvement.

## Fixed comparison conditions

For one comparison set, every candidate must use:

- the same clean Git commit;
- the versioned task in `benchmarks/representative-task.txt`;
- the same model, llama.cpp build, context/KV settings, CPU, and GPU;
- at least 3 repetitions per `n_cpu_moe` candidate.

`benchmark-subagent.py` refuses a dirty workspace and records the commit and task SHA-256 so candidate results can be checked for comparability.

## Measurement procedure

For each candidate, first stop the model server and collect prompt/generation throughput. Example for `n_cpu_moe=48`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\benchmark-model.ps1 `
  -NCpuMoe 48 `
  -Repetitions 3 `
  -OutputPath .\.local\throughput-48.json
```

Then start the model with the same candidate in terminal A:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-model.ps1 `
  -NCpuMoe 48 `
  -TuneIfMissing $false
```

Run the representative agent workload in terminal B:

```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark-subagent.py `
  --n-cpu-moe 48 `
  --throughput-json .\.local\throughput-48.json `
  --repetitions 3
```

Repeat the same sequence for each candidate being compared. Results are written to `.local/qwen-subagent-<n_cpu_moe>.json` and remain outside Git.

Each result records:

- end-to-end latency for every run plus mean/median;
- prompt tokens/sec from `benchmark-model.ps1`;
- generation tokens/sec from `benchmark-model.ps1`;
- agent rounds for every run plus mean;
- selected `n_cpu_moe`;
- repository commit, task hash, llama.cpp build, CPU, and GPU metadata.

## Decision rule

The current `tune-model.ps1` policy remains generation-only. Compare its selected candidate with the candidate that minimizes representative-workload median end-to-end latency under identical conditions. Change the tuning objective only when at least 3 repeated runs per candidate show a repeatable end-to-end improvement without changing the benchmark snapshot or task.
