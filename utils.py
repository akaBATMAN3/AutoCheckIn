import os
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
