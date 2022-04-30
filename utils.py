import os
import datetime as dt


class LogWriter:
    def __init__(self, logdir, logfile):
        os.makedirs(logdir, exist_ok=True)
        self.fout = open(os.path.join(logdir, logfile), "a")
        self.fout.writelines("\n" + dt.datetime.now().strftime('%F %T') + "\n")

    def write(self, text):
        self.fout.writelines(text + "\n")
        self.fout.flush()

    def close(self):
        self.fout.close()