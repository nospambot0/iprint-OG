# OpenThermal for Windows — SC03h-3714 prototype

Windows x64 desktop BLE discovery and GATT inspection for the Shenzhen Frog To Sea iPrint / SC03h printer family.

## Features
- Scan nearby Bluetooth Low Energy devices.
- Prioritize likely SC03h/iPrint devices.
- Connect to a selected BLE device.
- Enumerate GATT services and characteristics.
- Subscribe to notifications and display raw data.

## Printing
Printing is intentionally disabled until the exact printer firmware transfer protocol is verified. The expected AE30 / AE01 / AE02 UUID profile is a family hint, not proof of compatibility.

## Build locally
Install 64-bit Python 3.11, then run:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name OpenThermal --collect-all PySide6 --collect-all bleak main.py
```
Output: `dist\OpenThermal.exe`.
