import os
import shutil
from abc import ABC, abstractmethod

class SetupUni(ABC):

    def __init__(self, loger):
        self.logingApp = loger

    def ensure_dir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
            self.logingApp.loger(f"Created directory: {path}")

    def copy_file(self, src, dst):
        self.ensure_dir(os.path.dirname(dst))
        shutil.copy2(src, dst)
        self.logingApp.loger(f"Copied {src} to {dst}")

    @abstractmethod
    def setUp(self):
        ...
