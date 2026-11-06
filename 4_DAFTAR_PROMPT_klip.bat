@echo off
cd /d "%~dp0"
echo Membuat daftar prompt untuk generator video AI...
py buat_video.py naskah\langit_biru.json --prompt-klip
echo.
echo Buka file klip\kenapa_langit_biru\daftar_prompt.txt
pause
