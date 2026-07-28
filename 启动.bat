@echo off
chcp 65001 >nul
cls
echo ========================================
echo   Tie Ban Shen Shu Calculator
echo ========================================
echo.
echo Please select:
echo   1. Web Version (Recommended)
echo   2. Console Version
echo   3. Install Dependencies
echo   0. Exit
echo.
set /p choice=Enter option [0-3]:

if "%choice%"=="1" goto web
if "%choice%"=="2" goto console
if "%choice%"=="3" goto install
if "%choice%"=="0" goto end
goto invalid

:web
echo.
echo Starting Web version...
echo.
echo ========================================
echo   Tie Ban Shen Shu Calculator - Web
echo ========================================
echo.
echo Starting web server...
echo.
echo Server URL: http://localhost:8000
echo.
echo Open your browser and visit the URL above
echo.
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo.
python server.py
echo.
echo Server stopped
pause
goto end

:console
echo.
echo Starting Console version...
echo.
echo ========================================
echo   Tie Ban Shen Shu Calculator
echo ========================================
echo.
python main.py
echo.
echo Program ended
pause
goto end

:install
echo.
echo Installing dependencies...
echo.
echo ========================================
echo   Tie Ban Shen Shu - Install
echo ========================================
echo.
echo [1/2] Checking Python environment...
python --version >nul 2>&1
if %%errorlevel%% neq 0 (
    echo Error: Python not found, please install Python 3.6 or higher
    pause
    goto end
)
echo Python check passed
echo.
echo [2/2] Installing dependencies...
echo Installing from local directory...
pip install --no-index --find-links=lib/packages -r requirements.txt
if %%errorlevel%% neq 0 (
    echo.
    echo Error: Installation failed, trying from network...
    pip install -r requirements.txt
    if %%errorlevel%% neq 0 (
        echo Error: Installation failed, please check network connection
        pause
        goto end
    )
)
echo.
echo ========================================
echo Dependencies installed successfully!
echo ========================================
echo.
pause
goto end

:invalid
echo.
echo Invalid option, please run again
pause

:end
