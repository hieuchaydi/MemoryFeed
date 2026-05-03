#!/usr/bin/env python
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
cmd = [sys.executable, "setup.py", "build_ext", "--inplace"]
print("Running:", " ".join(cmd))
subprocess.check_call(cmd, cwd=root)
print("Built native module in:", root)
