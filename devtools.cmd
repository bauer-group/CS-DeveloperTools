@echo off
setlocal enabledelayedexpansion

:: =============================================================================
:: DevTools - Swiss Army Knife for Git-based Development
:: Runtime Container for Git operations and development tools
:: =============================================================================

set "SCRIPT_DIR=%~dp0"
set "IMAGE_NAME=bauer-devtools"
set "CONTAINER_NAME=devtools-runtime"

:: Parse command - save full argument for shell command
set "COMMAND=%~1"
set "ARG2=%~2"
if "%COMMAND%"=="" set "COMMAND=help"

:: Route to command
if /i "%COMMAND%"=="shell" call :cmd_shell "%ARG2%" & goto :eof
if /i "%COMMAND%"=="run" goto :cmd_run
if /i "%COMMAND%"=="build" goto :cmd_build
if /i "%COMMAND%"=="stats" goto :cmd_stats
if /i "%COMMAND%"=="cleanup" goto :cmd_cleanup
if /i "%COMMAND%"=="changelog" goto :cmd_changelog
if /i "%COMMAND%"=="release" goto :cmd_release
if /i "%COMMAND%"=="lfs-migrate" goto :cmd_lfs
if /i "%COMMAND%"=="lfs" goto :cmd_lfs
if /i "%COMMAND%"=="history-clean" goto :cmd_history
if /i "%COMMAND%"=="branch-rename" goto :cmd_branch
if /i "%COMMAND%"=="split-repo" goto :cmd_split
if /i "%COMMAND%"=="rewrite-commits" goto :cmd_rewrite
if /i "%COMMAND%"=="gh-create" goto :cmd_gh_create
if /i "%COMMAND%"=="gh-topics" goto :cmd_gh_topics
if /i "%COMMAND%"=="gh-archive" goto :cmd_gh_archive
if /i "%COMMAND%"=="gh-workflow" goto :cmd_gh_workflow
if /i "%COMMAND%"=="gh-add-workflow" goto :cmd_gh_addworkflow
if /i "%COMMAND%"=="gh-clean-releases" goto :cmd_gh_clean
if /i "%COMMAND%"=="gh-visibility" goto :cmd_gh_visibility
if /i "%COMMAND%"=="version" goto :cmd_version
if /i "%COMMAND%"=="--version" goto :cmd_version
if /i "%COMMAND%"=="-v" goto :cmd_version
if /i "%COMMAND%"=="help" goto :cmd_help
if /i "%COMMAND%"=="--help" goto :cmd_help
if /i "%COMMAND%"=="-h" goto :cmd_help

echo [ERROR] Unknown command: %COMMAND%
goto :cmd_help

:: =============================================================================
:: Commands
:: =============================================================================

:cmd_shell
:: Get path from first argument passed via call
set "PROJECT_PATH=%~1"
if "%PROJECT_PATH%"=="" set "PROJECT_PATH=%CD%"

:: Resolve to absolute path
pushd "%PROJECT_PATH%" 2>nul
if errorlevel 1 (
    echo [ERROR] Directory not found: %PROJECT_PATH%
    exit /b 1
)
set "PROJECT_PATH=%CD%"
popd

call :check_docker
call :ensure_image

echo [INFO] Starting DevTools shell...
echo [INFO] Mounting: %PROJECT_PATH%

:: Get git config
for /f "tokens=*" %%i in ('git config --global user.name 2^>nul') do set "GIT_NAME=%%i"
for /f "tokens=*" %%i in ('git config --global user.email 2^>nul') do set "GIT_EMAIL=%%i"

docker run -it --rm ^
    --name %CONTAINER_NAME% ^
    -v "%PROJECT_PATH%:/workspace" ^
    -e "GIT_USER_NAME=%GIT_NAME%" ^
    -e "GIT_USER_EMAIL=%GIT_EMAIL%" ^
    -e "PROJECT_PATH=/workspace" ^
    -w /workspace ^
    %IMAGE_NAME% /bin/bash -l
goto :eof

:cmd_run
if "%~2"=="" (
    echo [ERROR] Script name required
    exit /b 1
)
set "SCRIPT=%~2"
set "ARGS="
shift
shift
:run_args_loop
if "%~1"=="" goto :run_args_done
set "ARGS=%ARGS% %~1"
shift
goto :run_args_loop
:run_args_done

call :check_docker
call :ensure_image

echo [INFO] Running: %SCRIPT%%ARGS%
docker run --rm ^
    -v "%CD%:/workspace" ^
    -w /workspace ^
    %IMAGE_NAME% /bin/bash -lc "%SCRIPT%%ARGS%"
goto :eof

