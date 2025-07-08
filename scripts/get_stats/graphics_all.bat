@echo off

setlocal
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~dpnx0" %* && exit

set "SCRIPT_DIR=%~dp0"
set "BAT_FILE=%SCRIPT_DIR%graphics_all.bat"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "REQUIREMENTS=%SCRIPT_DIR%requirements.txt"
set "TASK_NAME=Auto logger"
set "LOCK_FILE=%SCRIPT_DIR%\.venv\.setup_complete"

if not exist "%LOCK_FILE%" (
    mkdir "%SCRIPT_DIR%logs"
    mkdir "%SCRIPT_DIR%metrics"
    if not exist "%VENV_DIR%" (
        python -m venv "%VENV_DIR%"
    )
    if exist "%REQUIREMENTS%" (
        call "%VENV_DIR%\Scripts\activate.bat"
        pip install -r "%REQUIREMENTS%"
        python.exe -m pip install --upgrade pip
    ) else (
        echo [ERROR] File requirements.txt not found
        pause
        exit
    )
    echo. > "%LOCK_FILE%"
    pause
    exit 
)

cd /d "%SCRIPT_DIR%"
call "%VENV_DIR%\Scripts\activate.bat"
python "%SCRIPT_DIR%app\app.py"

if %errorlevel% neq 0 (
    pause
)
endlocal
exit