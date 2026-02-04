# AutoCheckIn

V2free 自动签到脚本，使用 Selenium + undetected-chromedriver 实现。

## 安装

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 配置

创建 `.env` 文件，添加账号密码：

```
V2FREE_EMAILS=account1@gmail.com,account2@qq.com
V2FREE_PASSWORD=your_password
```

多个邮箱用逗号分隔，所有账号共用同一密码。

## 运行

```bash
./run.sh
```

或手动运行：

```bash
source venv/bin/activate
python V2free.py
```

## 日志

签到结果保存在 `log/V2free.txt`

## 注意事项

- 需要安装 Chrome 浏览器
- macOS 需授予终端辅助功能权限（系统设置 → 隐私与安全性 → 辅助功能）
- 运行时不要最小化浏览器窗口
