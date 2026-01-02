import os


import subprocess
import shlex
from typing import List, Dict

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

def set_host_env_vars(env_vars: Dict[str, str]) -> None:
    """
    Sets environment variables on the host system when running in a Flatpak.
    """
    if not is_flatpak():
        return

    command_parts = []
    for key, value in env_vars.items():
        command_parts.append(f"export {key}={shlex.quote(value)}")

    command_string = "; ".join(command_parts)

    # We don't need to capture output or check for errors here.
    run_host_command(['sh', '-c', command_string], check=False)
