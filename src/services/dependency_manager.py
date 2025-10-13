import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from ..core.logger import Logger


class DependencyManager:
    """
    Manages Wine prefix dependencies like DXVK, VKD3D, and Winetricks.

    This class handles the initialization of Wine prefixes and the installation
    of necessary components into them. It intelligently detects the directory
    structure of the provided Proton version (GE-Proton vs. Valve) to find
    the correct library and binary paths.
    """

    def __init__(self, logger: Logger, proton_path: Path, steam_root: Path):
        """
        Initializes the DependencyManager.

        It inspects the Proton directory to determine if it follows the
        GE-Proton ('files' directory) or standard Valve ('dist' directory)
        layout, setting internal paths accordingly.

        Args:
            logger (Logger): The logger instance for output.
            proton_path (Path): The path to the selected Proton executable file.
            steam_root (Path): The root path of the Steam installation.
        """
        self.logger = logger
        self.steam_root = steam_root
        self.proton_root_dir = proton_path.parent

        # Detect Proton structure (GE-Proton vs. Valve)
        if (self.proton_root_dir / 'files').exists():
            self.logger.info("Detected GE-Proton-like structure.")
            self.proton_bin_path = self.proton_root_dir / 'files' / 'bin'
            self.lib_path_x64 = self.proton_root_dir / 'files' / 'lib' / 'wine'
            self.lib_path_x86 = self.proton_root_dir / 'files' / 'lib' / 'wine'
            self.arch_folder_x64 = 'x86_64-windows'
            self.arch_folder_x86 = 'i386-windows'
        else:
            self.logger.info("Detected Valve Proton-like structure.")
            self.proton_bin_path = self.proton_root_dir / 'dist' / 'bin'
            self.lib_path_x64 = self.proton_root_dir / 'dist' / 'lib64' / 'wine'
            self.lib_path_x86 = self.proton_root_dir / 'dist' / 'lib' / 'wine'
            self.arch_folder_x64 = ''
            self.arch_folder_x86 = ''

    def _get_custom_env(self, prefix_path: Path) -> Dict[str, str]:
        """
        Prepares a custom environment for running Wine/Proton commands.

        This sets up essential environment variables like `WINEPREFIX`, `PATH`,
        and `WINE` to ensure that commands are executed within the correct
        context of the specified prefix and Proton version.

        Args:
            prefix_path (Path): The path to the game's instance prefix directory.

        Returns:
            Dict[str, str]: A dictionary of environment variables.
        """
        env = os.environ.copy()
        env["PATH"] = f"{self.proton_bin_path}:{env.get('PATH', '')}"
        env["WINEPREFIX"] = str(prefix_path / "pfx")
        env["WINE"] = str(self.proton_bin_path / "wine")
        env["WINESERVER"] = str(self.proton_bin_path / "wineserver")
        env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(self.steam_root)
        env["DXVK_ASYNC"] = "1"
        env["DXVK_LOG_LEVEL"] = "info"
        return env

    def initialize_prefix(self, prefix_path: Path):
        """
        Initializes a new Wine prefix by running `wineboot`.

        This creates the basic directory structure and files required for a
        functional Wine prefix.

        Args:
            prefix_path (Path): The path to the game's instance prefix directory.
        """
        self.logger.info(f"Initializing Wine prefix at {prefix_path / 'pfx'}...")
        custom_env = self._get_custom_env(prefix_path)
        try:
            proc = subprocess.run(
                ["wineboot", "--init"],
                env=custom_env,
                check=True,
                capture_output=True,
                text=True,
                errors='replace',
                timeout=120
            )
            self.logger.info("Wine prefix initialized successfully.")
            self.logger.info(f"wineboot stdout: {proc.stdout}")
        except subprocess.TimeoutExpired:
            self.logger.error("wineboot command timed out during prefix initialization.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to initialize Wine prefix. Stderr: {e.stderr}")

    def _get_dll_paths(self, lib_name: str) -> Optional[Dict[str, Path]]:
        """
        Constructs the paths to 32-bit and 64-bit DLLs for a given library.

        Args:
            lib_name (str): The name of the library (e.g., "dxvk").

        Returns:
            Optional[Dict[str, Path]]: A dictionary with "x64" and "x86" paths,
            or None if the paths could not be found.
        """
        self.logger.info(f"Finding paths for '{lib_name}' library...")

        x64_path = self.lib_path_x64 / lib_name / self.arch_folder_x64
        x86_path = self.lib_path_x86 / lib_name / self.arch_folder_x86

        if x64_path.exists() and x86_path.exists():
            self.logger.info(f"Found '{lib_name}' paths: {x64_path} | {x86_path}")
            return {"x64": x64_path, "x86": x86_path}

        self.logger.error(f"Could not find paths for '{lib_name}'.")
        return None

    def apply_dxvk_vkd3d(self, prefix_path: Path):
        """
        Applies DXVK and VKD3D-Proton to a Wine prefix.

        This involves copying the necessary DLL files into the prefix's
        `system32` and `syswow64` directories and setting the required
        Windows registry overrides.

        Args:
            prefix_path (Path): The path to the game's instance prefix directory.
        """
        self.logger.info(f"Applying DXVK/VKD3D to prefix: {prefix_path}")

        system32_path = prefix_path / "pfx" / "drive_c" / "windows" / "system32"
        syswow64_path = prefix_path / "pfx" / "drive_c" / "windows" / "syswow64"

        dll_sources = {
            "dxvk": self._get_dll_paths("dxvk"),
            "vkd3d-proton": self._get_dll_paths("vkd3d-proton"),
        }

        for lib_name, paths in dll_sources.items():
            if not paths:
                self.logger.warning(f"Skipping '{lib_name}', paths not found.")
                continue

            for arch, src_path in paths.items():
                dest_path = syswow64_path if arch == "x86" else system32_path
                if not src_path.exists():
                    self.logger.warning(f"Source path not found for {lib_name} ({arch}): {src_path}")
                    continue

                self.logger.info(f"Copying DLLs for {lib_name} ({arch}) to {dest_path}")
                for dll in src_path.glob("*.dll"):
                    shutil.copy(dll, dest_path)

        custom_env = self._get_custom_env(prefix_path)
        reg_commands = {
            'HKEY_CURRENT_USER\\Software\\Wine\\DllOverrides': [
                ('d3d10', 'native,builtin'), ('d3d10_1', 'native,builtin'),
                ('d3d10core', 'native,builtin'), ('d3d11', 'native,builtin'),
                ('d3d9', 'native,builtin'), ('dxgi', 'native,builtin'),
                ('d3d12', 'native,builtin'), ('d3d12core', 'native,builtin'),
            ]
        }
        for key, values in reg_commands.items():
            for value_name, value_data in values:
                try:
                    subprocess.run(
                        ["wine", "reg", "add", key, "/v", value_name, "/d", value_data, "/f"],
                        env=custom_env, check=True, capture_output=True, text=True, errors='replace'
                    )
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Failed to set registry key: {key}\\{value_name}. Stderr: {e.stderr}")

    def apply_winetricks(self, prefix_path: Path, verbs: List[str]):
        """
        Applies a list of Winetricks verbs to the specified Wine prefix.

        Args:
            prefix_path (Path): The path to the game's instance prefix directory.
            verbs (List[str]): A list of Winetricks verbs to execute.
        """
        if not verbs:
            return

        self.logger.info(f"Applying Winetricks verbs: {verbs}")
        winetricks_path = shutil.which("winetricks")
        if not winetricks_path:
            self.logger.error("Winetricks is not installed or not in PATH.")
            return

        custom_env = self._get_custom_env(prefix_path)
        try:
            subprocess.run(
                [winetricks_path, *verbs],
                env=custom_env, check=True, capture_output=True, text=True, errors='replace'
            )
            self.logger.info(f"Successfully applied Winetricks verbs: {verbs}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to apply Winetricks verbs: {verbs}. Stderr: {e.stderr}")