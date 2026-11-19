@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === ImageToPDF Studio 一键打包并同步源码 ===
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail
python -m PyInstaller --noconfirm --distpath dist --workpath build ImageToPDF_Studio.spec
if errorlevel 1 goto :fail
python scripts/make_source_bundle.py
if errorlevel 1 goto :fail
echo.
echo 完成:
echo   EXE   dist\ImageToPDF_Studio.exe
echo   源码  源码交付\ImageToPDF_源码_v*.zip
goto :end
:fail
echo.
echo 失败，请检查上方错误信息。
:end
pause
