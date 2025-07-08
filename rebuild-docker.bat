@echo off

setlocal
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~dpnx0" %* && exit

set "SCRIPT_DIR=%~dp0"
set "BAT_FILE=%SCRIPT_DIR%rebuild-docker.bat"
set "COMPOSE_FILE=%SCRIPT_DIR%docker-compose.yml"
set "TASK_NAME=rebuild-docker-manager"
set "SCRIPT_DIR_app=D:\Rag_service\scripts\get_stats\"
set "SCRIPT_DIR_vdb=D:\Rag_service\scripts\VDB_Utils\"


cd /d %SCRIPT_DIR_app%
call "%SCRIPT_DIR_app%.venv\Scripts\activate"
python "%SCRIPT_DIR_app%app\app.py" --flag_last
call deactivate
cd /d %SCRIPT_DIR_vdb%
call "%SCRIPT_DIR_vdb%.venv\Scripts\activate"
python "%SCRIPT_DIR_vdb%update_vdb.py"
call deactivate
cd /d  %SCRIPT_DIR%
docker-compose -f %COMPOSE_FILE% down
docker-compose -f %COMPOSE_FILE% up -d --build
endlocal
exit