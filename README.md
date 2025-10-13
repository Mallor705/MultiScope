# Proton-Coop

![Proton-Coop Banner](httpshttps://github.com/Mallor705/Proton-Coop/assets/80993074/399081e7-295e-4c55-b040-02d242407559)

**Proton-Coop** is a powerful tool for Linux that enables local co-op for PC games that don't natively support it. It works by running multiple instances of a game simultaneously, each sandboxed with its own Proton prefix, controller, and display settings. This allows you to play games with separate saves and configurations on the same machine, as if you were on different computers.

## 🚀 Key Features

- **Multi-Instance Gaming:** Launch multiple instances of a game simultaneously.
- **GUI Profile Editor:** An intuitive graphical interface to create, manage, and launch game profiles.
- **Complete Isolation:** Each instance runs in its own sandbox (`bwrap`) with a separate Wine prefix, ensuring no conflicts with saves or configurations.
- **Device Management:** Assign specific keyboards, mice, and controllers to each game instance for a true local co-op feel.
- **Display & Audio Control:** Run each instance on a specific monitor and direct audio to a specific output device.
- **Flexible Launch Options:**
    - Choose any installed Proton version (including GE-Proton and others).
    - Apply DXVK/VKD3D and run custom Winetricks verbs per profile.
    - Set custom environment variables.
- **Splitscreen & Fullscreen Modes:**
    - **Fullscreen:** Each instance runs on a separate monitor.
    - **Splitscreen:** Automatically arrange multiple instances on a single monitor, with horizontal or vertical layouts.
- **CLI and GUI:** Use the powerful command-line interface for scripting and automation, or the user-friendly GUI for easy profile management.

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Steam:** Required for managing and finding Proton versions.
- **Proton:** At least one version of Proton (e.g., Proton Experimental, GE-Proton) must be installed through Steam.
- **Gamescope:** For window management and performance optimization.
- **Bubblewrap (`bwrap`):** For sandboxing and process isolation.
- **Python 3.8+** and `pip`.
- **PyGObject & Adwaita:** For the graphical user interface. On Debian/Ubuntu, you can install these with:
  ```bash
  sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
  ```

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Mallor705/Proton-Coop.git
    cd Proton-Coop
    ```
2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the application:**
    - To start the GUI:
      ```bash
      ./protoncoop.py
      ```
    - To use the CLI:
      ```bash
      ./protoncoop.py <profile_name>
      ```

## 🎮 How to Use

### Using the GUI (Recommended)

The easiest way to get started is with the graphical user interface.

1.  **Launch the GUI:**
    ```bash
    ./protoncoop.py
    ```
2.  **Add a New Profile:** Click the "Add New Profile" button and give your profile a name.
3.  **Configure the Profile:**
    - **General Tab:** Fill in the game name, path to the executable, and Proton version.
    - **Player Config Tab:** Adjust the number of players and assign specific keyboards, mice, and controllers to each player.
    - **Window Layout Tab:** Configure the resolution and choose between fullscreen (one instance per monitor) or splitscreen mode.
4.  **Save and Launch:** Click "Save Profile" and then "Launch Game".

### Using the CLI

For advanced users and automation, the CLI provides full control.

1.  **Create a Profile:** You can create a profile using the GUI first, or manually create a `.json` file in `~/.config/proton-coop/profiles/`.
2.  **Launch a Profile:**
    ```bash
    ./protoncoop.py <profile_name>
    ```
    (Replace `<profile_name>` with the filename of your profile, without the `.json` extension).
3.  **Edit a Profile:**
    ```bash
    ./protoncoop.py edit <profile_name>
    ```
    This will open the profile JSON file in your default text editor.

### Example `profile.json`

Here is an example of what a profile file looks like. You can use this as a template for manual creation.

```json
{
    "GAME_NAME": "Stardew Valley",
    "EXE_PATH": "/home/user/.steam/steam/steamapps/common/Stardew Valley/Stardew Valley.exe",
    "PROTON_VERSION": "GE-Proton8-25",
    "NUM_PLAYERS": 2,
    "INSTANCE_WIDTH": 1920,
    "INSTANCE_HEIGHT": 1080,
    "APP_ID": "413150",
    "GAME_ARGS": "",
    "IS_NATIVE": false,
    "MODE": "splitscreen",
    "SPLITSCREEN": {
        "ORIENTATION": "horizontal"
    },
    "ENV_VARS": {
        "MANGOHUD": "1"
    },
    "PLAYERS": [
        {
            "ACCOUNT_NAME": null,
            "LANGUAGE": null,
            "LISTEN_PORT": null,
            "USER_STEAM_ID": null,
            "PHYSICAL_DEVICE_ID": "/dev/input/by-id/usb-Sony_Interactive_Entertainment_Wireless_Controller-if03-event-joystick",
            "MOUSE_EVENT_PATH": null,
            "KEYBOARD_EVENT_PATH": null,
            "AUDIO_DEVICE_ID": "alsa_output.pci-0000_0b_00.4.analog-stereo",
            "MONITOR_ID": null
        },
        {
            "ACCOUNT_NAME": null,
            "LANGUAGE": null,
            "LISTEN_PORT": null,
            "USER_STEAM_ID": null,
            "PHYSICAL_DEVICE_ID": null,
            "MOUSE_EVENT_PATH": "/dev/input/by-id/usb-Logitech_USB_Receiver-if02-event-mouse",
            "KEYBOARD_EVENT_PATH": "/dev/input/by-id/usb-Logitech_USB_Receiver-event-kbd",
            "AUDIO_DEVICE_ID": null,
            "MONITOR_ID": null
        }
    ],
    "selected_players": [],
    "APPLY_DXVK_VKD3D": true,
    "WINETRICKS_VERBS": null
}
```

## 🛠️ Project Structure

The project is organized into the following directories:

-   `src/`: The main source code for the application.
    -   `cli/`: Command-line interface logic.
    -   `core/`: Core components like configuration, logging, and custom exceptions.
    -   `gui/`: The GTK4/Adwaita graphical user interface.
    -   `models/`: Pydantic data models for profiles and instances.
    -   `services/`: Business logic for managing instances, devices, and dependencies.
-   `docs/`: Documentation files.

## 🤝 Contributing

Contributions are welcome! If you'd like to contribute, please feel free to fork the repository, make your changes, and open a pull request.

## 📄 License

This project is distributed under the MIT License. See the `LICENSE` file for more details.