@echo off
setlocal
cd /d "%~dp0"
echo PolicyWatch - Commit, push, and deploy to GitHub Pages
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\publish-github.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo Publishing stopped. Read the message above; your local files are still available.
if /I not "%POLICYWATCH_NO_PAUSE%"=="1" pause
exit /b %RESULT%
