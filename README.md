# OpenThermal — Windows x64

Standalone Windows desktop utility for BLE discovery and GATT inspection of SC03h / iPrint-family thermal printers.

## Source
The clean application source is in [app/](app/). The previous malformed ZIP bundle has been removed. Build automation is in [GitHub Actions](.github/workflows/build-windows.yml).

## Build
Open **Actions → Build OpenThermal Windows EXE**. On success, download the `OpenThermal-Windows-x64` artifact or the prerelease asset.

## Current limitations
This build supports BLE scanning, connecting, GATT enumeration and notification inspection. Printing remains disabled until the exact printer firmware transfer protocol is verified. The SC03h-3714 model name alone does not establish a safe print data format.
