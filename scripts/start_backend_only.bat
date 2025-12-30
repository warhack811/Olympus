@echo off
setlocal
if /i "%~1" neq "keep" (
    cmd /k "%~f0" keep
    exit /b
)
title Mami AI - Backend Only
color 0A

cd /d %~dp0..

echo Backend baslatiliyor...

:: Venv kontrolu (proje kok dizininde) - start.bat ile ayni oncelik sirasi (venv -> .venv)
set PYTHON_CMD=python
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    set PYTHON_CMD=python
    echo [BILGI] venv aktif edildi
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    set PYTHON_CMD=python
    echo [BILGI] .venv aktif edildi
) else (
    echo [UYARI] Sanal ortam bulunamadi, sistem Python kullaniliyor
)

echo.
echo Python Surumu:
%PYTHON_CMD% --version
echo.

:: Python ciktisini buffer'lamayi kapat
set PYTHONUNBUFFERED=1

:: Port 8000 baska bir process tarafindan kullaniliyorsa kapat
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo [UYARI] 8000 portu kullaniliyor PID=%%a - Kapatiliyor...
    taskkill /F /PID %%a >nul 2^>^&1
)
timeout /t 2 /nobreak >nul

%PYTHON_CMD% -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

:: Hata durumunda pencereyi acik tut
if errorlevel 1 (
    echo.
    echo [HATA] Bir sorun olustu!
    pause
)

echo.
echo [BILGI] Uvicorn kapandi.
pause
