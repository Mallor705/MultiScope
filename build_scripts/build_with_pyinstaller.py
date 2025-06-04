#!/usr/bin/env python3
import sys
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRY_SCRIPT = PROJECT_ROOT / "linuxcoop.py"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / "linuxcoop.spec"

def check_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller não está instalado. Instalando via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def clean_previous_builds():
    for path in [DIST_DIR, BUILD_DIR, SPEC_FILE]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    print("Builds anteriores limpos.")

def build_pyinstaller(onefile=True, noconsole=False, extra_args=None):
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "linuxcoop",
        "--paths", str(PROJECT_ROOT / "src"),
        str(ENTRY_SCRIPT)
    ]
    if onefile:
        cmd.append("--onefile")
    if noconsole:
        cmd.append("--noconsole")
    if extra_args:
        cmd.extend(extra_args)
    print("Executando:", " ".join(cmd))
    subprocess.check_call(cmd)

def print_usage():
    print(f"""
Script para compilar o Linux-Coop com PyInstaller.

Uso:
    python {__file__} [--onefile/--onedir] [--console/--noconsole] [--clean] [--help] [argumentos PyInstaller]

Opções:
    --onefile       Gera um único executável (padrão).
    --onedir        Gera pasta com arquivos (modo onedir).
    --console       Exibe console ao rodar o executável.
    --noconsole     Não exibe console (padrão para apps GUI).
    --clean         Remove builds anteriores antes de compilar.
    --help          Exibe esta mensagem.

Exemplo:
    python {__file__} --onefile --noconsole --clean

Após a compilação, o executável estará em: {DIST_DIR}/
""")

def main():
    onefile = True
    noconsole = False
    clean = False
    extra_args = []

    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print_usage()
        return

    if "--onedir" in args:
        onefile = False
        args.remove("--onedir")
    if "--onefile" in args:
        onefile = True
        args.remove("--onefile")
    if "--console" in args:
        noconsole = False
        args.remove("--console")
    if "--noconsole" in args:
        noconsole = True
        args.remove("--noconsole")
    if "--clean" in args:
        clean = True
        args.remove("--clean")

    extra_args = args  # Any remaining args are passed to PyInstaller

    if clean:
        clean_previous_builds()

    check_pyinstaller()
    build_pyinstaller(onefile=onefile, noconsole=noconsole, extra_args=extra_args)

    print("\nCompilação finalizada!")
    print(f"Executável gerado em: {DIST_DIR}/")

if __name__ == "__main__":
    main()
