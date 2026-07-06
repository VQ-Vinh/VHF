@echo off
cd /d "D:\EMBEDDED\DLV_Corporation\VHF"
set PYTHONPATH=D:\EMBEDDED\DLV_Corporation\VHF
"%~dp0venv\Scripts\python.exe" -u "%~dp0vhf_processor\main.py" %*
