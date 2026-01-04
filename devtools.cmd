@echo off
:: =============================================================================
:: DevTools - Swiss Army Knife for Git-based Development
:: Runtime Container for Git operations and development tools
:: =============================================================================

set "SCRIPT_DIR=%~dp0"
set "IMAGE_NAME=bauer-devtools"
set "CONTAINER_NAME=devtools-runtime"

:: Get command
set "CMD=%1"
if "%CMD%"=="" set "CMD=help"

:: Route commands
if /i "%CMD%"=="shell" goto shell
if /i "%CMD%"=="build" goto build
if /i "%CMD%"=="run" goto run
if /i "%CMD%"=="stats" goto stats
if /i "%CMD%"=="cleanup" goto cleanup
if /i "%CMD%"=="changelog" goto script
if /i "%CMD%"=="release" goto script
if /i "%CMD%"=="lfs-migrate" goto script
if /i "%CMD%"=="lfs" goto script
if /i "%CMD%"=="history-clean" goto script
if /i "%CMD%"=="branch-rename" goto script
if /i "%CMD%"=="split-repo" goto script
if /i "%CMD%"=="rewrite-commits" goto script
if /i "%CMD%"=="gh-create" goto script
if /i "%CMD%"=="gh-topics" goto script
if /i "%CMD%"=="gh-archive" goto script
if /i "%CMD%"=="gh-workflow" goto script
if /i "%CMD%"=="gh-add-workflow" goto script
if /i "%CMD%"=="gh-clean-releases" goto script
if /i "%CMD%"=="gh-visibility" goto script
if /i "%CMD%"=="version" goto version
if /i "%CMD%"=="--version" goto version
if /i "%CMD%"=="-v" goto version
if /i "%CMD%"=="help" goto help
if /i "%CMD%"=="--help" goto help
if /i "%CMD%"=="-h" goto help
echo [ERROR] Unknown command: %CMD%
goto help

:: =============================================================================
:shell
:: =============================================================================
setlocal
set "P=%~2"
if "%P%"=="" set "P=%CD%"
pushd "%P%" 2>nul || goto shell_err
set "P=%CD%"
popd
:: Convert to short path (8.3) to avoid spaces
for %%i in ("%P%") do set "SHORT_P=%%~si"
call :check_docker || goto :eof
call :ensure_image || goto :eof
echo [INFO] Starting DevTools shell...
echo [INFO] Mounting: %P%
echo [DEBUG] Short path: %SHORT_P%
for /f "tokens=*" %%i in ('git config --global user.name 2^>nul') do set "GIT_NAME=%%i"
for /f "tokens=*" %%i in ('git config --global user.email 2^>nul') do set "GIT_EMAIL=%%i"
docker run -it --rm --name %CONTAINER_NAME% -v %SHORT_P%:/workspace -e "GIT_USER_NAME=%GIT_NAME%" -e "GIT_USER_EMAIL=%GIT_EMAIL%" -w /workspace %IMAGE_NAME%
endlocal
goto :eof

:shell_err
echo [ERROR] Directory not found: %P%
exit /b 1

:: =============================================================================
:build
:: =============================================================================
call :check_docker || goto :eof
echo [INFO] Building DevTools image...
docker build -t %IMAGE_NAME% "%SCRIPT_DIR%services\devtools" || goto build_err
echo [OK] Image built successfully
goto :eof

:build_err
echo [ERROR] Failed to build image
exit /b 1

:: =============================================================================
:run
:: =============================================================================
if "%~2"=="" goto run_err
call :check_docker || goto :eof
call :ensure_image || goto :eof
set "SCRIPT=%~2"
echo [INFO] Running: %SCRIPT% %3 %4 %5 %6
docker run --rm -v "%CD%:/workspace" -w /workspace %IMAGE_NAME% /bin/bash -lc "%SCRIPT% %~3 %~4 %~5 %~6"
goto :eof

:run_err
echo [ERROR] Script name required
exit /b 1

:: =============================================================================
:stats
:: =============================================================================
set "P=%~2"
if "%P%"=="" set "P=%CD%"
call :check_docker || goto :eof
call :ensure_image || goto :eof
docker run --rm -v "%P%:/workspace" -w /workspace %IMAGE_NAME% /bin/bash -lc "git-stats.sh"
goto :eof

