@echo off
setlocal ENABLEDELAYEDEXPANSION
REM decompile.bat — Windows wrapper to extract graphics and bins.
REM Order:
REM   1) tools\rom_graphics.py  --file FILE --manifest manifests\graphics.json --extract
REM   2) tools\gfx_convert.py   --manifest manifests\graphics.json --extract

REM ----------------------------- defaults -----------------------------
set "FilePath="

REM Relative paths
set "SCRIPT_DIR=%~dp0"
set "TOOLS_DIR=%SCRIPT_DIR%tools"
set "MAN_DIR=%SCRIPT_DIR%manifests"

set "GraphicsManifest=%MAN_DIR%graphics.json"
set "ROMGRAPH=%TOOLS_DIR%rom_graphics.py"
set "GFXCONVERT=%TOOLS_DIR%gfx_convert.py"

REM ----------------------------- arg parsing -----------------------------
:parse
if "%~1"=="" goto after_parse
if /I "%~1"=="-f"              (set "FilePath=%~2" & shift & shift & goto parse)
if /I "%~1"=="--file"          (set "FilePath=%~2" & shift & shift & goto parse)
if /I "%~1"=="-g"              (set "GraphicsManifest=%~2" & shift & shift & goto parse)
if /I "%~1"=="--graphics-manifest" (set "GraphicsManifest=%~2" & shift & shift & goto parse)
shift
goto parse
:after_parse

if not defined FilePath (
  echo Missing -f/--file. Use: decompile.bat -f FILE [-g GRAPHICS.json]
  exit /b 1
)
if not exist "%FilePath%" (
  echo File not found: %FilePath%
  exit /b 1
)
if not exist "%GraphicsManifest%" (
  echo Missing graphics manifest: %GraphicsManifest%
  exit /b 1
)
if not exist "%ROMGRAPH%" (
  echo Missing tool: %ROMGRAPH%
  exit /b 1
)
if not exist "%GFXCONVERT%" (
  echo Missing tool: %GFXCONVERT%
  exit /b 1
)

REM ----------------------------- python detection -----------------------------
set "PYCMD="
where py.exe >nul 2>nul
if %errorlevel%==0 (
  py -3 -c "import sys; sys.exit(0 if sys.version_info>=(3,7) else 1)" >nul 2>nul
  if %errorlevel%==0 set "PYCMD=py -3"
)
if not defined PYCMD (
  for %%P in (python3.exe python.exe) do (
    where %%P >nul 2>nul && (
      "%%P" -c "import sys; sys.exit(0 if sys.version_info>=(3,7) else 1)" >nul 2>nul
      if !errorlevel! EQU 0 (
        set "PYCMD=%%P"
        goto :found_py
      )
    )
  )
)
:found_py
if not defined PYCMD (
  echo Python 3.7+ not found. Please install Python 3.
  exit /b 1
)

REM ----------------------------- run steps -----------------------------
echo [1/2] rom_graphics.py --extract
%PYCMD% "%ROMGRAPH%" --file "%FilePath%" --manifest "%GraphicsManifest%" --extract || exit /b 1

echo [2/2] gfx_convert.py --extract
%PYCMD% "%GFXCONVERT%" --manifest "%GraphicsManifest%" --extract || exit /b 1

echo Done.
exit /b 0
