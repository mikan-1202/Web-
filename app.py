import sys,time,random,re,os,contextlib,base64,json
sys.stderr=open("error.log","a",encoding="utf-8")
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException,NoSuchElementException

LOG_FILE="error.log"
CREDENTIALS_FILE="credentials.json"
MESSAGE_FILE_PATH="dict.txt"
CHROMEDRIVER_PATH="./chromedriver.exe"
DEFAULT_USER_AGENT=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
" (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
WAIT_TIMEOUT=10
MESSAGE_DELIMITER="---"

@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull,"w") as devnull:
        old_stderr=sys.stderr
        sys.stderr=devnull
        try: yield
        finally: sys.stderr=old_stderr

def ask_post_interval():
    try:
        min_sec = float(input("投稿間隔の最小秒数:\n> "))
        max_sec = float(input("投稿間隔の最大秒数:\n> "))
        if min_sec > max_sec or min_sec < 0:
            raise ValueError("不正な範囲です")
        return min_sec, max_sec
    except Exception as e:
        exit_with_error(f"投稿間隔の入力エラー: {e}")

def load_messages(file_path,delimiter=MESSAGE_DELIMITER):
    try:
        with open(file_path,encoding="utf-8") as f: raw=f.read()
        messages=[msg.strip() for msg in raw.split(delimiter) if msg.strip()]
        if not messages: raise ValueError("メッセージファイルが空です。")
        return messages
    except Exception as e: exit_with_error(f"メッセージ読込エラー: {e}")

def choose_message(messages,previous=None):
    candidates=[m for m in messages if m!=previous]
    return random.choice(candidates or messages)

def init_driver(proxy=None):
    options=Options()
    options.add_argument("--log-level=3")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--disable-voice-input")
    options.add_argument("--mute-audio")
    options.add_argument(f"user-agent={DEFAULT_USER_AGENT}")
    if proxy: options.add_argument(f"--proxy-server={proxy}")
    service=Service(executable_path=CHROMEDRIVER_PATH,log_path=os.devnull)
    with suppress_stderr(): return webdriver.Chrome(service=service,options=options)

def detect_board_encoding_selenium(base_url,bbs,driver):
    setting_url=f"{base_url}/{bbs}/SETTING.TXT"
    try:
        driver.get(setting_url)
        pre_elements=driver.find_elements(By.TAG_NAME,"pre")
        text=pre_elements[0].text if pre_elements else driver.page_source
        for line in text.splitlines():
            if line.startswith("BBS_UNICODE"):
                _,value=line.split("=",1)
                return value.strip().lower()=="change"
        print("[ℹ️] BBS_UNICODE設定が見つかりません。Shift_JISと仮定します。")
        return False
    except Exception as e:
        print(f"[⚠️] SETTING.TXT読み込み失敗: {e}")
        return False

def contains_surrogate_pairs(text):
    return any(0xD800<=ord(c)<=0xDFFF or ord(c)>0xFFFF for c in text)

def save_credentials(email,password):
    creds={"email":base64.b64encode(email.encode()).decode(),"password":base64.b64encode(password.encode()).decode()}
    with open(CREDENTIALS_FILE,"w") as f: json.dump(creds,f)

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE): return None,None
    with open(CREDENTIALS_FILE) as f: creds=json.load(f)
    try:
        email=base64.b64decode(creds["email"]).decode()
        password=base64.b64decode(creds["password"]).decode()
        return email,password
    except Exception: return None,None

def clear_and_send_keys(driver,by,selector,text,timeout=WAIT_TIMEOUT):
    elem=WebDriverWait(driver,timeout).until(EC.presence_of_element_located((by,selector)))
    elem.clear()
    elem.send_keys(text)

def try_get(driver,url,max_attempts=3):
    for attempt in range(max_attempts):
        try:
            with suppress_stderr(): driver.get(url)
            return True
        except Exception as e:
            print(f"[⚠️] driver.get()失敗（{attempt+1}回目）: {type(e).__name__} - {e}")
            time.sleep(2)
    return False

def is_logged_in(driver):
    try:
        driver.find_element(By.XPATH,'//h1[text()="どんぐり基地"]')
        return True
    except NoSuchElementException: return False

