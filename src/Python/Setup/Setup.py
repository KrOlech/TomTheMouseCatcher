import os
import shutil

from src.Python.Settings import Settings


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def copy_file(src, dst):
    ensure_dir(os.path.dirname(dst))
    shutil.copy2(src, dst)
    print(f"Copied {src} to {dst}")

def setUp():
    ensure_dir(Settings.logLocation)
    ensure_dir(Settings.expectedLocation)