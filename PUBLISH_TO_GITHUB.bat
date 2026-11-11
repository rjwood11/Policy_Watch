@echo off
call "%~dp0PUBLISH-TO-GITHUB.bat" %*
exit /b %ERRORLEVEL%
