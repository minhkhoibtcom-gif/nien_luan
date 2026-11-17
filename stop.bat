@echo off
setlocal

rem Tat app Streamlit da bat bang start.bat (tim tien trinh dang nghe cong 8501).
rem Luu y: file .bat khong dung chu co dau, vi cmd doc sai ky tu UTF-8.
set "PORT=8501"
set "FOUND="

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    if not "%%p"=="0" (
        set "FOUND=1"
        taskkill /PID %%p /T /F >nul 2>nul
    )
)

if defined FOUND (
    echo Da tat app o cong %PORT%.
) else (
    echo Khong co app nao dang chay o cong %PORT%.
)

endlocal
timeout /t 2 >nul
