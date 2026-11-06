@echo off
cd /d "%~dp0"
echo Memasang kebutuhan program (hanya sekali)...
py -m pip install -r requirements.txt
echo.
echo Selesai. Kalau tidak ada tulisan ERROR merah di atas, lanjut klik 2_BUAT_VIDEO_cepat.bat
pause
