cd ..
python -m PyInstaller main_folder_win.spec -y --clean
cd dev

@REM timeout 10
@REM EXIT