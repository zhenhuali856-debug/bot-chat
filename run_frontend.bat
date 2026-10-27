@echo off
chcp 65001 >nul
echo 正在启动 Vue 3 前端开发服务 (Vite)...
cd /d "%~dp0frontend"
npm run dev
pause