:cmd_build
call :check_docker
echo [INFO] Building DevTools image...
docker build -t %IMAGE_NAME% "%SCRIPT_DIR%services\devtools"
if errorlevel 1 (
    echo [ERROR] Failed to build image
    exit /b 1
)
echo [OK] Image built successfully
goto :eof

:cmd_stats
set "PROJECT_PATH=%~2"
if "%PROJECT_PATH%"=="" set "PROJECT_PATH=%CD%"
call :invoke_script "git-stats.sh" "%PROJECT_PATH%"
goto :eof

:cmd_cleanup
set "PROJECT_PATH=%~2"
if "%PROJECT_PATH%"=="" set "PROJECT_PATH=%CD%"
call :invoke_script "git-cleanup.sh" "%PROJECT_PATH%" %3 %4 %5
goto :eof

:cmd_changelog
call :invoke_script "git-changelog.py" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_release
call :invoke_script "git-release.py" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_lfs
call :invoke_script "git-lfs-migrate.sh" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_history
call :invoke_script "git-history-clean.sh" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_branch
call :invoke_script "git-branch-rename.sh" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_split
call :invoke_script "git-split-repo.py" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_rewrite
call :invoke_script "git-rewrite-commits.py" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_gh_create
call :invoke_script "gh-create-repo.sh" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_gh_topics
call :invoke_script "gh-topic-manager.py" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_gh_archive
call :invoke_script "gh-archive-repos.py" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_gh_workflow
call :invoke_script "gh-trigger-workflow.sh" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_gh_addworkflow
call :invoke_script "gh-add-workflow.py" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_gh_clean
call :invoke_script "gh-clean-releases.py" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_gh_visibility
call :invoke_script "gh-visibility.py" "%CD%" %2 %3 %4 %5
goto :eof

:cmd_version
echo DevTools v1.0.0
echo Swiss Army Knife for Git-based Development
echo.
echo Components:
echo   - DevTools Runtime Container (Git, Python, Shell)
echo   - Git Tools (stats, cleanup, changelog, release, lfs-migrate, history-clean, branch-rename, split-repo, rewrite-commits)
echo   - GitHub Tools (gh-create, gh-topics, gh-archive, gh-workflow, gh-add-workflow, gh-clean-releases, gh-visibility)
goto :eof

:cmd_help
echo.
echo ======================================================================
echo               DevTools - Developer Swiss Army Knife
echo ======================================================================
echo.
echo Usage:
echo   devtools ^<command^> [options]
echo.
echo Commands:
echo.
echo   Runtime Container:
echo     shell [PROJECT_PATH]    Start interactive shell in DevTools container
echo     run ^<script^> [args]     Run a script in the container
echo     build                   Build/rebuild the DevTools container
echo.
echo   Git Tools (via container):
echo     stats [PROJECT_PATH]    Show repository statistics
echo     cleanup [PROJECT_PATH]  Clean up branches and cache
echo     changelog [options]     Generate changelog
echo     release [options]       Manage releases
echo     lfs-migrate [options]   Migrate repository to Git LFS
echo     history-clean [opts]    Remove large files from git history
echo     branch-rename [opts]    Rename git branches (local + remote)
echo     split-repo [options]    Split monorepo into separate repos
echo     rewrite-commits [opts]  Rewrite commit messages (pattern-based)
echo.
echo   GitHub Tools (via container):
echo     gh-create [options]     Create GitHub repository
echo     gh-topics [options]     Manage repository topics
echo     gh-archive [options]    Archive repositories
echo     gh-workflow [options]   Trigger GitHub Actions workflows
echo     gh-add-workflow [opts]  Add workflow files to repos
echo     gh-clean-releases       Clean releases and tags
echo     gh-visibility [opts]    Change repo visibility (public/private)
echo.
echo   General:
echo     help                    Show this help
echo     version                 Show version info
echo.
echo Examples:
echo   devtools shell                          # Shell in current directory
echo   devtools shell C:\Projects\MyApp        # Shell in other project
echo   devtools stats                          # Repository statistics
echo   devtools run git-cleanup.sh --dry-run   # Run script
echo.
goto :eof

:: =============================================================================
:: Helper Functions
:: =============================================================================

:check_docker
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    exit /b 1
)
goto :eof

:ensure_image
docker image inspect %IMAGE_NAME% >nul 2>&1
if errorlevel 1 (
    echo [INFO] Building DevTools container...
    call :cmd_build
)
goto :eof

:invoke_script
set "SCRIPT_NAME=%~1"
set "WORK_PATH=%~2"
set "EXTRA_ARGS=%~3 %~4 %~5 %~6"

call :check_docker
call :ensure_image

docker run --rm ^
    -v "%WORK_PATH%:/workspace" ^
    -w /workspace ^
    %IMAGE_NAME% /bin/bash -lc "%SCRIPT_NAME% %EXTRA_ARGS%"
goto :eof