def login_donguri(driver,email,password):
    driver.get("https://donguri.5ch.net/")
    try:
        clear_and_send_keys(driver,By.NAME,"email",email)
        clear_and_send_keys(driver,By.NAME,"pass",password)
        submit=driver.find_element(By.XPATH,'//button[text()="ログインする"]')
        driver.execute_script("arguments[0].click();",submit)
        time.sleep(2)
        if is_logged_in(driver): print("[✅] ログイン成功")
        else: exit_with_error("ログイン失敗：IDまたはパスワードが無効か仕様変更の可能性")
    except Exception as e: exit_with_error(f"ログイン処理中のエラー: {e}")

def post_message_once(driver,message,base_url,bbs,key):
    url=f"{base_url}/test/read.cgi/{bbs}/{key}/"
    try:
        if not try_get(driver,url): raise Exception("ページ読み込み失敗")
        WebDriverWait(driver,WAIT_TIMEOUT).until(EC.presence_of_element_located((By.NAME,"mail")))
        clear_and_send_keys(driver,By.NAME,"mail","sage")
        clear_and_send_keys(driver,By.NAME,"MESSAGE",message)
        submit_btn=driver.find_element(By.CSS_SELECTOR,'input[type="submit"][value="書き込む"]')
        driver.execute_script("arguments[0].click();",submit_btn)
        try:
            confirm_btn=WebDriverWait(driver,3).until(EC.element_to_be_clickable((By.CSS_SELECTOR,'input[type="submit"][value*="承諾して書き込む"]')))
            print("[⚠️] 承諾ボタンをクリック")
            driver.execute_script("arguments[0].click();",confirm_btn)
        except TimeoutException: pass
        print(f"[✅] 投稿成功: {message}")
        return driver,False
    except Exception as e:
        print(f"[🔥] 投稿処理中エラー: {type(e).__name__} - {e}")
        return driver,True

def parse_url():
    url=input("投稿先スレッドのURLを貼ってください:\n> ").strip()
    match=re.search(r"https?://([^/]+).*/test/read\.cgi/([^/]+)/(\d+)",url)
    if not match: exit_with_error("URL形式が不正です")
    return f"https://{match.group(1)}",match.group(2),match.group(3)

def write_log(message):
    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE,"a",encoding="utf-8") as f: f.write(f"[{timestamp}] {message}\n")

def ensure_log_file_exists():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE,"w",encoding="utf-8") as f: f.write("")

def exit_with_error(message):
    print(f"[ERR] {message}")
    write_log(message)
    input("終了するにはEnterを押してください...")
    sys.exit(1)

def main():
    ensure_log_file_exists()
    base_url,bbs,key=parse_url()
    POST_INTERVAL_RANGE = ask_post_interval()
    email,password=load_credentials()
    if not email or not password:
        email=input("どんぐりアカウントのメールアドレス:\n> ")
        password=input("パスワード:\n> ")
        save_credentials(email,password)
    driver=init_driver()
    login_donguri(driver,email,password)
    if not is_logged_in(driver): exit_with_error("ログインに失敗しました。")
    messages=load_messages(MESSAGE_FILE_PATH)
    prev=None
    is_unicode_supported=detect_board_encoding_selenium(base_url,bbs,driver)
    print(f"[📘] 板のUnicode対応: {'あり（UTF-8）' if is_unicode_supported else 'なし（Shift_JIS）'}")
    try:
        while True:
            valid_messages=[m for m in messages if is_unicode_supported or not contains_surrogate_pairs(m)]
            if not valid_messages: exit_with_error("有効なメッセージがありません（絵文字を含むためスキップ）")
            msg=choose_message(valid_messages,prev)
            driver,should_restart=post_message_once(driver,msg,base_url,bbs,key)
            if should_restart:
                print("[🔄] driverを再起動しています...")
                driver.quit()
                time.sleep(5)
                driver=init_driver()
                login_donguri(driver,email,password)
                continue
            prev=msg
            wait=random.uniform(*POST_INTERVAL_RANGE)
            print(f"[⏱] 次の投稿まで {wait:.1f} 秒待機")
            time.sleep(wait)
    except KeyboardInterrupt:
        print("\n[INFO] 中断されました")
    except Exception as e:
        exit_with_error(f"未処理例外発生: {type(e).__name__} - {e}")
    finally:
        try: driver.quit()
        except Exception: pass
        input("終了するにはEnterを押してください...")

if __name__=="__main__":
    main()
