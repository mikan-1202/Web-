# 📝 自動投稿スクリプト

> Seleniumを使用して、指定URLへの自動ログイン＋投稿を行うPythonスクリプトです。ログイン情報や投稿メッセージはローカルに安全に保存され、任意のスレッドに自動投稿を繰り返します。

## 🚀 機能概要 / Features

- ✅ ユーザー認証付き掲示板への自動ログイン（Cookie確認あり）
- ✅ `dict.txt`からランダムな投稿文を選択して投稿
- ✅ 投稿間隔をランダム化（人間っぽい挙動）
- ✅ Selenium + ChromeDriverによるブラウザ制御
- ✅ ログイン情報をBase64でローカル保存（`credentials.json`）
- ✅ 投稿失敗時にリトライ処理あり

---

## 📁 構成 / File Structure

├─ main.py # メインスクリプト
├─ dict.txt # 投稿文が区切り文字で入ったテキストファイル
├─ credentials.json # ログイン情報（初回保存される）
├─ chromedriver.exe # Chrome用WebDriver（バージョン合わせる必要あり）
├─ requirements.txt # 使用ライブラリ一覧

---

## 🔧 事前準備 / Setup

### 1. 必要なライブラリのインストール
```bash
pip install -r requirements.txt
