$Py = "C:\Users\Thrish_Sudha\AppData\Local\Programs\Python\Python312\python.exe"
$LogDir = "run_logs"
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

function Run-Experiment {
    param(
        [string]$Dataset,
        [string]$ModeFlag,
        [string]$Tag
    )
    $LogFile = "$LogDir\${Dataset}_${Tag}.log"
    Write-Host "=== Starting $Dataset $Tag at $(Get-Date) ==="
    
    if ([string]::IsNullOrEmpty($ModeFlag)) {
        cmd.exe /c "`"$Py`" train_federated.py --dataset $Dataset --seed 2025 > `"$LogFile`" 2>&1"
    } else {
        cmd.exe /c "`"$Py`" train_federated.py --dataset $Dataset $ModeFlag --seed 2025 > `"$LogFile`" 2>&1"
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error running $Dataset $Tag. Check $LogFile"
        exit $LASTEXITCODE
    }
    Write-Host "=== Finished $Dataset $Tag at $(Get-Date) ==="
}

Run-Experiment "can_vtc" "" "fhe"
Run-Experiment "can_vtc" "--no-fhe" "nofhe"
Run-Experiment "car_hack" "" "fhe"
Run-Experiment "car_hack" "--no-fhe" "nofhe"
Run-Experiment "cicids" "" "fhe"
Run-Experiment "cicids" "--no-fhe" "nofhe"
Run-Experiment "veremi" "" "fhe"
Run-Experiment "veremi" "--no-fhe" "nofhe"

Write-Host "Running CKKS Benchmark..."
cmd.exe /c "`"$Py`" benchmark_real_ckks.py"

Write-Host "Building Comparison..."
cmd.exe /c "`"$Py`" build_comparison.py"

Write-Host "Copying results to dashboard folder..."
Copy-Item "checkpoints\federated_summary_*.json" -Destination "C:\Users\Thrish_Sudha\Desktop\Amrita Files\LGSI IOV\Claude's work\FHE_Comparison\results\" -Force
Copy-Item "checkpoints\real_ckks_benchmark.json" -Destination "C:\Users\Thrish_Sudha\Desktop\Amrita Files\LGSI IOV\Claude's work\FHE_Comparison\results\" -Force
Copy-Item "checkpoints\comparison_summary.json" -Destination "C:\Users\Thrish_Sudha\Desktop\Amrita Files\LGSI IOV\Claude's work\FHE_Comparison\results\" -Force

Write-Host "Changing directory to scripts..."
Set-Location "C:\Users\Thrish_Sudha\Desktop\Amrita Files\LGSI IOV\Claude's work\FHE_Comparison\scripts"

Write-Host "Generating Dashboard Data..."
cmd.exe /c "`"$Py`" generate_dashboard_data.py"

Write-Host "Building Dashboard..."
cmd.exe /c "`"$Py`" build_dashboard.py"

Write-Host "Building PPTX Slides..."
cmd.exe /c "`"$Py`" build_pptx_slides.py"

Write-Host "All scripts finished successfully at $(Get-Date)."
