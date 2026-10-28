@echo off
rem ------------------------------------------------------------
rem Telegram Account‑Selling Bot – quick start script
rem ------------------------------------------------------------
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

rem ---- 1. Create virtual environment if it does not exist ----
if not exist venv (
    echo Creating virtual environment... 
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

rem ---- 2. Activate venv ----
call venv\Scripts\activate

rem ---- 3. Upgrade pip and install requirements ----
python -m pip install --upgrade pip
if exist requirements.txt (
    echo Installing dependencies from requirements.txt ...
    pip install -r requirements.txt
) else (
    echo requirements.txt not found – installing minimal deps...
    pip install aiogram requests
)

rem ---- 4. Run the bot ----
echo Starting the Telegram bot...
python main.py

rem ---- 5. Deactivate venv after exit ----
deactivate
