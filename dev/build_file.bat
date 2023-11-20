cd ..
python -m PyInstaller main_file_win.spec -y --clean
cd dev

@REM timeout 10
@REM EXIT