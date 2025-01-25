#!/bin/bash

# Pythonの有無を確認
if ! command -v python3 &> /dev/null; then
    echo "Pythonがインストールされていません。"
    exit 1
fi

# Pythonのバージョンを確認
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Pythonバージョン: $PYTHON_VERSION"

# 最低限のバージョンチェック
REQUIRED_VERSION="3.11"
if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo "Pythonバージョンが古すぎます。最低限のバージョン: $REQUIRED_VERSION"
    exit 1
fi

# 仮想環境のディレクトリを設定
VENV_DIR=".venv"

# 仮想環境が既に存在するか確認
if [ -d "$VENV_DIR" ]; then
    echo "仮想環境が既に存在します。"
    read -p "上書きインストールしますか？ (y/n): " OVERWRITE
    if [[ "$OVERWRITE" != "y" ]]; then
        echo "プロセスがキャンセルされました。"
        exit 1
    fi
    echo "既存の仮想環境を削除しています..."
    rm -rf "$VENV_DIR"
fi

# 仮想環境を作成
python3 -m venv "$VENV_DIR"
if [ $? -ne 0 ]; then
    echo "仮想環境の作成に失敗しました。"
    exit 1
fi

# 仮想環境をアクティブ化して依存関係をインストール
source "$VENV_DIR/bin/activate"
if [ $? -ne 0 ]; then
    echo "仮想環境のアクティブ化に失敗しました。"
    exit 1
fi

pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "依存関係のインストールに失敗しました。"
    exit 1
fi

echo "仮想環境の設定が完了しました。"
