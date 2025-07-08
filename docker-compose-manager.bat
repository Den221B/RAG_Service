@echo off

setlocal
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~dpnx0" %* && exit
set "SCRIPT_DIR=%~dp0"
set "BAT_FILE=%SCRIPT_DIR%docker-compose-manager.bat"
set "COMPOSE_FILE=%SCRIPT_DIR%docker-compose.yml"
set "TASK_NAME=docker-compose-manager"

docker version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not running or is not installed!
    pause
    exit 
)

docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" ps | find "Up" >nul
if %ERRORLEVEL% equ 0 (
    echo Containers are already running.
) else (
    echo Launching docker-compose...
    docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" up -d
)

echo We check the status of the services...
docker-compose -f "%COMPOSE_FILE%" -p "%PROJECT_NAME%" ps
endlocal
exit