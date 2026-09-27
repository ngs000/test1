@echo off
cd /d "%~dp0"
echo A arrancar o Dual-API Writer...

rem Prefer the "py" launcher (default on Windows installs); fall back to "python".
where py >/dev/null 2>nul
if not errorlevel 1 (
    py -3 server.py %*
    goto end
)
where python >/dev/null 2>nul
if not errorlevel 1 (
    python server.py %*
    goto end
)
echo.
echo Python nao encontrado. Instala-o em https://www.python.org/downloads/
echo (marca "Add python.exe to PATH" durante a instalacao) e volta a abrir este ficheiro.

:end
pause
