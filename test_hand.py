import os
import time
import pytest

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

CHROME_BIN = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")

HEADLESS = os.getenv("HEADLESS", "false").lower() == "false"
TIMEOUT = 25

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

    service = Service("/usr/bin/chromedriver")
    d = webdriver.Chrome(service=service, options=opts)
    yield d
    d.quit()

OPENBMC_URL = os.getenv("OPENBMC_URL", "https://127.0.0.1:2443").rstrip("/")
OPENBMC_USER = os.getenv("OPENBMC_USER", "root")
OPENBMC_PASS = os.getenv("OPENBMC_PASS", "0penBmc")

def test_login_success(driver):
    driver.get(f"{OPENBMC_URL}/#/login")
    wait = WebDriverWait(driver, TIMEOUT)
    time.sleep(5)
    user_input = driver.find_element(By.ID, "username")
    pass_input = driver.find_element(By.ID, "password")
    submit_btn = driver.find_element(By.XPATH, '//*[@id="app"]/main/div/div[1]/div/form/button')

    user_input.clear()
    user_input.send_keys(OPENBMC_USER)
    pass_input.clear()
    pass_input.send_keys(OPENBMC_PASS)
    submit_btn.click()
    time.sleep(5)
    assert driver.current_url != f"{OPENBMC_URL}/#/login"

WRONG_PASS = os.getenv("WRONG_PASS", "totally_wrong_password")
def test_login_invalid_credentials(driver):
    driver.get(f"{OPENBMC_URL}/#/login")
    wait = WebDriverWait(driver, TIMEOUT)

    user_input = driver.find_element(By.ID, "username")
    pass_input = driver.find_element(By.ID, "password")
    submit_btn = driver.find_element(By.XPATH, '//*[@id="app"]/main/div/div[1]/div/form/button')

    user_input.clear()
    user_input.send_keys(OPENBMC_USER)
    pass_input.clear()
    pass_input.send_keys(WRONG_PASS)
    submit_btn.click()
    time.sleep(5)

    assert "/login" in driver.current_url, f"Ожидали остаться на странице логина, URL: {driver.current_url}"

def test_poweron(driver):
    driver.get(f"{OPENBMC_URL}/#/login")
    wait = WebDriverWait(driver, TIMEOUT)
    time.sleep(3)
    user_input = driver.find_element(By.ID, "username")
    pass_input = driver.find_element(By.ID, "password")
    submit_btn = driver.find_element(By.XPATH, '//*[@id="app"]/main/div/div[1]/div/form/button')

    user_input.clear()
    user_input.send_keys(OPENBMC_USER)
    pass_input.clear()
    pass_input.send_keys(OPENBMC_PASS)
    submit_btn.click()
    time.sleep(3)

    driver.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div/nav/ul/li[4]/button').click()
    time.sleep(1)
    driver.find_element(By.XPATH, '//*[@id="operations"]/li/a[7]').click()
    time.sleep(3)
    driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[3]/div[2]/div/button').click()
    result_div = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div[3]/div[2]/div/div')
    assert result_div.text == "There are no options to display while a power operation is in progress. When complete, power operations will be displayed here."

def test_get_logs(driver):
    driver.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div/nav/ul/li[2]/button').click()
    time.sleep(1)
    driver.find_element(By.XPATH, '//*[@id="logs"]/li/a[1]').click()
    time.sleep(3)
    logs_table = driver.find_element(By.XPATH, '//*[@id="table-event-logs"]/tbody/tr/td/div/div')
    assert logs_table.text == "No items available"