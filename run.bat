@echo off
setlocal

REM ���z���̃f�B���N�g����ݒ�
set VENV_DIR=.venv

REM ���z�����A�N�e�B�u��
call %VENV_DIR%\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ���z���̃A�N�e�B�u���Ɏ��s���܂����B
    exit /b %errorlevel%
)

REM �J�����g�f�B���N�g����ύX
cd discord_tts || exit /b 1

REM run.py �����s
python run.py
endlocal
pause
