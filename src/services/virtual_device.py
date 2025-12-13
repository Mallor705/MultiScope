import time
from evdev import UInput, ecodes as e, list_devices, InputDevice, AbsInfo
from ..core.exceptions import VirtualDeviceError

class VirtualDeviceService:
    def __init__(self, logger):
        self._logger = logger
        self._ui = None

    def create_virtual_joystick(self):
        """Creates a minimal virtual joystick and finds its event node."""
        if self._ui:
            self._logger.warning("Virtual joystick already exists.")
            # If it exists, we assume the devnode is also known and correct
            return self._ui.devnode

        device_name = "Virtual Joystick by MultiScope"
        try:
            capabilities = {
                e.EV_KEY: [e.BTN_A],
                e.EV_ABS: [
                    (e.ABS_X, AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=0)),
                    (e.ABS_Y, AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=0)),
                ],
            }
            self._ui = UInput(capabilities, name=device_name, vendor=0x1234, product=0x5678)
            self._logger.info("Virtual device object created. Searching for its event node...")

            # Robustly find the device node
            start_time = time.time()
            timeout = 5  # seconds
            while time.time() - start_time < timeout:
                devices = [InputDevice(path) for path in list_devices()]
                for device in devices:
                    if device.name == device_name:
                        self._logger.info(f"Found virtual joystick at {device.path}")
                        # UInput object doesn't always have a correct devnode attribute immediately.
                        # We store the found path for reliability.
                        self._ui.devnode = device.path
                        return device.path
                time.sleep(0.1)

            raise VirtualDeviceError("Virtual joystick created but its event node could not be found.")

        except Exception as ex:
            self._logger.error(f"Failed to create virtual joystick: {ex}")
            if self._ui:
                self._ui.close()
                self._ui = None
            raise VirtualDeviceError(f"Failed to create virtual joystick: {ex}") from ex


    def destroy_virtual_joystick(self):
        """Destroys the virtual joystick if it exists."""
        if self._ui:
            try:
                self._ui.close()
                self._logger.info("Virtual joystick destroyed.")
            except Exception as ex:
                self._logger.error(f"Error destroying virtual joystick: {ex}")
            finally:
                self._ui = None
