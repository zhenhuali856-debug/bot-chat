@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Rabbit AI - 网页开发控制台

echo 正在启动 Rabbit AI 网页开发控制台 (http://localhost:3000)...

if exist "backend\.venv\Scripts\python.exe" (
    "backend\.venv\Scripts\python.exe" "dev_dashboard.py"
) else (
    python "dev_dashboard.py"
)

pause
