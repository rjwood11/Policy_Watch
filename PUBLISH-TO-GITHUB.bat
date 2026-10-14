@echo off
setlocal
cd /d "%~dp0"
echo PolicyWatch - Commit, push, and deploy to GitHub Pages
echo Checks run first. If files have changed, you will be asked for a commit description.
echo To cancel before committing, press Ctrl+C at the description prompt.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\publish-github.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo Publishing stopped. Read the message above; your local files are still available.
if /I not "%POLICYWATCH_NO_PAUSE%"=="1" pause
exit /b %RESULT%
