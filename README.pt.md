# Linux-Coop

[Ver em inglês](README.md) | [Ver o principal](README.md)

![Linux-Coop Banner](https://github.com/Mallor705/Linux-Coop/assets/80993074/399081e7-295e-4c55-b040-02d242407559)

Allows playing Windows titles in local cooperative mode on Linux, running multiple instances of the same game via Proton and Gamescope, with independent profiles and controller support.

## Key Features

- **Advanced Local Co-op:** Run up to two instances of the same game simultaneously for a seamless local cooperative experience.
- **Isolated Game Profiles:** Maintain independent saves and configurations for each game through customizable profiles.
- **Execution Flexibility:** Supports selecting any `.exe` executable and various Proton versions, including GE-Proton.
- **Customizable Resolution:** Adjust the resolution for each game instance individually.
- **Simplified Debugging:** Automatic log generation to facilitate problem identification and correction.
- **Controller Mapping:** Configure specific physical controllers for each player.
- **Broad Compatibility:** Supports multiple games through the profile system.

## Project Status

- **Core Functionality:** Games open in separate instances with independent saves.
- **Performance:** Optimized performance for a fluid gaming experience.
- **Proton Management:** Fully selectable Proton version, including GE-Proton support.
- **Organization:** Dedicated profiles for each game.

### Known Issues

- **Controller Recognition:** In some cases, controllers may not be recognized (priority for correction).
- **Window Arrangement:** Instances may open on the same monitor, requiring manual movement.

## System Prerequisites

To ensure the correct functioning of Linux-Coop, the following prerequisites are essential:

- **Steam:** Must be installed and configured on your system.
- **Proton:** Install Proton (or GE-Proton) via Steam.
- **Gamescope:** Install Gamescope by following the [official instructions](https://github.com/ValveSoftware/gamescope).
- **Bubblewrap (`bwrap`):** Essential tool for process isolation.
- **Device Permissions:** Ensure access permissions to control devices in `/dev/input/by-id/`.
- **Linux Utilities:** Bash and basic Linux system utilities.
- **Python 3.8+:** The project requires Python version 3.8 or higher.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Mallor705/Linux-Coop.git
    cd Linux-Coop
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

    Alternatively, if you are developing or prefer an editable installation:

    ```bash
    pip install -e .
    ```

## How to Use

### 1. Create a Game Profile

Create a JSON file in the `profiles/` folder with a descriptive name (e.g., `MyGame.json`).

**Example Content for Horizontal Splitscreen:**

```json
{
  "game_name": "GAME",
  "exe_path": ".steam/Steam/steamapps/common/GAME/game.exe",
  "players": [
    {
      "account_name": "Player1",
      "language": "brazilian",
      "listen_port": "",
      "user_steam_id": "76561190000000001"
    },
    {
      "account_name": "Player2",
      "language": "brazilian",
      "listen_port": "",
      "user_steam_id": "76561190000000002"
    }
  ],
  "proton_version": "GE-Proton10-4",
  "instance_width": 1920,
  "instance_height": 1080,
  "player_physical_device_ids": [
    "",
    ""
  ],
  "player_mouse_event_paths": [
    "",
    ""
  ],
  "player_keyboard_event_paths": [
    "",
    ""
  ],
  "app_id": "12345678",
  "game_args": "",
  "use_goldberg_emu": false,
  "env_vars": {
    "WINEDLLOVERRIDES": "",
    "MANGOHUD": "1"
  },
  "is_native": false,
  "mode": "splitscreen",
  "splitscreen": {
    "orientation": "horizontal",
    "instances": 2
  }
}
```

**Example Content for Vertical Splitscreen:**

```json
{
  "game_name": "GAME",
  "exe_path": ".steam/Steam/steamapps/common/GAME/game.exe",
  "players": [
    {
      "account_name": "Player1",
      "language": "brazilian",
      "listen_port": "",
      "user_steam_id": "76561190000000001"
    },
    {
      "account_name": "Player2",
      "language": "brazilian",
      "listen_port": "",
      "user_steam_id": "76561190000000002"
    }
  ],
  "proton_version": "GE-Proton10-4",
  "instance_width": 1920,
  "instance_height": 1080,
  "player_physical_device_ids": [
    "/dev/input/by-id/...",
    "/dev/input/by-id/..."
  ],
  "player_mouse_event_paths": [
    "/dev/input/by-id/...",
    "/dev/input/by-id/..."
  ],
  "player_keyboard_event_paths": [
    "/dev/input/by-id/...",
    "/dev/input/by-id/..."
  ],

  "player_audio_device_ids": [
    "",
    ""
  ],
  
  
  "app_id": "12345678",
  "game_args": "",
  "use_goldberg_emu": false,
  "env_vars": {
    "WINEDLLOVERRIDES": "",
    "MANGOHUD": "1"
  },
  "is_native": false,
  "mode": "splitscreen",
  "splitscreen": {
    "orientation": "vertical",
    "instances": 2
  }
}
```

### 2. Run the Main Script

From the project root, execute the command, replacing `<profile_name>` with the name of your profile JSON file (without the `.json` extension):

```bash
python ./linuxcoop.py <profile_name>
# Or, if installed via setuptools:
linux-coop <profile_name>
```

Upon execution, the script will:

- Validate all necessary dependencies.
- Load the specified game profile.
- Create separate Proton prefixes for each game instance.
- Launch both game windows via Gamescope.
- Generate detailed logs in `~/.local/share/linux-coop/logs/` for debugging.

### 3. Controller Mapping

- Controllers are configured in the profile file or in specific files within `controller_config/`.
- To avoid conflicts, controller blacklists (e.g., `Player1_Controller_Blacklist`) are automatically generated.
- **Important:** Connect all your physical controllers before starting the script.

## Testing the Installation

To verify that the prerequisites are correctly installed, run the following commands:

```bash
gamescope --version
bwrap --version
```

## Tips and Troubleshooting

-   **Controllers not recognized:** Check permissions in `/dev/input/by-id/` and confirm that device IDs are correct in your profile file.
-   **Proton not found:** Ensure that the Proton version name in your profile exactly matches the installation name in Steam.
-   **Instances on the same monitor:** Game instances may open on the same monitor. To move and organize them, you can use the following keyboard shortcuts. **Note that shortcuts may vary depending on your Linux desktop environment and personalized settings:**
      *   `Super + W` (or `Ctrl + F9` / `Ctrl + F10`): Displays an overview of all workspaces and open windows (Activities/Overview), similar to hovering the mouse in the top-left corner.
      *   `Super + Arrows (↑ ↓ ← →)`: Moves and snaps the active window to one side of the screen.
      *   `Super + PgDn`: Minimizes the active window.
      *   `Super + PgUp`: Maximizes the active window.
      *   `Alt + Tab`: Switches between open windows of different applications.
      *   `Super + D`: Minimizes all windows and shows the desktop.
-   **Debugging logs:** Consult the `~/.local/share/linux-coop/logs/` directory for detailed information about errors and script behavior.

## Important Notes

-   Tested and optimized with Palworld, but may be compatible with other games (might require adjustments in the profile file).
-   Currently, the script only supports a two-player setup.
-   For games that do not natively support multiple instances, additional solutions such as sandboxes or separate Steam accounts might be necessary.

## Contribution

Contributions are welcome! Feel free to open issues or pull requests.

## License

This project is distributed under the MIT license. Consult the `LICENSE` file in the repository for more details. 