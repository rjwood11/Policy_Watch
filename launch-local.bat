@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%" || (
  echo Could not change to %ROOT%.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found on PATH.
  pause
  exit /b 1
)

set "PYTHON_CMD="
where python >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  where py >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

set "LAUNCH_MODE=%POLICYWATCH_LAUNCH_MODE%"
if not defined LAUNCH_MODE set "LAUNCH_MODE=static"

if not exist node_modules (
  echo Installing dependencies...
  call npm install
  if errorlevel 1 (
    echo npm install failed.
    pause
    exit /b 1
  )
)

set "DATA_WAS_REBUILT=0"
if /I "%POLICYWATCH_SKIP_DATA_BUILD%"=="1" (
  echo Skipping local data build because POLICYWATCH_SKIP_DATA_BUILD=1.
) else if /I "%POLICYWATCH_REBUILD_DATA%"=="1" (
  call :BuildData
) else if not exist "public\data\counties\index.json" (
  echo Generated county data was not found.
  call :BuildData
) else (
  echo Using existing generated data. Set POLICYWATCH_REBUILD_DATA=1 to rebuild before launch.
)
if errorlevel 1 exit /b 1

if /I "%LAUNCH_MODE%"=="static" (
  if not defined PYTHON_CMD (
    echo Python is required for static launch mode.
    echo Set POLICYWATCH_LAUNCH_MODE=dev to use the Next.js dev server instead.
    pause
    exit /b 1
  )

  if /I "%POLICYWATCH_REBUILD_STATIC%"=="1" (
    echo Building static export. This can take several minutes...
    call npm run build
    if errorlevel 1 (
      echo Static build failed.
      pause
      exit /b 1
    )
  ) else if "%DATA_WAS_REBUILT%"=="1" (
    echo Data changed. Building static export. This can take several minutes...
    call npm run build
    if errorlevel 1 (
      echo Static build failed.
      pause
      exit /b 1
    )
  ) else if not exist "out\index.html" (
    echo Static export was not found. Building it now. This can take several minutes...
    call npm run build
    if errorlevel 1 (
      echo Static build failed.
      pause
      exit /b 1
    )
  ) else (
    echo Using existing static export. Set POLICYWATCH_REBUILD_STATIC=1 to rebuild before launch.
  )
) else if /I "%LAUNCH_MODE%"=="dev" (
  echo Using Next.js dev server mode.
) else (
  echo Unknown POLICYWATCH_LAUNCH_MODE value: %LAUNCH_MODE%
  echo Use "static" or "dev".
  pause
  exit /b 1
)

set "PORT=3000"
where powershell >nul 2>nul
if not errorlevel 1 (
  for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | ForEach-Object { $_.Port }; 3000..3010 | Where-Object { $listeners -notcontains $_ } | Select-Object -First 1"`) do set "PORT=%%P"
)

set "URL=http://127.0.0.1:%PORT%"

if /I "%POLICYWATCH_DRY_RUN%"=="1" (
  echo Dry run complete. Would start PolicyWatch in %LAUNCH_MODE% mode at %URL%.
  endlocal
  exit /b 0
)

if /I "%LAUNCH_MODE%"=="static" (
  echo Starting local static server at %URL%...
  start "PolicyWatch Static Server" /D "%ROOT%" cmd /k "%PYTHON_CMD% -m scripts.serve_static --port %PORT% --host 127.0.0.1 --directory out"
) else (
  echo Starting local development server at %URL%...
  start "PolicyWatch Dev Server" /D "%ROOT%" cmd /k "npm run dev -- -p %PORT% --hostname 127.0.0.1"
)

echo Waiting for %URL% to respond...
where powershell >nul 2>nul
if not errorlevel 1 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$url = '%URL%'; $openBrowser = '%POLICYWATCH_NO_BROWSER%' -ne '1'; for ($i = 0; $i -lt 120; $i++) { try { $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2; if ($response.StatusCode -ge 200) { if ($openBrowser) { Start-Process $url }; exit 0 } } catch { Start-Sleep -Seconds 1 } }; exit 1"
  if errorlevel 1 (
    echo Server did not respond within 120 seconds.
    echo Check the PolicyWatch server window for errors.
    if /I "%LAUNCH_MODE%"=="dev" echo Dev mode can be slow for this prototype; try static mode by running launch-local.bat without POLICYWATCH_LAUNCH_MODE=dev.
  )
) else (
  timeout /t 5 /nobreak >nul
  if /I not "%POLICYWATCH_NO_BROWSER%"=="1" start "" "%URL%"
)

echo Server window is running separately. Close it to stop PolicyWatch.
if /I not "%POLICYWATCH_NO_PAUSE%"=="1" pause
endlocal
exit /b 0

:BuildData
if not defined PYTHON_CMD (
  if exist "public\data\counties\index.json" (
    echo Python was not found. Continuing with existing generated data.
    exit /b 0
  )
  echo Python was not found and no generated county data was found.
  pause
  exit /b 1
)

echo Building local data files. This can take 1-2 minutes...
call %PYTHON_CMD% -m scripts.summaries.build_prototype_data
if errorlevel 1 (
  if exist "public\data\counties\index.json" (
    echo Data build failed. Continuing with existing generated data.
    exit /b 0
  )
  echo Data build failed and no generated county data was found.
  pause
  exit /b 1
)
set "DATA_WAS_REBUILT=1"
exit /b 0
