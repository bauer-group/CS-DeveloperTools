#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Configure Microsoft Defender exclusions for Docker Desktop, WSL2, and Android development.

.DESCRIPTION
    This script adds path and process exclusions to Microsoft Defender to improve
    performance for Docker Desktop, WSL2, and Android Emulator/Studio workloads.

    These exclusions reduce real-time scanning overhead for frequently accessed
    files and processes during development.

.NOTES
    File Name      : defender-exclusions.ps1
    Prerequisite   : Must be run as Administrator
    Version        : 1.0.0

.EXAMPLE
    .\defender-exclusions.ps1

    Applies all Docker, WSL2, and Android exclusions.

.LINK
    https://github.com/bauer-group/CS-DeveloperTools
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Applying Microsoft Defender exclusions..." -ForegroundColor Cyan

# -------------------------
# Helper functions
# -------------------------
function Add-DefenderPath {
    param([string]$Path)
    try {
        Add-MpPreference -ExclusionPath $Path -ErrorAction Stop
        Write-Host "  [OK] Path excluded: $Path" -ForegroundColor Green
    } catch {
        Write-Host "  [--] Path already excluded or skipped: $Path" -ForegroundColor DarkGray
    }
}

function Add-DefenderProcess {
    param([string]$Process)
    try {
        Add-MpPreference -ExclusionProcess $Process -ErrorAction Stop
        Write-Host "  [OK] Process excluded: $Process" -ForegroundColor Green
    } catch {
        Write-Host "  [--] Process already excluded or skipped: $Process" -ForegroundColor DarkGray
    }
}

# ============================================================
# 1. Docker Desktop + WSL2
# ============================================================

Write-Host "`n[Docker Desktop + WSL2]" -ForegroundColor Yellow

$dockerPaths = @(
    "C:\Program Files\Docker",
    "C:\ProgramData\Docker",
    "$env:USERPROFILE\.docker",
    "\\wsl$\docker-desktop",
    "\\wsl$\docker-desktop-data"
)

$dockerProcesses = @(
    "docker.exe",
    "docker-desktop.exe",
    "docker-compose.exe",
    "wsl.exe",
    "vmcompute.exe",
    "vmmem",
    "vmmemWSL"
)

foreach ($p in $dockerPaths)     { Add-DefenderPath $p }
foreach ($p in $dockerProcesses) { Add-DefenderProcess $p }

# ============================================================
# 2. Android Emulator / Android Studio
# ============================================================

Write-Host "`n[Android Emulator / Android Studio]" -ForegroundColor Yellow

$androidPaths = @(
    "C:\Program Files (x86)\Android",
    "$env:LOCALAPPDATA\Android\Sdk",
    "$env:USERPROFILE\.android",
    "$env:USERPROFILE\.gradle"
)

$androidProcesses = @(
    "emulator.exe",
    "qemu-system-x86_64.exe",
    "adb.exe",
    "studio64.exe",
    "java.exe",
    "kotlin-daemon.exe"
)

foreach ($p in $androidPaths)      { Add-DefenderPath $p }
foreach ($p in $androidProcesses)  { Add-DefenderProcess $p }

# ============================================================
# 3. Summary / Verification
# ============================================================

Write-Host "`n[Verification]" -ForegroundColor Cyan

Write-Host "`nExcluded Paths:" -ForegroundColor Gray
(Get-MpPreference).ExclusionPath | Sort-Object | ForEach-Object { Write-Host "  $_" }

Write-Host "`nExcluded Processes:" -ForegroundColor Gray
(Get-MpPreference).ExclusionProcess | Sort-Object | ForEach-Object { Write-Host "  $_" }

# ============================================================
# 4. Final instructions
# ============================================================

Write-Host "`nDone." -ForegroundColor Green
Write-Host @"

Recommended next steps:
  1. Restart Docker Desktop
  2. Run: wsl --shutdown
  3. Restart Android Studio / Emulator

"@ -ForegroundColor Green
