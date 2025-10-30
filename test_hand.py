import os
import time
import pytest

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


CHROME_BIN = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

HEADLESS = os.getenv("HEADLESS", "false").lower() == "false"
TIMEOUT = 25

def wait_visible(driver, by, value, timeout=25):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((by, value))
    )

def wait_clickable(driver, by, value, timeout=25):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )

def safe_click(driver, element):
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        driver.execute_script("arguments[0].click();", element)

@pytest.fixture(scope="session")
def driver():
    opts = Options()
    # без headless
    opts.add_argument("--start-maximized")
    opts.add_experimental_option("detach", True)

    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.set_capability("acceptInsecureCerts", True)
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--allow-insecure-localhost")

    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-features=BlockInsecurePrivateNetworkRequests")


    service = Service("/usr/bin/chromedriver")
    d = webdriver.Chrome(service=service, options=opts)
    yield d
    d.quit()

OPENBMC_URL = os.getenv("OPENBMC_URL", "https://127.0.0.1:2443").rstrip("/")
OPENBMC_USER = os.getenv("OPENBMC_USER", "root")
OPENBMC_PASS = os.getenv("OPENBMC_PASS", "0penBmc")

def test_login_success(driver):
    driver.get(f"{OPENBMC_URL}/#/login")

    user_input = wait_visible(driver, By.ID, "username")
    pass_input = wait_visible(driver, By.ID, "password")
    submit_btn = wait_clickable(driver, By.XPATH, '//*[@id="app"]/main/div/div[1]/div/form/button')

    user_input.clear(); user_input.send_keys(OPENBMC_USER)
    pass_input.clear(); pass_input.send_keys(OPENBMC_PASS)
    safe_click(driver, submit_btn)

    # ждём ухода со страницы логина ИЛИ появления главной
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: d.current_url.rstrip("/") not in {f"{OPENBMC_URL}/#/login".rstrip("/")}
                   or d.current_url.rstrip("/") == f"{OPENBMC_URL}/#/".rstrip("/")
    )

    # итоговая проверка: мы либо на главной "#/", либо хотя бы уже не на "#/login"
    assert "/#/login" not in driver.current_url


WRONG_PASS = os.getenv("WRONG_PASS", "totally_wrong_password")

def test_login_invalid_credentials(driver):
    driver.get(f"{OPENBMC_URL}/#/login")

    user_input = wait_visible(driver, By.ID, "username")
    pass_input = wait_visible(driver, By.ID, "password")
    submit_btn = wait_clickable(driver, By.XPATH, '//*[@id="app"]/main/div/div[1]/div/form/button')

    user_input.clear(); user_input.send_keys(OPENBMC_USER)
    pass_input.clear(); pass_input.send_keys(WRONG_PASS)
    safe_click(driver, submit_btn)

    WebDriverWait(driver, TIMEOUT).until(lambda d: d.current_url != f"{OPENBMC_URL}/#/login" or d.current_url == f"{OPENBMC_URL}/#/login")

    # допускаем два корректных исхода: 1) остались на странице логина; 2) появился явный алерт/ошибка
    stayed_on_login = "/#/login" in driver.current_url
    error_hint = False
    try:
        # разные варианты селекторов тоста/алерта — на всякий случай
        err = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(@class,'alert') or contains(@class,'toast') or contains(text(),'invalid') or contains(text(),'Incorrect') or contains(text(),'Ошибка')]"))
        )
        error_hint = err is not None
    except Exception:
        pass

    assert stayed_on_login or error_hint, f"Ожидали ошибку логина, но URL: {driver.current_url}"

def test_poweron(driver):
    driver.get(f"{OPENBMC_URL}/#/login")

    user_input = wait_visible(driver, By.ID, "username")
    pass_input = wait_visible(driver, By.ID, "password")
    submit_btn = wait_clickable(driver, By.XPATH, '//*[@id="app"]/main/div/div[1]/div/form/button')

    user_input.clear(); user_input.send_keys(OPENBMC_USER)
    pass_input.clear(); pass_input.send_keys(OPENBMC_PASS)
    safe_click(driver, submit_btn)

    WebDriverWait(driver, TIMEOUT).until(lambda d: "/#/login" not in d.current_url)

    # меню "Server control" (старые XPATH’ы часто ломаются; оставим, но с ожиданиями)
    nav_btn = wait_clickable(driver, By.XPATH, '//*[@id="app"]/div/div[2]/div/nav/ul/li[4]/button')
    safe_click(driver, nav_btn)
    time.sleep(1)
    power_item = wait_clickable(driver, By.XPATH, '//*[@id="operations"]/li/a[7]')
    safe_click(driver, power_item)

    # кнопка Power On
    power_btn = wait_clickable(driver, By.XPATH, '//*[@id="main-content"]/div/div[3]/div[2]/div/button')
    safe_click(driver, power_btn)

    result_div = wait_visible(driver, By.XPATH, '//*[@id="main-content"]/div/div[3]/div[2]/div/div')
    assert "power operation is in progress" in result_div.text or "no options to display" in result_div.text.lower()

def test_get_logs(driver):
    # Ожидаем, что сессия уже залогинена после предыдущего теста
    logs_menu = wait_clickable(driver, By.XPATH, '//*[@id="app"]/div/div[2]/div/nav/ul/li[2]/button')
    safe_click(driver, logs_menu)
    time.sleep(1)
    logs_item = wait_clickable(driver, By.XPATH, '//*[@id="logs"]/li/a[1]')
    safe_click(driver, logs_item)

    logs_table = wait_visible(driver, By.XPATH, '//*[@id="table-event-logs"]/tbody/tr/td/div/div')
    assert "No items available" in logs_table.text

