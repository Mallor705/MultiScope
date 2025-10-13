import re
import subprocess
from typing import Dict, List


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
        except subprocess.CalledProcessError:
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

        for line in by_id_output.splitlines():
            match = re.match(r".*?\s+([^\s]+)\s+->\s+\.\.(/event\d+)", line)
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

        for dev_type in detected_devices:
            detected_devices[dev_type] = sorted(
                detected_devices[dev_type], key=lambda x: x['name']
            )
        return detected_devices

    def get_audio_devices(self) -> List[Dict[str, str]]:
        """
        Detects available audio output devices (sinks) using `pactl`.

        Returns:
            List[Dict[str, str]]: A list of dictionaries, where each
            dictionary represents an audio sink and contains its 'id'
            (PulseAudio name) and 'name' (human-readable description).
        """
        audio_sinks = []
        pactl_output = self._run_command("pactl list sinks")
        sink_id, desc, name = None, None, None

        for line in pactl_output.splitlines():
            if line.startswith("Sink #"):
                if name:
                    audio_sinks.append({"id": name, "name": desc or name})
                sink_id, desc, name = line.split('#')[1], None, None
            elif "Description:" in line:
                desc = line.split(":", 1)[1].strip()
            elif "Name:" in line:
                name = line.split(":", 1)[1].strip()

        if name:
            audio_sinks.append({"id": name, "name": desc or name})

        return sorted(audio_sinks, key=lambda x: x['name'])

    def get_display_outputs(self) -> List[Dict[str, str]]:
        """
        Detects connected display outputs (monitors) using `xrandr`.

        Returns:
            List[Dict[str, str]]: A list of dictionaries, where each
            dictionary represents a connected monitor and contains its
            'id' and 'name' (e.g., "DP-1").
        """
        display_outputs = []
        xrandr_output = self._run_command("xrandr --query")
        connected_pattern = re.compile(r"^(\S+) connected.*")

        for line in xrandr_output.splitlines():
            match = connected_pattern.match(line)
            if match:
                display_name = match.group(1)
                if not display_name.lower().startswith("virtual"):
                    display_outputs.append({"id": display_name, "name": display_name})

        return sorted(display_outputs, key=lambda x: x['name']) 