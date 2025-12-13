# Windows PowerShell Test Suite for TinyTelemetry

####################################################
# This test file runs 3 test types:
# ---------------------------------
# 1) Baseline test
# 2) 5% Packet Loss (Batch=5)
# 3) Stress Test (Loss + Duplicates + Random Batch)
####################################################

$ErrorActionPreference = "Stop"

$SERVER_SCRIPT = "server_phase2.py"
$CLIENT_SCRIPT = "client_phase2.py"
$DURATION = 10

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "[*] TinyTelemetry Windows Automated Test Suite" -ForegroundColor Cyan
Write-Host "=============================================="

# Function to cleanly stop background server
function Stop-Server {
    param($proc)
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force
        Write-Host "Server stopped." -ForegroundColor Gray
    }
}

# ==========================================
# SCENARIO 1: BASELINE (Batch Size 1)
# ==========================================
Write-Host "`n[1] SCENARIO 1: Baseline (No Loss, Batch=1)" -ForegroundColor Yellow
Write-Host "---------------------------------------------"

# Start Server in background
$serverProc = Start-Process python -ArgumentList "$SERVER_SCRIPT" -PassThru -NoNewWindow
Start-Sleep -Seconds 2

# Run Client
python $CLIENT_SCRIPT --interval 0.5 --duration $DURATION --batch_size 1

Write-Host "[OK] Scenario 1 Complete." -ForegroundColor Green
Stop-Server $serverProc
Start-Sleep -Seconds 1

# ==========================================
# SCENARIO 2: PACKET LOSS (Batch Size 5)
# ==========================================
Write-Host "`n[2] SCENARIO 2: 5% Packet Loss (Batch=5)" -ForegroundColor Yellow
Write-Host "------------------------------------------"
Write-Host "[!] Using Internal Python Simulation for Loss..." -ForegroundColor Magenta

# Start Server with 5% simulated loss
$serverProc = Start-Process python -ArgumentList "$SERVER_SCRIPT", "--simulate_loss", "0.05" -PassThru -NoNewWindow
Start-Sleep -Seconds 2

# Run Client (Wait 5 readings per batch)
python $CLIENT_SCRIPT --interval 0.2 --duration $DURATION --batch_size 5

Write-Host "[OK] Scenario 2 Complete." -ForegroundColor Green
Stop-Server $serverProc
Start-Sleep -Seconds 1

# ==========================================
# SCENARIO 3: STRESS MIX (Loss + Dups)
# ==========================================
Write-Host "`n[3] SCENARIO 3: Stress Test (Loss + Duplicates + Random Batch)" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------"

# Start Server with 5% loss
$serverProc = Start-Process python -ArgumentList "$SERVER_SCRIPT", "--simulate_loss", "0.05" -PassThru -NoNewWindow
Start-Sleep -Seconds 2

# Run Client with Duplicates and Random Batching
python $CLIENT_SCRIPT --interval 0.2 --duration $DURATION --batch_size 5 --random_batch --simulate_dups 0.1

Write-Host "[OK] Scenario 3 Complete." -ForegroundColor Green
Stop-Server $serverProc

Write-Host "`n[DONE] All Tests Finished!" -ForegroundColor Cyan