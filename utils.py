import os
import json
import hashlib
from datetime import datetime


class LogWriter:
    """日志写入器，支持 with 语句"""

    def __init__(self, logdir, logfile):
        os.makedirs(logdir, exist_ok=True)
        self.fout = open(os.path.join(logdir, logfile), "a", encoding="utf-8")
        self.fout.write(f"\n{'='*60}\n{datetime.now():%Y-%m-%d %H:%M:%S}\n{'='*60}\n")

    def write(self, text, level="INFO"):
        self.fout.write(f"[{datetime.now():%H:%M:%S}] [{level}] {text}\n")
        self.fout.flush()

    def close(self):
        self.fout.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class CookieManager:
    """Cookie 管理器，负责保存和加载 cookies"""

    def __init__(self, cookie_dir="cookies"):
        """初始化 Cookie 管理器

        Args:
            cookie_dir: Cookie 存储目录，默认为 cookies/
        """
        self.cookie_dir = cookie_dir
        self.cookie_file = os.path.join(cookie_dir, "v2free_cookies.json")
        os.makedirs(cookie_dir, exist_ok=True)

    def _load_all_cookies(self):
        """从统一 JSON 文件加载所有账号的 cookies

        Returns:
            dict: {email: cookies_list} 格式的字典，文件不存在返回空字典
        """
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            print(f"统一 Cookie 文件损坏，将重新创建")
            return {}

    def _save_all_cookies(self, all_cookies):
        """保存所有账号的 cookies 到统一 JSON 文件

        Args:
            all_cookies: {email: cookies_list} 格式的字典

        Returns:
            bool: 是否保存成功
        """
        try:
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(all_cookies, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存统一 Cookie 文件失败: {e}")
            return False

    def has_cookies(self, email):
        """检查账号是否有 cookies"""
        all_cookies = self._load_all_cookies()
        return email in all_cookies and len(all_cookies[email]) > 0

    def save_cookies(self, driver, email):
        """保存单个账号的 cookies 到统一文件"""
        try:
            # 1. 加载所有账号的 cookies
            all_cookies = self._load_all_cookies()

            # 2. 更新当前账号
            all_cookies[email] = driver.get_cookies()

            # 3. 保存回文件
            return self._save_all_cookies(all_cookies)
        except Exception as e:
            print(f"保存 Cookie 失败 ({email}): {e}")
            return False

    def load_cookies(self, driver, email):
        """从统一 JSON 文件加载单个账号的 cookies"""
        try:
            # 1. 加载所有账号的 cookies
            all_cookies = self._load_all_cookies()

            # 2. 检查是否存在该账号
            if email not in all_cookies:
                return False

            cookies = all_cookies[email]

            # 3. 清除现有 cookies
            driver.delete_all_cookies()

            # 4. 添加保存的 cookies
            for cookie in cookies:
                # JSON 反序列化后，expiry 是整数，安全移除
                cookie.pop('expiry', None)
                driver.add_cookie(cookie)

            return True
        except json.JSONDecodeError:
            print(f"统一 Cookie 文件损坏，将删除该账号: {email}")
            self.delete_cookies(email)
            return False
        except Exception as e:
            print(f"加载 Cookie 失败 ({email}): {e}")
            return False

    def delete_cookies(self, email):
        """从统一文件中删除单个账号的 cookies"""
        try:
            # 1. 加载所有账号的 cookies
            all_cookies = self._load_all_cookies()

            # 2. 删除指定账号
            if email in all_cookies:
                del all_cookies[email]
                # 3. 保存回文件
                return self._save_all_cookies(all_cookies)

            return True  # 本来就不存在，视为成功
        except Exception as e:
            print(f"删除 Cookie 失败 ({email}): {e}")
            return False
