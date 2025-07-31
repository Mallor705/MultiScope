#!/usr/bin/env python3
import sys
from src.cli.commands import main as cli_main
from src.gui.app import run_gui

def main():
    args = sys.argv[1:] # Get arguments excluding the script name

    if not args:
        # If no arguments are provided, open the GUI by default
        run_gui()
        return # Exit after launching GUI

    command = args[0]

    # Handle help and version commands
    if command in ["--help", "-h", "help"]:
        print("Linux-Coop - Run Windows games in local cooperative mode on Linux")
        print("")
        print("Usage:")
        print("  linux-coop                    # Open GUI")
        print("  linux-coop gui                # Open GUI")
        print("  linux-coop <profile_name>     # Run profile in CLI mode")
        print("  linux-coop edit <profile_name> # Edit profile")
        print("  linux-coop --help             # Show this help")
        print("  linux-coop --version          # Show version")
        print("")
        print("Examples:")
        print("  linux-coop                    # Open GUI")
        print("  linux-coop Palworld           # Run Palworld profile")
        print("  linux-coop edit Palworld      # Edit Palworld profile")
        return
    elif command in ["--version", "-v", "version"]:
        print("Linux-Coop v2.0.0")
        return

    if command == "gui":
        if len(args) > 1:
            print("Error: The 'gui' command does not accept additional arguments.", file=sys.stderr)
            sys.exit(1)
        run_gui()
    elif command == "edit":
        if len(args) < 2:
            print("Error: The 'edit' command requires the profile name. Usage: linuxcoop.py edit <PROFILE_NAME>", file=sys.stderr)
            sys.exit(1)
        profile_name = args[1]
        cli_main(profile_name, edit_mode=True) # Pass a flag to indicate edit mode
    else:
        # Assume it's a profile name for CLI mode
        if len(args) > 1:
            print(f"Warning: Additional arguments ignored for profile '{command}'.", file=sys.stderr)
        cli_main(command)

if __name__ == "__main__":
    main()
