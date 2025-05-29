#!/usr/bin/env python3
"""
Linux-Coop: Launch multiple game instances using Proton and Gamescope
"""

from cli.commands import main

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])