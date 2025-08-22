@echo off
setlocal ENABLEDELAYEDEXPANSION
REM compile.bat — Windows wrapper to build a translated PocketStation save/ROM.
REM Order:
REM   1) tools\gfx_convert.py   --manifest manifests\graphics.json --pack
REM   2) tools\rom_graphics.py  --file FILE --manifest manifests\graphics.json --pack
REM   3) tools\rom_patches.py   --file FILE --manifest manifests\patches.json --language LANG [base-offset] [--dry-run]
REM   4) tools\rom_names.py     --file FILE --manifest manifests\cards.json   --language LANG [base-offset] [--dry-run]

REM ----------------------------- defaults -----------------------------
set "FilePath="
set "Language="
set "BaseMode=raw"
set "CustomOffset="
set "DryRun="

REM Paths relative to this script
set "SCRIPT_DIR=%~dp0"
set "TOOLS_DIR=%SCRIPT_DIR%tools"
set "MAN_DIR=%SCRIPT_DIR%manifests"

set "GraphicsManifest=%MAN_DIR%graphics.json"
set "PatchesManifest=%MAN_DIR%patches.json"
set "CardsManifest=%MAN_DIR%cards.json"

set "GFXCONVERT=%TOOLS_DIR%gfx_convert.py"
set "ROMGRAPH=%TOOLS_DIR%rom_graphics.py"
set "ROMPATCH=%TOOLS_DIR%rom_patches.py"
set "ROMNAMES=%TOOLS_DIR%rom_names.py"

REM ----------------------------- arg parsing -----------------------------
:parse
if "%~1"=="" goto after_parse
if /I "%~1"=="-f"              (set "FilePath=%~2" & shift & shift & goto parse)
if /I "%~1"=="--file"          (set "FilePath=%~2" & shift & shift & goto parse)
if /I "%~1"=="-l"              (set "Language=%~2" & shift & shift & goto parse)
if /I "%~1"=="--language"      (set "Language=%~2" & shift & shift & goto parse)
if /I "%~1"=="--raw"           (set "BaseMode=raw" & shift & goto parse)
if /I "%~1"=="--mcs"           (set "BaseMode=mcs" & shift & goto parse)
if /I "%~1"=="--offset"        (set "BaseMode=offset" & set "CustomOffset=%~2" & shift & shift & goto parse)
if /I "%~1"=="-g"              (set "GraphicsManifest=%~2" & shift & shift & goto parse)
if /I "%~1"=="--graphics-manifest" (set "GraphicsManifest=%~2" & shift & shift & goto parse)
if /I "%~1"=="-p"              (set "PatchesManifest=%~2" & shift & shift & goto parse)
if /I "%~1"=="--patches-manifest"  (set "PatchesManifest=%~2" & shift & shift & goto parse)
if /I "%~1"=="-c"              (set "CardsManifest=%~2" & shift & shift & goto parse)
if /I "%~1"=="--cards-manifest"    (set "CardsManifest=%~2" & shift & shift & goto parse)
if /I "%~1"=="--dry-run"       (set "DryRun=yes" & shift & goto parse)
shift
goto parse
:after_parse

REM ----------------------------- validate -----------------------------
if not defined FilePath (
  echo Missing -f/--file. Use: compile.bat -f FILE [-l LANG] [--raw^|--mcs^|--offset HEX]
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
if not exist "%PatchesManifest%" (
  echo Missing patches manifest: %PatchesManifest%
  exit /b 1
)
if not exist "%CardsManifest%" (
  echo Missing cards manifest: %CardsManifest%
  exit /b 1
)

if not exist "%GFXCONVERT%" (
  echo Missing tool: %GFXCONVERT%
  exit /b 1
)
if not exist "%ROMGRAPH%" (
  echo Missing tool: %ROMGRAPH%
  exit /b 1
)
if not exist "%ROMPATCH%" (
  echo Missing tool: %ROMPATCH%
  exit /b 1
)
if not exist "%ROMNAMES%" (
  echo Missing tool: %ROMNAMES%
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

REM ----------------------------- choose language if needed -----------------------------
if not defined Language (
  set "langs="
  for /f "usebackq delims=" %%L in (`%PYCMD% -c "import json,sys; j=json.load(open(r'%CardsManifest%',encoding='utf-8')); print('\n'.join(k for k,v in j.items() if isinstance(v,list) and v and isinstance(v[0],dict) and 'name' in v[0] and 'number' in v[0]))"` ) do (
    set "langs=!langs! %%L"
  )
  if not defined langs (
    echo No languages found in %CardsManifest%
    exit /b 2
  )
  echo Languages in %CardsManifest%:
  set /a n=0
  for %%X in (!langs!) do (
    set /a n+=1
    echo   !n!) %%X
    set "L_!n!=%%X"
  )
  set /p sel=Choose language [1-!n!]: 
  if not defined L_%sel% (
    echo Invalid choice.
    exit /b 2
  )
  for /f "delims=" %%K in ("!L_%sel%!") do set "Language=%%K"
)

REM ----------------------------- base args -----------------------------
set "BASEARGS="
if /I "%BaseMode%"=="raw"    set "BASEARGS=--raw"
if /I "%BaseMode%"=="mcs"    set "BASEARGS=--mcs"
if /I "%BaseMode%"=="offset" set "BASEARGS=--offset %CustomOffset%"
if /I "%DryRun%"=="yes"      set "DRY=--dry-run"  else set "DRY="

REM ----------------------------- optional textures sync -----------------------------
if exist "%SCRIPT_DIR%textures\*.png" if exist "%SCRIPT_DIR%gfx\png" (
  echo Copying textures\*.png -> gfx\png\
  copy /Y "%SCRIPT_DIR%textures\*.png" "%SCRIPT_DIR%gfx\png\" >nul
)

REM ----------------------------- run steps -----------------------------
echo [1/4] gfx_convert.py --pack
%PYCMD% "%GFXCONVERT%" --manifest "%GraphicsManifest%" --pack || exit /b 1

echo [2/4] rom_graphics.py --pack
%PYCMD% "%ROMGRAPH%" --file "%FilePath%" --manifest "%GraphicsManifest%" --pack || exit /b 1

echo [3/4] rom_patches.py
%PYCMD% "%ROMPATCH%" --file "%FilePath%" --manifest "%PatchesManifest%" --language "%Language%" %BASEARGS% %DRY% || exit /b 1

echo [4/4] rom_names.py
%PYCMD% "%ROMNAMES%" --file "%FilePath%" --manifest "%CardsManifest%" --language "%Language%" %BASEARGS% %DRY% || exit /b 1

echo Done.
exit /b 0
