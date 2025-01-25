@echo off
setlocal

REM 仮想環境のディレクトリを設定
set VENV_DIR=.venv

REM 仮想環境をアクティブ化
call %VENV_DIR%\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo 仮想環境のアクティブ化に失敗しました。
    exit /b %errorlevel%
)

REM カレントディレクトリを変更
cd discord_tts || exit /b 1

REM run.py を実行
python run.py
endlocal
pause
