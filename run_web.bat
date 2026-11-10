@echo off
setlocal
cd /d "%~dp0"
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Links"
set "PYEXE=" & set "PYARG="
py -3.12 --version >nul 2>&1 && (set "PYEXE=py" & set "PYARG=-3.12")
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYEXE (
  echo Python 3.12 was not found. Run Install-Windows.bat first.
  pause & exit /b 1
)
"%PYEXE%" %PYARG% -c "import fastapi, uvicorn, multipart, faster_whisper, numpy, cv2, streamlink" >nul 2>&1
if errorlevel 1 (
  echo Installing the required packages. This only happens once...
  "%PYEXE%" %PYARG% -m pip install -r requirements.txt
  if errorlevel 1 ( echo Package install failed. & pause & exit /b 1 )
)
echo Starting ClipForge. Keep this window open. Your browser will open in a moment.
"%PYEXE%" %PYARG% -m clipforge_web
if errorlevel 1 pause
