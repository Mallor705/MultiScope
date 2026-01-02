import logging
import re
import subprocess
from screeninfo import get_monitors
from ..models.profile import Profile
from ..core.utils import is_flatpak, run_host_command
from typing import Dict, List, Tuple, Optional, Union


class DeviceManager:
    """
    Discovers and manages system hardware devices.

    This class provides methods to detect and list available input devices
    (keyboards, mice, joysticks), audio output devices (sinks), and display
    outputs (monitors) by interfacing with system command-line tools like
    `ls`, `pactl`, and `xrandr`.
    """

    def __init__(self):
        """Initializes the DeviceManager."""
        pass

    def _run_command(self, command: str) -> str:
        """
        Executes a shell command and returns its standard output.

        Args:
            command (str): The command to execute.

        Returns:
            str: The stripped stdout from the command, or an empty string
                 if an error occurs.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except FileNotFoundError:
            logging.error(f"Command not found: {command.split()[0]}")
            return ""
        except subprocess.CalledProcessError as e:
            logging.error(f"Command failed: '{command}' with error: {e.stderr.strip()}")
            return ""

    def _get_device_name_from_id(self, device_id_full: str) -> str:
        """
        Generates a human-readable name from a device's ID path.

        It cleans up the raw device ID string by removing path prefixes and
        technical suffixes, making it more suitable for display in a UI.

        Args:
            device_id_full (str): The full device path from `/dev/input/by-id/`.

        Returns:
            str: A cleaned, human-readable device name.
        """
        name_part = device_id_full.replace("/dev/input/by-id/", "")
        name_part = re.sub(r"-event-(kbd|mouse|joystick)", "", name_part)
        name_part = re.sub(r"-if\d+", "", name_part)
        name_part = name_part.replace("usb-", "").replace("_", " ")
        name_part = " ".join(
            [word.capitalize() for word in name_part.split(" ")]
        ).strip()
        return name_part

    def get_input_devices(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Detects and categorizes available input devices.

        Parses the output of `ls -l /dev/input/by-id/` to find keyboards,
        mice, and joysticks.

        Returns:
            Dict[str, List[Dict[str, str]]]: A dictionary where keys are
            "keyboard", "mouse", and "joystick". Each key holds a list of
            device dictionaries, with each dictionary containing the
            device's 'id' (path) and 'name' (human-readable).
        """
        detected_devices: Dict[str, List[Dict[str, str]]] = {
            "keyboard": [],
            "mouse": [],
            "joystick": []
        }
        by_id_output = self._run_command("ls -l /dev/input/by-id/")

        # A more specific regex to find symlinks to event devices.
        device_pattern = re.compile(r"\s([^\s]+)\s+->\s+\.\./event\d+")

        for line in by_id_output.splitlines():
            try:
                match = device_pattern.search(line)
                if match:
                    device_name_id_raw = match.group(1)
                    full_path = f"/dev/input/by-id/{device_name_id_raw}"
                    human_name = self._get_device_name_from_id(full_path)
                    device = {"id": full_path, "name": human_name}

                    if "event-joystick" in device_name_id_raw:
                        detected_devices["joystick"].append(device)
                    elif "event-mouse" in device_name_id_raw:
                        detected_devices["mouse"].append(device)
                    elif "event-kbd" in device_name_id_raw:
                        detected_devices["keyboard"].append(device)
            except (IndexError, AttributeError) as e:
                logging.warning(
                    f"Could not parse input device line: '{line}'. Error: {e}"
                )
                continue

        for dev_type in detected_devices:
            detected_devices[dev_type] = sorted(
                detected_devices[dev_type], key=lambda x: x['name']
            )
        return detected_devices

    def get_audio_devices(self) -> List[Dict[str, str]]:
        """
        Detects available audio output devices (sinks) using `pactl`.
        It uses `flatpak-spawn --host` when running inside a Flatpak.

        Returns:
            List[Dict[str, str]]: A list of dictionaries, where each
            dictionary represents an audio sink and contains its 'id'
            (PulseAudio name) and 'name' (human-readable description).
        """
        audio_sinks = []
        command = "LANG=C pactl list sinks"

        if is_flatpak():
            pactl_output = run_host_command(command.split(), capture_output=True, text=True, check=True).stdout.strip()
        else:
            pactl_output = self._run_command(command)
        desc, name = None, None

        for line in pactl_output.splitlines():
            try:
                if line.startswith("Sink #"):
                    if name:
                        audio_sinks.append({"id": name, "name": desc or name})
                    desc, name = None, None
                elif "Description:" in line:
                    desc = line.split(":", 1)[1].strip()
                elif "Name:" in line:
                    name = line.split(":", 1)[1].strip()
            except (IndexError, AttributeError) as e:
                logging.warning(
                    f"Could not parse audio device line: '{line}'. Error: {e}"
                )
                continue

        if name:
            audio_sinks.append({"id": name, "name": desc or name})

        return sorted(audio_sinks, key=lambda x: x['name'])

    def get_screen_info(self) -> List[Dict[str, Union[int, bool]]]:
        monitors = []
        for i, monitor in enumerate(get_monitors()):
            monitors.append({
                "id": i,
                "x": monitor.x,
                "y": monitor.y,
                "width": monitor.width,
                "height": monitor.height,
            })
        return monitors

    def get_instance_dimensions(self, profile: Profile, instance_num: int) -> Tuple[Optional[int], Optional[int]]:
        """Calculates instance dimensions, accounting for splitscreen.
        For groups of up to 4 instances, the logic is repeated for each group."""

        monitors = self.get_screen_info()

        monitors_sorted = sorted(monitors, key=lambda x: x["id"])

        monitor_to_use = None

        if not profile.is_splitscreen_mode or not profile.splitscreen:
            # Fullscreen mode
            if instance_num < len(monitors_sorted):
                monitor_to_use = monitors_sorted[instance_num]
            else:
                return None, None
        else:
            # Splitscreen mode
            orientation = profile.splitscreen.orientation
            num_players = profile.effective_num_players()

            if num_players < 1:
                if monitors_sorted:
                    monitor_to_use = monitors_sorted[0]
                else:
                    return None, None
            else:
                group_index = instance_num // 4

                if group_index < len(monitors_sorted):
                    monitor_to_use = monitors_sorted[group_index]
                else:
                    return None, None

                # Applies splitscreen logic within the group.
                instance_in_group = instance_num % 4
                num_players_in_group = min(4, num_players - group_index * 4)

                if monitor_to_use:
                    width = monitor_to_use["width"]
                    height = monitor_to_use["height"]

                    if num_players_in_group == 1:
                        return width, height
                    elif num_players_in_group == 2:
                        if orientation == "vertical":
                            return width // 2, height
                        else:
                            return width, height // 2
                    elif num_players_in_group == 3:
                        if orientation == "vertical":
                            if instance_in_group == 0:
                                return width // 2, height
                            else:
                                return width // 2, height // 2
                        else:
                            if instance_in_group == 0:
                                return width, height // 2
                            else:
                                return width // 2, height // 2
                    elif num_players_in_group == 4:
                        return width // 2, height // 2

        if monitor_to_use:
            return monitor_to_use["width"], monitor_to_use["height"]

        return None, None
