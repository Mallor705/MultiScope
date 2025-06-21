import subprocess
import re
from pathlib import Path
from typing import List, Dict, Tuple

class DeviceManager:
    def __init__(self):
        pass

    def _run_command(self, command: str) -> str:
        """Helper to run shell commands and return stdout."""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            # print(f"Error executing command '{command}': {e}")
            # print(f"Stderr: {e.stderr}")
            return "" # Return empty string on error, the calling method should handle it

    def _get_device_name_from_id(self, device_id_full: str) -> str:
        """Extracts a human-readable name from the /dev/input/by-id device string."""
        # Remove the /dev/input/by-id/ prefix
        name_part = device_id_full.replace("/dev/input/by-id/", "")
        
        # Remove common suffixes and prefixes that are not user-friendly
        name_part = re.sub(r"-event-(kbd|mouse|joystick)", "", name_part)
        name_part = re.sub(r"-if\d+", "", name_part) # Remove -ifXX
        name_part = name_part.replace("usb-", "").replace("_", " ") # Replace underscores and usb prefix
        
        # Capitalize first letter of each word
        name_part = " ".join([word.capitalize() for word in name_part.split(" ")]).strip()
        
        return name_part

    def get_input_devices(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Detects and returns input devices categorized by type.
        Returns a dictionary with keys:
        - 'keyboard': List of dicts {id: ..., name: ...}
        - 'mouse': List of dicts {id: ..., name: ...}
        - 'joystick': List of dicts {id: ..., name: ...}
        """
        detected_devices: Dict[str, List[Dict[str, str]]] = {
            "keyboard": [],
            "mouse": [],
            "joystick": []
        }

        by_id_output = self._run_command("ls -l /dev/input/by-id/")
        
        for line in by_id_output.splitlines():
            match = re.match(r".*?\s+([^\s]+)\s+->\s+\.\.(/event\d+|/mouse\d+|/js\d+)", line)
            if match:
                device_name_id_raw = match.group(1) # e.g., usb-Rapoo_Rapoo_Gaming_Device-if01-event-kbd
                full_device_id_path = f"/dev/input/by-id/{device_name_id_raw}"
                device_human_name = self._get_device_name_from_id(full_device_id_path)

                if "event-kbd" in device_name_id_raw:
                    detected_devices["keyboard"].append({"id": full_device_id_path, "name": device_human_name})
                elif "event-mouse" in device_name_id_raw:
                    detected_devices["mouse"].append({"id": full_device_id_path, "name": device_human_name})
                elif "event-joystick" in device_name_id_raw:
                    detected_devices["joystick"].append({"id": full_device_id_path, "name": device_human_name})
                # Also add /dev/input/jsX paths to joystick if they exist and are relevant
                elif "joystick" in device_name_id_raw and match.group(2).startswith("/js"):
                    # For joysticks, we might still want to list the /dev/input/jsX path for direct use
                    # if the profile or other parts of the code specifically look for it.
                    # However, the user asked to store /dev/input/by-id/ format in profile.
                    # I will add both if it's a joystick, for broader compatibility.
                    # The 'id' will be the /dev/input/by-id path, and a 'secondary_id' for /dev/input/jsX
                    pass # We only care about the by-id path for storage as per request.
        
        # Sort devices by name for consistent UI display
        for dev_type in detected_devices:
            detected_devices[dev_type] = sorted(detected_devices[dev_type], key=lambda x: x['name'])

        return detected_devices

    def get_audio_devices(self) -> List[Dict[str, str]]:
        """
        Detects and returns available audio output devices (sinks).
        Returns a list of dicts with keys:
        - 'id': The pulse audio sink ID.
        - 'name': A human-readable name for the sink.
        """
        audio_sinks = []
        pactl_output = self._run_command("pactl list sinks").strip() # Use 'list sinks' for more details

        # Regex to capture Sink #ID and Description
        sink_id_pattern = re.compile(r"Sink #(\d+)")
        description_pattern = re.compile(r"\s+Description: (.+)")
        name_pattern = re.compile(r"\s+Name: (.+)")

        current_sink_id = None
        current_description = None
        current_name = None

        for line in pactl_output.splitlines():
            sink_id_match = sink_id_pattern.match(line)
            if sink_id_match:
                # New sink starts, save previous if complete
                if current_sink_id and current_name:
                    audio_sinks.append({"id": current_name, "name": current_description if current_description else current_name})
                current_sink_id = sink_id_match.group(1)
                current_description = None
                current_name = None
                continue

            description_match = description_pattern.match(line)
            if description_match:
                current_description = description_match.group(1)
                continue
            
            name_match = name_pattern.match(line)
            if name_match:
                current_name = name_match.group(1)
                continue
        
        # Add the last sink if it's complete
        if current_sink_id and current_name:
            audio_sinks.append({"id": current_name, "name": current_description if current_description else current_name})

        return sorted(audio_sinks, key=lambda x: x['name']) 