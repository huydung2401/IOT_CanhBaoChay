@echo off
chcp 65001 >nul
setlocal
title Khoi dong CanhBaoChay
REM ===== Bam 1 lan: chay Node-RED, 2 mo phong Wokwi, mo dashboard =====
REM Chay duoc o bat ky thu muc nao (clone ve dau cung duoc): GOC = thu muc chua file nay.
set "GOC=%~dp0"
set "GOC=%GOC:~0,-1%"
cd /d "%GOC%"

REM ---- Kiem tra Node.js ----
where node >nul 2>&1
if errorlevel 1 (
    echo [LOI] Chua cai Node.js. Cai ban LTS tu https://nodejs.org roi chay lai file nay.
    start "" https://nodejs.org/en/download
    pause
    exit /b 1
)

REM ---- Kiem tra Node-RED, chua co thi tu cai (mat 1-3 phut, chi lan dau) ----
where node-red >nul 2>&1
if errorlevel 1 (
    echo [0/5] Chua co Node-RED, dang cai: npm install -g --unsafe-perm node-red ...
    call npm install -g --unsafe-perm node-red
    where node-red >nul 2>&1
    if errorlevel 1 (
        echo [LOI] Cai Node-RED khong thanh cong. Mo PowerShell chay: npm install -g --unsafe-perm node-red
        pause
        exit /b 1
    )
)

REM ---- Tim VS Code (khong can lenh code trong PATH) ----
set "VSCODE="
for %%P in ("%LOCALAPPDATA%\Programs\Microsoft VS Code" "%ProgramFiles%\Microsoft VS Code" "%ProgramFiles(x86)%\Microsoft VS Code") do (
    if not defined VSCODE if exist "%%~P\Code.exe" set "VSCODE=%%~P"
)
if not defined VSCODE (
    echo [LOI] Khong tim thay VS Code. Cai tu https://code.visualstudio.com roi chay lai.
    start "" https://code.visualstudio.com
    pause
    exit /b 1
)
set "CODE_EXE=%VSCODE%\Code.exe"
set "CODE_CLI=%VSCODE%\bin\code.cmd"

REM ---- 1. Extension Wokwi + tu chay mo phong (chi mat thoi gian o lan dau) ----
echo [1/5] Kiem tra extension Wokwi va Auto Run Command...
call "%CODE_CLI%" --install-extension wokwi.wokwi-vscode >nul 2>&1
call "%CODE_CLI%" --install-extension gabrielgrinberg.auto-run-command >nul 2>&1
for %%T in (esp01 esp02) do (
    if not exist "%GOC%\wokwi\%%T\.vscode\settings.json" (
        mkdir "%GOC%\wokwi\%%T\.vscode" 2>nul
        copy /y "%GOC%\wokwi\settings_tu_chay_wokwi.json" "%GOC%\wokwi\%%T\.vscode\settings.json" >nul
    )
)

REM ---- 2. Node-RED (neu chua chay); CSDL canhbaochay.db nam trong thu muc project ----
echo [2/5] Khoi dong Node-RED...
netstat -ano | findstr ":1880 " | findstr LISTENING >nul
if not errorlevel 1 goto nodered_san
start "Node-RED - CanhBaoChay" /min cmd /k "cd /d "%GOC%" && node-red"
goto nodered_xong
:nodered_san
echo       Node-RED da chay san, bo qua.
:nodered_xong

REM ---- 3. Dua flow moi nhat vao Node-RED (khong doi thi bo qua), cai goi con thieu ----
echo [3/5] Kiem tra flow Node-RED (lan dau tu cai dashboard + SQLite, mat 1-3 phut)...
node "%GOC%\nodered\cap_nhat_flow.js" --cho 120
if errorlevel 1 echo       Canh bao: chua cap nhat duoc flow. Xem cua so Node-RED.

REM ---- 4. Hai cua so VS Code, moi cua so tu chay mo phong sau ~5 giay ----
echo [4/5] Mo mo phong esp01 va esp02...
start "" "%CODE_EXE%" -n "%GOC%\wokwi\esp01"
timeout /t 4 /nobreak >nul
start "" "%CODE_EXE%" -n "%GOC%\wokwi\esp02"

REM ---- 5. Doi he thong len roi mo dashboard ----
echo [5/5] Doi 20 giay roi mo dashboard...
timeout /t 20 /nobreak >nul
start "" http://localhost:1880/dashboard

REM Xep cua so de ca hai mo phong luon hien (bi che kin la Wokwi chay cham, mat ket noi)
echo Xep cua so: dashboard ben trai, esp01/esp02 ben phai...
timeout /t 4 /nobreak >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%GOC%\xep_cua_so.ps1"

echo.
echo Xong. Dashboard se xanh het sau khoang 30-60 giay.
echo - Lan dau tren may moi: VS Code hien "INVALID LICENSE" thi bam F1 ^> Wokwi: Request a New License.
echo - Cua so Node-RED dang thu nho o thanh tac vu: dung dong no.
echo - DUNG thu nho hoac che kin 2 cua so VS Code: mo phong se chay cham va mat ket noi.
echo - Khong chay file nay bang "Run as administrator".
timeout /t 15 >nul
