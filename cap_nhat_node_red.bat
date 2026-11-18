@echo off
chcp 65001 >nul
setlocal
title Cap nhat flow Node-RED - CanhBaoChay
REM Dua flow trong nodered\luong_tong_hop.json vao Node-RED (giu bien Telegram, broker, tab khac).
REM Thuong khong can chay file nay: chay_he_thong.bat da tu kiem tra moi lan khoi dong.
set "GOC=%~dp0"
set "GOC=%GOC:~0,-1%"
netstat -ano | findstr ":1880 " | findstr LISTENING >nul
if not errorlevel 1 goto chay_cap_nhat
echo Node-RED chua chay, dang khoi dong...
start "Node-RED - CanhBaoChay" /min cmd /k "cd /d "%GOC%" && node-red"
:chay_cap_nhat
node "%GOC%\nodered\cap_nhat_flow.js" --cho 120 --ep
echo.
pause
