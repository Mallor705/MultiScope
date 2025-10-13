#!/usr/bin/env python3
import sys
from src.cli.commands import main as cli_main
from src.gui.app import run_gui
from src.core.config import Config

def main():
    """
    The main entry point for the Proton-Coop application.

    This function parses command-line arguments to determine whether to launch
    the GUI, run the CLI to launch a game profile, or edit a profile. It also
    handles the `--parent-pid` argument for monitoring by a parent process.
    """
    # Run comprehensive migration at startup for all legacy paths (profiles and prefixes)
    Config.migrate_legacy_paths()

    args = sys.argv[1:]
    parent_pid = None

    # Simple manual parsing for --parent-pid
    if "--parent-pid" in args:
        try:
            pid_index = args.index("--parent-pid") + 1
            if pid_index < len(args):
                parent_pid = int(args[pid_index])
                # Remove the flag and its value from args list
                args.pop(pid_index - 1)
                args.pop(pid_index - 1)
            else:
                print("Error: --parent-pid flag requires a value.", file=sys.stderr)
                sys.exit(1)
        except (ValueError, IndexError):
            print("Error: Invalid value for --parent-pid.", file=sys.stderr)
            sys.exit(1)

    if not args:
        run_gui()
        return

    command = args[0]

    if command == "gui":
        run_gui()
    elif command == "edit":
        if len(args) < 2:
            print("Error: 'edit' command requires a profile name.", file=sys.stderr)
            sys.exit(1)
        cli_main(args[1], edit_mode=True)
    else:
        cli_main(command, parent_pid=parent_pid)

if __name__ == "__main__":
    main()
