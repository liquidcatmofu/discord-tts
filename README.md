# discord-tts

ローカルで動作する多機能なVoiceVox読み上げボットです。

現在執筆中のため、このReadmeは不完全です。

## 目次

- [discord-tts](#discord-tts)
  - [目次](#目次)
  - [概要](#概要)
  - [環境](#環境)
- [環境構築](#環境構築)

## 概要

PythonのDiscord APIのPycordを使用し、VoiceVoxの音声で読み上げを行うbotです。
サーバーごと、ユーザーごとの辞書機能、話者変更、音程や速度を変更する機能を内蔵しています。
スラッシュコマンドと接頭辞によるコマンドの両方に対応します。

## 環境

- Python 3.11.7
- Pycord 2.5.0
- PyNaCl 1.5.0
- Requests 2.32.3
- Python-dotenv 1.0.1

# 環境構築

## Python実行環境のインストール

開発に使用したバージョンは3.11.7ですが、3.11以上であれば動くはずです。
セキュリティの問題のため、マイナーバージョンは最新のものを用いることを推奨します。

### Windowsの場合
[こちら](https://www.python.org/downloads/)からお使いの環境に合ったPythonのインストーラーをダウンロードし、インストールしてください。

### Linuxの場合
お使いのパッケージマネージャーからインストールしてください。


## リポジトリのクローン

PyCharm等のIDEでクローンします。依存関係のインストールまでが自動で行われるためこちらを推奨。


IDEを用いない場合は以下のコマンドを実行します。
```
$ git clone https://github.com/liquidcatmofu/discord-tts
```



