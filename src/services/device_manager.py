import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple


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
        self.pnp_ids = self._load_pnp_ids()

    def _load_pnp_ids(self) -> Dict[str, str]:
        """
        Loads and parses the pnp.ids file to map vendor IDs to manufacturer names.
        """
        pnp_map = {}
        # Common locations for the pnp.ids file
        pnp_paths = ["/usr/share/hwdata/pnp.ids", "/usr/share/misc/pnp.ids"]
        pnp_file = None

        for path in pnp_paths:
            if os.path.exists(path):
                pnp_file = path
                break

        if not pnp_file:
            return pnp_map

        try:
            with open(pnp_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.startswith("#") or not line.strip():
                        continue

                    # Vendor entries are not indented
                    if not line.startswith("\t"):
                        parts = line.strip().split("\t", 1)
                        if len(parts) == 2:
                            vendor_id = parts[0]
                            vendor_name = parts[1].strip()
                            if len(vendor_id) == 3:
                                pnp_map[vendor_id] = vendor_name
        except IOError:
            pass # File not found or not readable

        return pnp_map

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

    def _parse_edid(self, edid_raw: bytes) -> Tuple[Optional[str], Optional[str]]:
        """
        Parses raw EDID data to find the manufacturer ID and monitor model name.
        """
        manufacturer_id = None
        model_name = None

        # The manufacturer ID is stored in bytes 8-9.
        try:
            # The ID is a 3-letter code, packed into 15 bits.
            m_id_bytes = edid_raw[8:10]
            # Each letter is a 5-bit uppercase char offset from 'A'.
            pnp_id = (
                chr(((m_id_bytes[0] & 0b01111100) >> 2) + 64) +
                chr(((m_id_bytes[0] & 0b00000011) << 3) + ((m_id_bytes[1] & 0b11100000) >> 5) + 64) +
                chr((m_id_bytes[1] & 0b00011111) + 64)
            )
            manufacturer_id = pnp_id
        except IndexError:
            pass

        # The model name is in a descriptor block.
        for i in range(54, 126, 18):
            block = edid_raw[i : i + 18]
            if block.startswith(b'\x00\x00\x00\xfc\x00'):
                try:
                    name = block[5:18].split(b'\n')[0].decode('ascii').strip()
                    if name:
                        model_name = name
                        break # Found the name, no need to check other blocks
                except (UnicodeDecodeError, IndexError):
                    continue

        return manufacturer_id, model_name

    def get_display_outputs(self) -> List[Dict[str, str]]:
        """
        Detects connected display outputs and their model names.
        It uses `xrandr` to get the list of connected ports in the correct
        order, then reads EDID information from `/sys/class/drm/` to find
        the real monitor model name.
        """
        # Step 1: Get the list and order of connected displays from xrandr.
        xrandr_output = self._run_command("xrandr --query")
        connected_displays = []
        for line in xrandr_output.splitlines():
            if " connected" in line and not line.startswith(" "):
                display_id = line.split()[0]
                if not display_id.lower().startswith("virtual"):
                    connected_displays.append(display_id)

        # Step 2: Find model names by reading EDID from sysfs.
        display_outputs = []
        drm_path = "/sys/class/drm/"
        try:
            # Match xrandr outputs (e.g., "DP-1") with DRM connectors.
            drm_connectors = [d for d in os.listdir(drm_path) if "card" in d]

            for display_id in connected_displays:
                model_name = None
                for connector in drm_connectors:
                    if display_id in connector:
                        try:
                            # Check if the connector is enabled and has EDID info.
                            status_path = os.path.join(drm_path, connector, "status")
                            edid_path = os.path.join(drm_path, connector, "edid")

                            with open(status_path, 'r') as f:
                                if f.read().strip() != "connected":
                                    continue

                            if os.path.exists(edid_path):
                                with open(edid_path, 'rb') as f:
                                    edid_raw = f.read()
                                    manufacturer_id, model_name = self._parse_edid(edid_raw)
                                    if model_name or manufacturer_id:
                                        break # Found name, stop searching connectors
                        except (IOError, OSError):
                            continue # Ignore errors reading from a specific connector

                # Step 3: Build the final name.
                brand_name = self.pnp_ids.get(manufacturer_id)

                parts = []
                if brand_name:
                    parts.append(brand_name)
                if model_name:
                    parts.append(model_name)

                if parts:
                    name = f"{' '.join(parts)} ({display_id})"
                else:
                    name = display_id # Fallback

                display_outputs.append({"id": display_id, "name": name})

        except (IOError, OSError):
            # Fallback if /sys/class/drm is not accessible.
            # Return the simple list from xrandr.
            return [{"id": did, "name": did} for did in connected_displays]

        return display_outputs