@echo off
chcp 65001 >nul
title NALA SMART PANEL - CONG CU NAP FIRMWARE TU DONG (TU LAM DIEN TU)
color 0B
echo =====================================================================
echo    NALA SMART PANEL - ESP32-S3 VOICE & INTERCOM HUB (v3.6.1)
echo          Tac gia: Pham Ngoc Ty (TU LAM DIEN TU)
echo =====================================================================
echo.
echo [1/3] Dang kiem tra cong COM ket noi voi ESP32-S3...
echo Hay dam bao ban da cam cap Type-C tu ESP32-S3 vao may tinh!
echo.
set /p COMPORT="Nhap ten cong COM (vi du COM3, COM4, COM5...): "

if "%COMPORT%"=="" (
    echo [LOI] Ban chua nhap ten cong COM!
    pause
    exit /b
)

echo.
echo [2/3] Dang chuan bi nap Firmware v3.6.1 len cong %COMPORT%...
echo (Neu chip khong nhan, vui long nhan giu nut BOOT, cam cap roi nhan Enter)
pause

echo.
echo [3/3] Dang nap Flash...
python -m esptool --chip esp32s3 --port %COMPORT% --baud 921600 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 80m --flash_size 16MB 0x0000 bootloader.bin 0x8000 partitions.bin 0x10000 firmware.bin

if %ERRORLEVEL% equ 0 (
    echo.
    echo =====================================================================
    echo    NAP FIRMWARE THANH CONG 100%! 
    echo    Man hinh se khoi dong lai va phat WiFi: NALA_PANEL_SETUP
    echo    Ket noi WiFi tren dien thoai va truy cap http://192.168.4.1 de cai dat.
    echo =====================================================================
) else (
    echo.
    echo [THAT BAI] Qua trinh nap gap loi! Vui long kiem tra lai driver CH340/CP2102 hoac cong COM.
)

pause
