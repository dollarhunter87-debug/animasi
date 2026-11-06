@echo off
cd /d "%~dp0"
echo Membuat video kualitas penuh (1080x1920). Butuh internet. Mohon tunggu...
py buat_video.py naskah\langit_biru.json
echo.
echo Hasil ada di folder "keluaran".
pause
