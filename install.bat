@echo off
setlocal

REM Pythonの有無を確認
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Pythonがインストールされていません。
    exit /b %errorlevel%
)

REM Pythonのバージョンを確認
for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo Pythonバージョン: %PYTHON_VERSION%

REM 最低限のバージョンチェック
set REQUIRED_VERSION=3.11
for /f "tokens=1,2,3 delims=." %%a in ("%PYTHON_VERSION%") do (
    if %%a LSS 3 (
        echo Pythonバージョンが古すぎます。最低限のバージョン: %REQUIRED_VERSION%
        exit /b 1
    ) else if %%a==3 if %%b LSS 6 (
        echo Pythonバージョンが古すぎます。最低限のバージョン: %REQUIRED_VERSION%
        exit /b 1
    )
)

REM 仮想環境のディレクトリを設定
set VENV_DIR=.venv

REM 仮想環境が既に存在するか確認
if exist %VENV_DIR% (
    echo 仮想環境が既に存在します。
    set /p OVERWRITE="上書きインストールしますか？ (y/n): "
    if /i "%OVERWRITE%" neq "y" (
        echo プロセスがキャンセルされました。
        exit /b
    )
    echo 既存の仮想環境を削除しています...
    rmdir /s /q %VENV_DIR%
)

REM 仮想環境を作成
python -m venv %VENV_DIR%
if %errorlevel% neq 0 (
    echo 仮想環境の作成に失敗しました。
    exit /b %errorlevel%
)

REM 仮想環境をアクティブ化して依存関係をインストール
call %VENV_DIR%\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo 仮想環境のアクティブ化に失敗しました。
    exit /b %errorlevel%
)

pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 依存関係のインストールに失敗しました。
    exit /b %errorlevel%
)

echo 仮想環境の設定が完了しました。
endlocal
