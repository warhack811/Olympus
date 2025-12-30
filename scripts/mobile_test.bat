@echo off
title Mami AI - MOBIL TEST MODU (Frontend + Backend + Forge)
color 0D
cls

:: ===================================================================
:: Mami AI v4 - Tam Mobil Test (Frontend + Backend + Forge)
:: ===================================================================

echo.
echo  [1/4] Forge (Flux) kontrol ediliyor...
echo  -----------------------------------------
set "FORGE_PATH=D:\ai\forge\stable-diffusion-webui-forge-main"
if exist "%FORGE_PATH%\webui-user.bat" (
    echo        Forge baslatiliyor...
    pushd "%FORGE_PATH%"
    start "Mami AI - Forge" /min cmd /k "webui-user.bat"
    popd
    timeout /t 3 /nobreak >nul
) else (
    echo        [UYARI] Forge yolu bulunamadi. (Opsiyonel)
)

echo.
echo  [2/4] Backend baslatiliyor (Port 8000)...
echo  -----------------------------------------
cd /d %~dp0..

:: Backend'i yeni pencerede baslat
start "Mami AI - Backend" /min cmd /k "scripts\start_backend_only.bat"

echo.
echo  [3/4] Frontend baslatiliyor (Port 5173)...
echo  ------------------------------------------
cd ui-new

:: Frontend'i host modunda baslat (disaridan erisim icin)
start "Mami AI - Frontend" cmd /k "npm run dev -- --host 0.0.0.0"

echo.
echo  [4/4] Hazir!
echo  ------------------------------------------
echo.
echo  Telefonundan su adrese git:
echo.
echo    http://[IP_ADRESIN]:5173/new-ui/
echo.
echo  (Ornek: http://100.93.11.128:5173/new-ui/)
echo.
echo  Not: Tailscale veya Wi-Fi IP adresini kullanmalisin.
echo.
pause
