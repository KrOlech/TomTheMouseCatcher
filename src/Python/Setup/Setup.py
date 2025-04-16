import os
import shutil

from src.Python.Loger.Loger import Loger
from src.Python.Settings import Settings


class Setup(Loger):

    def ensure_dir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
            self.loger(f"Created directory: {path}")

    def copy_file(self, src, dst):
        self.ensure_dir(os.path.dirname(dst))
        shutil.copy2(src, dst)
        self.loger(f"Copied {src} to {dst}")

    def setUp(self):
        self.ensure_dir(Settings.dataLocation)
        self.ensure_dir(Settings.expectedLocation)
        self.ensure_dir(Settings.logLocation)
