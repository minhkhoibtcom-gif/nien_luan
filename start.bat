@echo off
setlocal
cd /d "%~dp0"

rem Bat app demo phan khuc khach hang (Streamlit) roi mo trinh duyet. Tat bang stop.bat.
rem Lan dau chay: tu tao moi truong ao venv va cai thu vien trong requirements.txt (can Python 3.11 tro len).
rem Luu y: file .bat khong dung chu co dau, vi cmd doc sai ky tu UTF-8.
set "PORT=8501"
set "PY=%~dp0venv\Scripts\python.exe"

netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul
if not errorlevel 1 goto :running

if exist "%PY%" goto :check_libs
echo [1/3] Tao moi truong ao venv...
where python >nul 2>nul
if errorlevel 1 goto :no_python
python -m venv venv
if errorlevel 1 goto :fail

:check_libs
"%PY%" -c "import streamlit, kmodes, sklearn, pandas, altair" >nul 2>nul
if not errorlevel 1 goto :run
echo [2/3] Cai thu vien trong requirements.txt (lan dau mat vai phut)...
"%PY%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :fail

:run
echo [3/3] Bat app o cong %PORT%...
rem Cua so Streamlit thu nho: xem log loi o do. Dong cua so do hoac chay stop.bat de tat app.
start "Phan khuc khach hang - Streamlit" /min "%PY%" -m streamlit run app.py --server.port %PORT% --server.headless true

rem Cho toi da 60 giay de server san sang
set /a WAIT=0
:wait_loop
ping -n 2 127.0.0.1 >nul
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul
if not errorlevel 1 goto :open
set /a WAIT+=1
if %WAIT% lss 60 goto :wait_loop
echo Server chua san sang sau 60 giay. Xem log trong cua so "Phan khuc khach hang - Streamlit".
goto :end

:running
echo App da chay san o cong %PORT%.

:open
echo Mo http://localhost:%PORT% ... Lan dau mo, mo hinh huan luyen mat vai giay.
start "" "http://localhost:%PORT%"
goto :end

:no_python
echo Khong tim thay Python. Cai Python 3.11 tro len (tick "Add python.exe to PATH") roi chay lai.
goto :end

:fail
echo Co loi khi cai dat. Xem thong bao phia tren.

:end
endlocal
timeout /t 3 >nul
