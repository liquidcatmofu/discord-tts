#!/bin/bash

# 仮想環境のディレクトリを設定
VENV_DIR=".venv"

# 仮想環境をアクティブ化
source "$VENV_DIR/bin/activate"
if [ $? -ne 0 ]; then
    echo "仮想環境のアクティブ化に失敗しました。"
    exit 1
fi

# カレントディレクトリを変更
cd discord_tts || exit 1

# run.py を実行
python run.py
