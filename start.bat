@echo off
@setlocal enableextensions
@cd /d "%~dp0"

cd server
call conda activate eyesea-server
python select_db.py
Pause