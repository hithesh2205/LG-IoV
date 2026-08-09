#!/bin/bash
set -x
PY="/c/Users/Thrish_Sudha/AppData/Local/Programs/Python/Python312/python.exe"
LOG_DIR="run_logs"
mkdir -p "$LOG_DIR"

run() {
  local dataset=$1
  local mode_flag=$2
  local tag=$3
  echo "=== Starting $dataset $tag at $(date) ==="
  "$PY" train_federated.py --dataset "$dataset" $mode_flag --seed 2025 > "$LOG_DIR/${dataset}_${tag}.log" 2>&1
  echo "=== Finished $dataset $tag at $(date) with exit code $? ==="
}

run can_vtc "" fhe
run car_hack "" fhe
run car_hack "--no-fhe" nofhe
run cicids "" fhe
run cicids "--no-fhe" nofhe
run veremi "" fhe
run veremi "--no-fhe" nofhe

echo "=== ALL RUNS COMPLETE at $(date) ==="
