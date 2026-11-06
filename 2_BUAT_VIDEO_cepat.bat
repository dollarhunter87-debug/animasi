@echo off
cd /d "%~dp0"
echo Membuat video contoh (kualitas rendah, untuk tes). Butuh internet. Mohon tunggu...
py buat_video.py naskah\langit_biru.json --draft
echo.
echo Hasil ada di folder "keluaran". 
pause
