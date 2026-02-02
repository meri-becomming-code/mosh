@echo off
TITLE Build MCC ADA Toolkit (Windows)
ECHO Installing Dependencies...
pip install -r requirements.txt
pip install pyinstaller

ECHO Building Executable...
python build_app.py

ECHO.
ECHO Done! Check the 'dist' folder.
PAUSE
