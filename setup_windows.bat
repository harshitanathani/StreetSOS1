@echo off
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Setup complete. Edit .env with your MySQL password, run database.sql in MySQL Workbench, then run python app.py
pause
