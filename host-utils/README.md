# Host Utilities

Scripts and tools that run directly on the Windows host system (not inside containers).

## Directory Structure

```
host-utils/
├── README.md           # This file
└── windows/            # Windows-specific utilities
    └── defender-exclusions.ps1
```

## Windows Utilities

### defender-exclusions.ps1

Configures Microsoft Defender exclusions for improved development performance.

**Purpose:**
- Reduces real-time scanning overhead for Docker Desktop, WSL2, and Android development
- Excludes frequently accessed paths and processes from antivirus scanning
- Significantly improves build times and emulator performance

**Excluded Components:**

| Category | Paths | Processes |
|----------|-------|-----------|
| Docker Desktop | `C:\Program Files\Docker`, `C:\ProgramData\Docker`, `%USERPROFILE%\.docker` | `docker.exe`, `docker-desktop.exe`, `docker-compose.exe` |
| WSL2 | `\\wsl$\docker-desktop`, `\\wsl$\docker-desktop-data` | `wsl.exe`, `vmcompute.exe`, `vmmem`, `vmmemWSL` |
| Android SDK | `C:\Program Files (x86)\Android`, `%LOCALAPPDATA%\Android\Sdk`, `%USERPROFILE%\.android` | `emulator.exe`, `qemu-system-x86_64.exe`, `adb.exe` |
| Android Studio | `%USERPROFILE%\.gradle` | `studio64.exe`, `java.exe`, `kotlin-daemon.exe` |

**Usage:**

```powershell
# Open PowerShell as Administrator
cd host-utils\windows
.\defender-exclusions.ps1
```

**Post-Execution Steps:**
1. Restart Docker Desktop
2. Run `wsl --shutdown` in PowerShell
3. Restart Android Studio / Emulator

**Verification:**
The script automatically displays all configured exclusions after execution.

To manually verify exclusions:
```powershell
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
Get-MpPreference | Select-Object -ExpandProperty ExclusionProcess
```

**Note:** This script requires Administrator privileges and will prompt for elevation if not already running elevated.
