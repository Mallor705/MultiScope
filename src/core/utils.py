import os


import subprocess
from typing import List

def is_flatpak() -> bool:
    """Checks if the application is running inside a Flatpak."""
    return os.path.exists("/.flatpak-info")

def run_host_command(command: List[str], **kwargs) -> subprocess.CompletedProcess:
    """
    Executes a command on the host system using 'flatpak-spawn --host'.
    """
    base_command = ["flatpak-spawn", "--host"]
    full_command = base_command + command
    return subprocess.run(full_command, **kwargs)

def run_host_command_async(command: List[str], **kwargs) -> subprocess.Popen:
    """
    Executes a command asynchronously on the host system using 'flatpak-spawn --host'.

    Returns:
        subprocess.Popen: The Popen object for the spawned process.
    """
    base_command = ["flatpak-spawn", "--host"]
    full_command = base_command + command
    return subprocess.Popen(full_command, **kwargs)
