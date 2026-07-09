import shutil
from typing import TYPE_CHECKING

from common.eval import WORKDIR_PREFIX

if TYPE_CHECKING:
    from pathlib import Path


def cleanup_workdirs(tmp_root: Path) -> int:
    swept = 0
    for path in sorted(tmp_root.glob(f"{WORKDIR_PREFIX}*")):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            swept += 1
    return swept
