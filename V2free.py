import os
import time
import random
import pyautogui
import undetected_chromedriver as uc
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)
from utils import LogWriter

load_dotenv()

# 配置常量
TIMEOUTS = {"alert": 5, "login": 10, "turnstile": 30, "checkin": 3}
CHROME_HEADER_HEIGHT = 85
WEBSITE_URL = "https://w1.v2free.net/auth/login"


def get_chrome_driver():
    """初始化 Chrome WebDriver"""
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    return uc.Chrome(options=options, version_main=144)


def parse_flow(flow_text):
    """解析流量文本为 GB 数值，如 '123.45MB' -> 0.12"""
    unit_map = {"MB": 1/1024, "GB": 1}
    try:
        text = flow_text.strip()
        return float(text[:-2]) * unit_map.get(text[-2:].upper(), 0)
    except (ValueError, IndexError):
        return None


def validate_config(config):
    """验证配置结构"""
    for key in ["logdir", "logfile", "accounts"]:
        if key not in config:
            raise ValueError(f"缺少配置项: {key}")
    if not config["accounts"].get("email"):
        raise ValueError("未配置邮箱账号")
    if not config["accounts"].get("passwd"):
        raise ValueError("未配置密码")


def checkin(accounts, logwriter):
    sum_flow = 0
    driver = None

    try:
        driver = get_chrome_driver()
        logwriter.write(f"开始签到，共 {len(accounts['email'])} 个账号", "INFO")

        for i, email in enumerate(accounts["email"]):
            driver.get(WEBSITE_URL)
            if i == 0:
                driver.maximize_window()

            # 登录
            driver.find_element(By.ID, "email").send_keys(email)
            driver.find_element(By.ID, "passwd").send_keys(accounts["passwd"])
            driver.find_element(By.ID, "login").click()

            # 处理登录弹窗（JavaScript alert）
            try:
                WebDriverWait(driver, TIMEOUTS["alert"]).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                logwriter.write(f"弹窗内容: {alert.text[:50]}...", "INFO")
                alert.accept()
            except TimeoutException:
                pass

            log = email + " "
            login_success = False

            # 验证登录是否成功
            try:
                WebDriverWait(driver, TIMEOUTS["login"]).until(
                    EC.presence_of_element_located((By.ID, "remain"))
                )
                login_success = True
            except TimeoutException:
                log += "登录失败. "
                logwriter.write(log, "ERROR")
                print(log)
                continue

            # 处理登录后确认弹窗
            try:
                btn = WebDriverWait(driver, TIMEOUTS["alert"]).until(
                    EC.element_to_be_clickable((By.ID, "result_ok"))
                )
                btn.click()
                time.sleep(1)
            except TimeoutException:
                pass

            # 检查是否已签到
            already_checked_in = False
            try:
                WebDriverWait(driver, TIMEOUTS["checkin"]).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.btn.btn-brand.disabled"))
                )
                already_checked_in = True
                log += "今日已签到. "
                logwriter.write("已签到，跳过人机验证", "INFO")
            except TimeoutException:
                logwriter.write("未签到，开始验证流程", "INFO")

            # 未签到：处理 Turnstile 验证
            if not already_checked_in:
                try:
                    container = WebDriverWait(driver, TIMEOUTS["turnstile"]).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".cf-turnstile"))
                    )
                    logwriter.write("检测到 Turnstile 验证", "INFO")

                    # 计算点击坐标
                    window = driver.get_window_rect()
                    rect = driver.execute_script(
                        "var r = arguments[0].getBoundingClientRect();"
                        "return {left: r.left, top: r.top, width: r.width, height: r.height};",
                        container
                    )
                    click_x = window['x'] + rect['left'] + 30 + random.randint(-3, 3)
                    click_y = window['y'] + CHROME_HEADER_HEIGHT + rect['top'] + rect['height'] / 2 + random.randint(-3, 3)

                    # 模拟人类点击
                    pyautogui.moveTo(click_x, click_y, duration=random.uniform(0.3, 0.6))
                    time.sleep(random.uniform(0.1, 0.3))
                    pyautogui.click()
                    logwriter.write(f"点击坐标: ({click_x:.0f}, {click_y:.0f})", "INFO")

                    # 等待验证完成
                    WebDriverWait(driver, TIMEOUTS["turnstile"]).until(
                        lambda d: d.find_element(By.CSS_SELECTOR, "input[name='cf-turnstile-response']").get_attribute("value")
                    )
                    logwriter.write("Turnstile 验证完成", "INFO")

                except TimeoutException:
                    logwriter.write("Turnstile 验证超时", "INFO")
                except Exception as e:
                    logwriter.write(f"Turnstile 错误: {e}", "ERROR")

                # 点击签到按钮
                try:
                    btn = WebDriverWait(driver, TIMEOUTS["login"]).until(
                        EC.element_to_be_clickable((By.ID, "checkin"))
                    )
                    btn.click()
                    msg = WebDriverWait(driver, TIMEOUTS["login"]).until(
                        EC.presence_of_element_located((By.ID, "msg"))
                    )
                    log += msg.text + " "
                except TimeoutException:
                    log += "签到超时. "
                except Exception as e:
                    log += f"签到出错: {e}. "

            # 获取剩余流量
            try:
                remain = driver.find_element(By.ID, "remain").text
                log += f"剩余流量：{remain} "
                flow = parse_flow(remain)
                if flow:
                    sum_flow += flow
            except NoSuchElementException:
                log += "流量获取失败. "

            print(log)
            logwriter.write(log, "INFO")
            driver.delete_all_cookies()

    except WebDriverException as e:
        logwriter.write(f"WebDriver错误: {e}", "ERROR")
    except Exception as e:
        logwriter.write(f"未预期错误: {e}", "ERROR")
    finally:
        if driver:
            driver.quit()

    return sum_flow


def main(config):
    validate_config(config)
    t0 = time.time()

    with LogWriter(config["logdir"], config["logfile"]) as logwriter:
        try:
            sum_flow = checkin(config["accounts"], logwriter)
            log = f"剩余总流量：{sum_flow:.2f}GB，运行时间：{time.time() - t0:.2f}s"
            print(log)
            logwriter.write(log, "INFO")
        except Exception as e:
            logwriter.write(f"执行失败: {e}", "ERROR")


if __name__ == "__main__":
    emails = os.getenv("V2FREE_EMAILS", "").split(",")
    passwd = os.getenv("V2FREE_PASSWORD", "")

    config = {
        "logdir": "log",
        "logfile": "V2free.txt",
        "accounts": {
            "email": [e.strip() for e in emails if e.strip()],
            "passwd": passwd
        }
    }
    main(config)
