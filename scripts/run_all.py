#!/usr/bin/env python3
"""Thin wrapper for local execution without installation."""

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")

if SRC not in sys.path:
    sys.path.insert(0, SRC)

from async_guard_toy.run_all import main


if __name__ == "__main__":
    main()
