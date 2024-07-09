# discord-tts

ローカルで動作する多機能なVoiceVox読み上げボットです。

**現在執筆中のため、このreadmeは不完全です。**

## 目次

- [discord-tts](#discord-tts)
  - [目次](#目次)
  - [概要](#概要)
  - [環境](#環境)
- [環境構築](#環境構築)
  - [Pythonのインストール](#pythonのインストール)
    - [Windowsの場合](#windowsの場合)
    - [Linuxの場合](#linuxの場合)
  - [リポジトリのクローン](#リポジトリのクローン)

## 概要

PythonのDiscord APIのPycordを使用し、VoiceVoxの音声で読み上げを行うbotです。
サーバーごと、ユーザーごとの辞書機能、話者変更、音程や速度を変更する機能を内蔵しています。
スラッシュコマンドと接頭辞によるコマンドの両方に対応します。

**提案や要望がある場合、または問題を見つけた場合はissueに投げてくれると嬉しいです。**

## 環境

- Python 3.11.7
- Pycord 2.5.0
- PyNaCl 1.5.0
- Requests 2.32.3
- Python-dotenv 1.0.1

# 環境構築

## Pythonのインストール

開発に使用したバージョンは3.11.7ですが、3.11以上であれば動くはずです。

### Windowsの場合
[こちら](https://www.python.org/downloads/)からお使いの環境に合ったPythonのインストーラーをダウンロードし、インストールしてください。

### Linuxの場合
お使いのパッケージマネージャーからインストールしてください。

## リポジトリのクローン

PyCharm等のIDEでクローンします。依存関係のインストールまでが自動で行われるためこちらを推奨。


IDEを用いない場合は以下のコマンドを実行します。
```
$ git clone https://github.com/liquidcatmofu/discord-tts.git
```

