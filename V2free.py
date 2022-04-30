import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from utils import LogWriter


def checkin(accounts, logwriter):
    sum_flow = 0
    driver = webdriver.Chrome()
    for i in range(len(accounts["email"])):
        driver.get("https://w1.v2free.net/auth/login")
        if i == 0:
            driver.maximize_window()
        driver.find_element(By.ID, "email").send_keys(accounts["email"][i])
        driver.find_element(By.ID, "passwd").send_keys(accounts["passwd"])
        driver.find_element(By.ID, "login").click()

        log = accounts["email"][i]
        try: # check in succeeded
            WebDriverWait(driver, timeout=3).until(lambda x: x.find_element(By.ID, "checkin")).click()
            time.sleep(3)
            log += WebDriverWait(driver, timeout=3).until(lambda x: x.find_element(By.ID, "msg")).text
        except TimeoutException: # check in failed
            log += "今日已签到."
        finally:
            remain_flow = driver.find_element(By.ID, "remain").text
            log += "剩余流量：" + remain_flow
            if remain_flow[-2] == "M":
                sum_flow += float(remain_flow.strip("MB")) / 1024
            elif remain_flow[-2] == "G":
                sum_flow += float(remain_flow.strip("GB"))
        print(log)
        logwriter.write(log)

        driver.delete_all_cookies()
    driver.quit()

    return sum_flow

def main(config):
    t0 = time.time()
    logwriter = LogWriter(config["logdir"], config["logfile"])
    sum_flow = checkin(config["accounts"], logwriter)
    log = "剩余总流量：{:.2f}GB，总运行时间：{:.2f}s\n".format(sum_flow, time.time() - t0)
    print(log)
    logwriter.write(log)
    logwriter.close()

if __name__ == "__main__":
    config = {
        "logdir": "log",
        "logfile": "V2free.txt",
        "accounts": {
	        "email": ["account1@gmail.com", "account2@qq.com"],
	        "passwd": "123456"
        }
    }
    main(config)