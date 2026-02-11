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
from utils import LogWriter, CookieManager

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


def verify_cookie_login(driver, logwriter):
    """验证 cookie 登录是否成功

    通过检查用户中心的特征元素来判断 cookie 是否有效
    """
    try:
        # 导航到用户中心
        driver.get("https://w1.v2free.net/user")

        # 处理可能出现的浏览器弹窗
        try:
            WebDriverWait(driver, TIMEOUTS["alert"]).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            logwriter.write(f"Cookie验证时出现弹窗: {alert.text[:50]}...", "INFO")
            alert.accept()
            time.sleep(0.5)
        except TimeoutException:
            pass  # 没有弹窗，继续

        # 处理 result_ok 确认按钮（如果存在）
        try:
            btn = WebDriverWait(driver, TIMEOUTS["login"]).until(
                EC.element_to_be_clickable((By.ID, "result_ok"))
            )
            btn.click()
            logwriter.write("Cookie验证：已点击 result_ok 确认按钮", "INFO")
            time.sleep(1)
        except TimeoutException:
            pass  # 没有 result_ok 按钮，继续

        # 检查特征元素：剩余流量显示（用户中心特有）
        WebDriverWait(driver, TIMEOUTS["checkin"]).until(
            EC.presence_of_element_located((By.ID, "remain"))
        )

        # # 双重验证：确保签到按钮也存在
        # WebDriverWait(driver, TIMEOUTS["checkin"]).until(
        #     lambda d: d.find_element(By.ID, "checkin") or
        #              d.find_element(By.CSS_SELECTOR, "a.btn.btn-brand.disabled")
        # )

        logwriter.write("Cookie 验证通过", "INFO")
        return True

    except TimeoutException:
        logwriter.write("Cookie 验证失败：未找到用户中心元素", "INFO")
        return False
    except Exception as e:
        logwriter.write(f"Cookie 验证异常: {e}", "ERROR")
        return False


def perform_full_login(driver, email, password, logwriter):
    """执行完整的 5 步登录流程

    这是原第 69-113 行的登录逻辑，提取为独立函数
    """
    # 清除浏览器中的所有 cookie，确保干净状态
    logwriter.write("→ 清除浏览器 Cookie，准备完整登录", "INFO")
    driver.delete_all_cookies()

    # 导航到登录页
    logwriter.write("→ 步骤0：开始访问登录页", "INFO")
    driver.get(WEBSITE_URL)
    logwriter.write("→ 步骤0：登录页加载完成", "INFO")

    # 输入凭证
    logwriter.write("→ 准备输入邮箱", "INFO")
    driver.find_element(By.ID, "email").send_keys(email)
    logwriter.write("→ 邮箱输入完成", "INFO")

    logwriter.write("→ 准备输入密码", "INFO")
    driver.find_element(By.ID, "passwd").send_keys(password)
    logwriter.write("→ 密码输入完成", "INFO")

    logwriter.write("→ 准备点击登录按钮", "INFO")
    driver.find_element(By.ID, "login").click()
    logwriter.write("→ 登录按钮已点击", "INFO")

    # 步骤1：处理第一波浏览器弹窗（登录后）
    try:
        WebDriverWait(driver, TIMEOUTS["alert"]).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        logwriter.write(f"登录后弹窗: {alert.text[:50]}...", "INFO")
        alert.accept()
        time.sleep(0.5)
    except TimeoutException:
        pass

    # 步骤2：等待并点击 result_ok 确认按钮
    try:
        btn = WebDriverWait(driver, TIMEOUTS["login"]).until(
            EC.element_to_be_clickable((By.ID, "result_ok"))
        )
        btn.click()
        logwriter.write("已点击 result_ok 确认登录", "INFO")
        time.sleep(1)  # 等待页面跳转
    except TimeoutException:
        logwriter.write("未找到 result_ok 按钮，跳过", "INFO")

    # 步骤3：处理第二波浏览器弹窗（跳转后）
    try:
        WebDriverWait(driver, TIMEOUTS["alert"]).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        logwriter.write(f"跳转后弹窗: {alert.text[:50]}...", "INFO")
        alert.accept()
        time.sleep(0.5)
    except TimeoutException:
        pass

    # 步骤4：再次点击 result_ok 确认按钮
    try:
        btn = WebDriverWait(driver, TIMEOUTS["login"]).until(
            EC.element_to_be_clickable((By.ID, "result_ok"))
        )
        btn.click()
        logwriter.write("已再次点击 result_ok 确认按钮", "INFO")
        time.sleep(1)
    except TimeoutException:
        logwriter.write("未找到第二个 result_ok 按钮，跳过", "INFO")

    return True


def login_with_cookie_fallback(driver, email, password, cookie_manager, logwriter):
    """优先使用 Cookie 登录，失败则回退到完整登录

    Args:
        driver: WebDriver 实例
        email: 账号邮箱
        password: 账号密码
        cookie_manager: CookieManager 实例
        logwriter: LogWriter 实例

    Returns:
        bool: 登录是否成功
    """
    # 1. 检查是否有保存的 cookies
    if cookie_manager.has_cookies(email):
        logwriter.write(f"发现 Cookie 缓存，尝试快速登录", "INFO")

        # 2. 加载 cookies（必须先访问域名）
        driver.get("https://w1.v2free.net")
        cookie_manager.load_cookies(driver, email)

        # 3. 验证 cookies 有效性
        if verify_cookie_login(driver, logwriter):
            logwriter.write("Cookie 登录成功，跳过完整登录流程（节省 ~17s）", "INFO")
            return True
        else:
            logwriter.write("Cookie 已失效，删除无效缓存", "INFO")
            cookie_manager.delete_cookies(email)

    # 4. 回退到完整登录
    logwriter.write("执行完整登录流程", "INFO")
    perform_full_login(driver, email, password, logwriter)

    cookie_manager.save_cookies(driver, email)
    logwriter.write("已保存新 Cookie 到本地", "INFO")
    return True


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
    cookie_manager = CookieManager()

    try:
        driver = get_chrome_driver()
        logwriter.write(f"开始签到，共 {len(accounts['email'])} 个账号", "INFO")

        for i, email in enumerate(accounts["email"]):
            if i == 0:
                driver.maximize_window()

            # 使用 Cookie 优先登录（替代原完整登录流程）
            if not login_with_cookie_fallback(
                driver, email, accounts["passwd"],
                cookie_manager, logwriter
            ):
                log = email + " 登录失败，跳过此账号"
                logwriter.write(log, "ERROR")
                print(log)
                continue  # 跳过失败的账号，继续处理下一个

            log = email + " "

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
                    time.sleep(1)  # 等待签到请求提交，防止点击过快导致表单未提交
                    msg = WebDriverWait(driver, TIMEOUTS["login"]).until(
                        EC.presence_of_element_located((By.ID, "result_ok"))
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
            # Cookie 已在登录时保存，不再需要清除

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
