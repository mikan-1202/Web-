import sys
import time
import random
import re
import os
import contextlib
import base64
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ==== 設定定数 ====
CREDENTIALS_FILE = "credentials.json"
MESSAGE_FILE_PATH = "dict.txt"
CHROMEDRIVER_PATH = "./chromedriver.exe"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
)
WAIT_TIMEOUT = 10
POST_INTERVAL_RANGE = (30, 36)
MESSAGE_DELIMITER = "---"


# ==== ユーティリティ ====
@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr


def load_messages(file_path, delimiter=MESSAGE_DELIMITER):
    try:
        with open(file_path, encoding="utf-8") as f:
            raw = f.read()
        messages = [msg.strip() for msg in raw.split(delimiter) if msg.strip()]
        if not messages:
            raise ValueError("メッセージファイルが空です。")
        return messages
    except Exception as e:
        sys.exit(f"[ERR] メッセージ読込エラー: {e}")


def choose_message(messages, prev=None):
    pool = [m for m in messages if m != prev]
    return random.choice(pool or messages)


def save_credentials(email, password):
    creds = {
        "email": base64.b64encode(email.encode()).decode(),
        "password": base64.b64encode(password.encode()).decode()
    }
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(creds, f)


def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        return None, None
    with open(CREDENTIALS_FILE) as f:
        creds = json.load(f)
    try:
        email = base64.b64decode(creds["email"]).decode()
        password = base64.b64decode(creds["password"]).decode()
        return email, password
    except Exception:
        return None, None


# ==== Selenium関連 ====
def init_driver(proxy=None):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_argument(f"user-agent={DEFAULT_USER_AGENT}")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")

    service = Service(executable_path=CHROMEDRIVER_PATH, log_path=os.devnull)
    with suppress_stderr():
        return webdriver.Chrome(service=service, options=options)


def clear_and_send_keys(driver, by, selector, text, timeout=WAIT_TIMEOUT):
    try:
        elem = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        elem.clear()
        elem.send_keys(text)
    except TimeoutException:
        print(f"[WARN] 要素が見つかりません: {selector}")
        raise


def try_get(driver, url, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            with suppress_stderr():
                driver.get(url)
            return True
        except Exception as e:
            print(f"[⚠️] driver.get()失敗（{attempt + 1}回目）: {type(e).__name__} - {e}")
            time.sleep(2)
    return False


def is_logged_in(driver):
    cookies = driver.get_cookies()
    cookie_names = {cookie['name'] for cookie in cookies}
    return 'DANGO' in cookie_names and 'PON' in cookie_names


def login_donguri(driver, email, password):
    login_url = "https://login.exsample"  # 正確なログインURLに変更する必要あり
    driver.get(login_url)

    try:
        clear_and_send_keys(driver, By.NAME, "login_email", email)
        clear_and_send_keys(driver, By.NAME, "login_password", password)
        submit = driver.find_element(By.NAME, "login")
        driver.execute_script("arguments[0].click();", submit)

        time.sleep(2)  # 少し待機してからログイン判定

        if is_logged_in(driver):
            print("[✅] ログイン成功（クッキー取得確認済）")
        else:
            sys.exit("[❌] ログイン失敗：IDまたはパスワードが無効、または仕様変更の可能性あり")

    except Exception as e:
        sys.exit(f"[ERR] ログイン処理中にエラー発生: {e}")


def post_message_once(driver, message, base_url, bbs, key, email=None, password=None, proxy=None):
    url = f"{base_url}/test/read.cgi/{bbs}/{key}/"

    if not try_get(driver, url):
        print("[🔁] driverを再起動して再試行します")
        driver.quit()
        driver = init_driver(proxy)
        if email and password:
            login_donguri(driver, email, password)
        if not try_get(driver, url):
            print("[🔥] driver.get() に再試行しても失敗しました")
            return driver

    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.NAME, "mail"))
        )
        clear_and_send_keys(driver, By.NAME, "mail", "sage")
        clear_and_send_keys(driver, By.NAME, "MESSAGE", message)

        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"][value="書き込む"]')
            driver.execute_script("arguments[0].click();", submit_btn)
        except NoSuchElementException:
            print("[⚠️] 書き込みボタンが見つかりません")
            return driver

        try:
            confirm_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"][value*="承諾して書き込む"]'))
            )
            print("[⚠️] 承諾ボタンをクリック")
            driver.execute_script("arguments[0].click();", confirm_btn)
        except TimeoutException:
            pass

        print(f"[✅] 投稿成功: {message}")

    except (TimeoutException, NoSuchElementException) as e:
        print(f"[🔥] 投稿処理中のエラー: {type(e).__name__} - {e}")

    return driver


# ==== メイン処理 ====
def parse_url():
    url = input("投稿先のURLを貼ってください:\n> ").strip()
    match = re.search(r"https?://([^/]+).*-----------/([^/]+)/(\d+)", url) #安全保障のため一部伏字
    if not match:
        sys.exit("[ERR] URL形式が不正です")
    return f"https://{match.group(1)}", match.group(2), match.group(3)


def main():
    base_url, bbs, key = parse_url()
    messages = load_messages(MESSAGE_FILE_PATH)
    prev = None

    email, password = load_credentials()
    if not email or not password:
        email = input("アカウントのメールアドレス:\n> ")
        password = input("パスワード:\n> ")
        save_credentials(email, password)

    driver = init_driver()
    login_donguri(driver, email, password)

    if not is_logged_in(driver):
        sys.exit("[❌] ログインに失敗しました。")

    try:
        while True:
            msg = choose_message(messages, prev)
            driver = post_message_once(driver, msg, base_url, bbs, key, email, password)
            prev = msg

            wait = random.uniform(*POST_INTERVAL_RANGE)
            print(f"[⏱] 次の投稿まで {round(wait, 1)} 秒待機")
            time.sleep(wait)
    except KeyboardInterrupt:
        print("\n[INFO] 中断されました")
    finally:
        driver.quit()
        input("終了するにはEnterを押してください...")



if __name__ == "__main__":
    main()