:: =============================================================================
:cleanup
:: =============================================================================
set "P=%~2"
if "%P%"=="" set "P=%CD%"
call :check_docker || goto :eof
call :ensure_image || goto :eof
docker run --rm -v "%P%:/workspace" -w /workspace %IMAGE_NAME% /bin/bash -lc "git-cleanup.sh %~3 %~4 %~5"
goto :eof

:: =============================================================================
:script
:: =============================================================================
call :check_docker || goto :eof
call :ensure_image || goto :eof
set "S="
if /i "%CMD%"=="changelog" set "S=git-changelog.py"
if /i "%CMD%"=="release" set "S=git-release.py"
if /i "%CMD%"=="lfs-migrate" set "S=git-lfs-migrate.sh"
if /i "%CMD%"=="lfs" set "S=git-lfs-migrate.sh"
if /i "%CMD%"=="history-clean" set "S=git-history-clean.sh"
if /i "%CMD%"=="branch-rename" set "S=git-branch-rename.sh"
if /i "%CMD%"=="split-repo" set "S=git-split-repo.py"
if /i "%CMD%"=="rewrite-commits" set "S=git-rewrite-commits.py"
if /i "%CMD%"=="gh-create" set "S=gh-create-repo.sh"
if /i "%CMD%"=="gh-topics" set "S=gh-topic-manager.py"
if /i "%CMD%"=="gh-archive" set "S=gh-archive-repos.py"
if /i "%CMD%"=="gh-workflow" set "S=gh-trigger-workflow.sh"
if /i "%CMD%"=="gh-add-workflow" set "S=gh-add-workflow.py"
if /i "%CMD%"=="gh-clean-releases" set "S=gh-clean-releases.py"
if /i "%CMD%"=="gh-visibility" set "S=gh-visibility.py"
docker run --rm -v "%CD%:/workspace" -w /workspace %IMAGE_NAME% /bin/bash -lc "%S% %~2 %~3 %~4 %~5"
goto :eof

:: =============================================================================
:version
:: =============================================================================
echo DevTools v1.0.0
echo Swiss Army Knife for Git-based Development
echo.
echo Components:
echo   - DevTools Runtime Container (Git, Python, Shell)
echo   - Git Tools (stats, cleanup, changelog, release, lfs-migrate, etc.)
echo   - GitHub Tools (gh-create, gh-topics, gh-archive, gh-workflow, etc.)
goto :eof

:: =============================================================================
:help
:: =============================================================================
echo.
echo ======================================================================
echo               DevTools - Developer Swiss Army Knife
echo ======================================================================
echo.
echo Usage: devtools ^<command^> [options]
echo.
echo Commands:
echo   shell [PATH]          Start interactive shell (default: current dir)
echo   build                 Build/rebuild the container
echo   run ^<script^> [args]   Run a script in the container
echo   stats [PATH]          Show repository statistics
echo   cleanup [PATH]        Clean up branches and cache
echo   changelog [opts]      Generate changelog
echo   release [opts]        Manage releases
echo   lfs-migrate [opts]    Migrate to Git LFS
echo   history-clean [opts]  Remove large files from history
echo   branch-rename [opts]  Rename git branches
echo   split-repo [opts]     Split monorepo
echo   rewrite-commits       Rewrite commit messages
echo   gh-create [opts]      Create GitHub repository
echo   gh-topics [opts]      Manage repository topics
echo   gh-archive [opts]     Archive repositories
echo   gh-workflow [opts]    Trigger GitHub Actions
echo   gh-add-workflow       Add workflow files
echo   gh-clean-releases     Clean releases and tags
echo   gh-visibility [opts]  Change repo visibility
echo   help                  Show this help
echo   version               Show version
echo.
echo Examples:
echo   devtools shell
echo   devtools shell "C:\My Projects\App"
echo   devtools stats
echo   devtools build
echo.
goto :eof

:: =============================================================================
:: Helper functions
:: =============================================================================

:check_docker
docker info >nul 2>&1
if errorlevel 1 echo [ERROR] Docker is not running. Please start Docker Desktop first. & exit /b 1
goto :eof

:ensure_image
docker image inspect %IMAGE_NAME% >nul 2>&1
if errorlevel 1 call :build
goto :eof
