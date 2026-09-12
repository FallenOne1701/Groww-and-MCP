# Register Windows Task Scheduler job: Monday 08:00 → weekly_job --once
# Uses the current user's account (no admin). Machine clock should be IST
# (Settings → Time → India Standard Time) so 08:00 is 08:00 IST.
param(
    [string]$TaskName = "GrowwWeeklyReviewPulse",
    [string]$RepoRoot = "",
    [int]$Hour = 8,
    [ValidateSet("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]
    [string]$Day = "Monday",
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task '$TaskName'."
    exit 0
}

$python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing venv Python at $python. Create .venv and pip install -r requirements.txt first."
}

$envFile = Join-Path $RepoRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Warning "No .env at $envFile — live Docs/Gmail will fail. Copy .env.example and fill secrets on this machine only."
}

$argument = "-m src.agent.weekly_job --once --mode heuristic"
$action = New-ScheduledTaskAction -Execute $python -Argument $argument -WorkingDirectory $RepoRoot
$at = Get-Date -Hour $Hour -Minute 0 -Second 0
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Groww weekly pulse: fetch Play reviews, classify, append Google Doc, Gmail draft (IST Monday 08:00 when the PC clock is IST)." `
    -Force | Out-Null

Write-Host "Registered '$TaskName'."
Write-Host "  Program : $python"
Write-Host "  Args    : $argument"
Write-Host "  Start in: $RepoRoot"
Write-Host "  When    : $Day ${Hour}:00 (local time — set Windows TZ to India Standard Time)"
Write-Host "Verify: Get-ScheduledTask -TaskName $TaskName"
Write-Host "Run now: Start-ScheduledTask -TaskName $TaskName"
