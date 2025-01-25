@echo off
setlocal

REM Python�̗L�����m�F
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python���C���X�g�[������Ă��܂���B
    exit /b %errorlevel%
)

REM Python�̃o�[�W�������m�F
for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo Python�o�[�W����: %PYTHON_VERSION%

REM �Œ���̃o�[�W�����`�F�b�N
set REQUIRED_VERSION=3.11
for /f "tokens=1,2,3 delims=." %%a in ("%PYTHON_VERSION%") do (
    if %%a LSS 3 (
        echo Python�o�[�W�������Â����܂��B�Œ���̃o�[�W����: %REQUIRED_VERSION%
        exit /b 1
    ) else if %%a==3 if %%b LSS 6 (
        echo Python�o�[�W�������Â����܂��B�Œ���̃o�[�W����: %REQUIRED_VERSION%
        exit /b 1
    )
)

REM ���z���̃f�B���N�g����ݒ�
set VENV_DIR=.venv

REM ���z�������ɑ��݂��邩�m�F
if exist %VENV_DIR% (
    echo ���z�������ɑ��݂��܂��B
    set /p OVERWRITE="�㏑���C���X�g�[�����܂����H (y/n): "
    if /i "%OVERWRITE%" neq "y" (
        echo �v���Z�X���L�����Z������܂����B
        exit /b
    )
    echo �����̉��z�����폜���Ă��܂�...
    rmdir /s /q %VENV_DIR%
)

REM ���z�����쐬
python -m venv %VENV_DIR%
if %errorlevel% neq 0 (
    echo ���z���̍쐬�Ɏ��s���܂����B
    exit /b %errorlevel%
)

REM ���z�����A�N�e�B�u�����Ĉˑ��֌W���C���X�g�[��
call %VENV_DIR%\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ���z���̃A�N�e�B�u���Ɏ��s���܂����B
    exit /b %errorlevel%
)

pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo �ˑ��֌W�̃C���X�g�[���Ɏ��s���܂����B
    exit /b %errorlevel%
)

echo ���z���̐ݒ肪�������܂����B
endlocal
