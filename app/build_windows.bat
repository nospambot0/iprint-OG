@echo off
setlocal
py -3.11 -m venv .venv || goto error
call .venv\Scripts\activate
python -m pip install --upgrade pip || goto error
pip install -r requirements.txt pyinstaller || goto error
pyinstaller --noconfirm --clean --onefile --windowed --name OpenThermal --collect-all PySide6 --collect-all bleak main.py || goto error
echo Build complete: dist\OpenThermal.exe
pause
exit /b 0
:error
echo Build failed. Review the error above.
pause
exit /b 1
