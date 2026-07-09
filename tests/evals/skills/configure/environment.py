import os
from pathlib import Path

from common.eval import PLUGIN_DIR_ENV


def plugin_dir() -> Path:
    return Path(os.environ[PLUGIN_DIR_ENV])


def luminosity_binary() -> Path:
    return plugin_dir() / "bin" / "luminosity"
