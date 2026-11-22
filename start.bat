@echo off
rem Everyday menu. Double-click to run.
chcp 65001 >nul
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
    echo  Run setup.bat first.
    pause
    exit /b 1
)
set PY=venv\Scripts\python make_video.py

:menu
cls
echo.
echo   AI Video Factory
echo   ================
echo   1. Make the next video  (posted automatically if auto-upload is on)
echo   2. Make a topic by number
echo   3. Show the topic list
echo   4. Preview a topic (one picture per scene, fast)
echo   5. Upload finished videos that are not posted yet
echo   6. History: every video and where it was posted
echo   7. Check setup
echo   8. Setup / change settings / connect accounts
echo   0. Exit
echo.
set "choice="
set /p choice=  Choose a number:
if "%choice%"=="1" %PY% --next
if "%choice%"=="2" (
    set "num="
    set /p num=  Topic number - e.g. 17 or 17-20:
    call %PY% --only %%num%%
)
if "%choice%"=="3" %PY% --list
if "%choice%"=="4" (
    set "num="
    set /p num=  Topic number:
    call %PY% --only %%num%% --preview --no-upload
)
if "%choice%"=="5" %PY% --upload-existing
if "%choice%"=="6" %PY% --history
if "%choice%"=="7" %PY% --doctor
if "%choice%"=="8" %PY% --setup
if "%choice%"=="0" exit /b 0
echo.
pause
goto menu
