@echo off
title Analizador de League of Legends
color 0A

:: Cambiar al directorio donde está el .bat
cd /d "%~dp0"

echo ==================================================
echo       INICIANDO ANALIZADOR DE LEAGUE OF LEGENDS
echo ==================================================
echo.

:: Comprobar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH del sistema.
    echo Por favor, instala Python desde https://www.python.org/downloads/
    echo Asegurate de marcar la casilla "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b
)

:: Ejecutar el script
python analizador.py

echo.
echo ==================================================
echo                 PROCESO TERMINADO
echo ==================================================
pause
