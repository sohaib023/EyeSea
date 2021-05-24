@echo off
cd server
call conda activate eyesea-server
python select_db.py
Pause