"""Resolving the staged plugin the solver drives and the scorer re-reads.

Kept in a leaf module so the solver and scorer share it without a cycle. The
task layer stages a plugin tree (real launcher at bin/luminosity) and exports
its path via ``LUMINOSITY_EVAL_PLUGIN_DIR``; both read it here at run time.
"""

import os
from pathlib import Path

PLUGIN_DIR_ENV = "LUMINOSITY_EVAL_PLUGIN_DIR"


def plugin_dir() -> Path:
    return Path(os.environ[PLUGIN_DIR_ENV])


def luminosity_binary() -> Path:
    return plugin_dir() / "bin" / "luminosity"
