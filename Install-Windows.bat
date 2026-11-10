@echo off
setlocal
cd /d "%~dp0"
echo ClipForge setup. This installs Python and FFmpeg if they are missing (internet needed).
where winget >nul 2>&1
if errorlevel 1 (
  echo winget was not found. Install "App Installer" from the Microsoft Store, or install Python 3.12 and FFmpeg by hand.
  pause & exit /b 1
)
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Links"
set "PYEXE=" & set "PYARG="
py -3.12 --version >nul 2>&1 && (set "PYEXE=py" & set "PYARG=-3.12")
if not defined PYEXE (
  echo Installing Python 3.12...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PYEXE (
  echo Python is installed but this window cannot see it yet. Close this window and run Install-Windows.bat again.
  pause & exit /b 1
)
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo Installing FFmpeg...
  winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
)
echo Installing ClipForge packages...
"%PYEXE%" %PYARG% -m pip install -r requirements.txt
if errorlevel 1 ( echo Package install failed. & pause & exit /b 1 )
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\ClipForge.lnk');$s.TargetPath='%~dp0run_web.bat';$s.WorkingDirectory='%~dp0';$s.Save()"
echo.
echo Done. Use the ClipForge shortcut on your Desktop (or run_web.bat) to start the app.
pause
