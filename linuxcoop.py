#!/usr/bin/env python3
import sys
from src.cli.commands import main as cli_main
from src.gui.app import run_gui

def main():
    args = sys.argv[1:] # Get arguments excluding the script name

    if not args:
        print("Usage: linuxcoop.py [PROFILE_NAME | gui | edit PROFILE_NAME]")
        print("  PROFILE_NAME: Launch game instances using the specified profile (CLI mode).")
        print("  gui: Launch the Linux-Coop Profile Editor GUI.")
        print("  edit PROFILE_NAME: Edit a game profile in your default text editor.")
        sys.exit(1)
    
    command = args[0]

    if command == "gui":
        if len(args) > 1:
            print("Erro: O comando 'gui' não aceita argumentos adicionais.", file=sys.stderr)
            sys.exit(1)
        run_gui()
    elif command == "edit":
        if len(args) < 2:
            print("Erro: O comando 'edit' requer o nome do perfil. Uso: linuxcoop.py edit <NOME_DO_PERFIL>", file=sys.stderr)
            sys.exit(1)
        profile_name = args[1]
        cli_main(profile_name, edit_mode=True) # Pass a flag to indicate edit mode
    else:
        # Assume it's a profile name for CLI mode
        if len(args) > 1:
            print(f"Aviso: Argumentos adicionais ignorados para o perfil '{command}'.", file=sys.stderr)
        cli_main(command)

if __name__ == "__main__":
    main()