[Português](docs/README.pt-br.md) | [Español](docs/README.es.md)

# MultiScope

**MultiScope** is an open-source tool for Linux/SteamOS that allows you to create and manage multiple instances of `gamescope` and `steam` simultaneously. This enables multiple players to enjoy their game library on a single computer, either in split-screen mode or each with their own display, along with dedicated audio output and input devices.

---
<img width="800" height="729" alt="multiscope-ui" src="https://github.com/user-attachments/assets/aea8a9e3-7c11-4978-9141-572d2dce9613" />

## ✨ Key Features

MultiScope is designed as a flexible solution for simultaneous multi-gaming on Linux. Here are some of its main features:

1.  **Simple Multi-Instance Management:** Run multiple Steam instances simultaneously, allowing you and your friends to enjoy your game libraries separately.
2.  **Per-Instance Hardware Assignment:** Assign specific mice, keyboards, and controllers to each game instance. (Mouse/Keyboard can only be assigned to one instance at a time)
3.  **Dedicated Audio Channels:** Route audio from each game instance to a separate audio output device.
4.  **Separate Home Directory:** MultiScope allows you to have a new, separate home for each instance, enabling you to customize settings and files individually. (Does not interfere with your standard Home directory)
5.  **Shared Game Library:** MultiScope allows you to share the Steam game directory among multiple instances, saving disk space and making game updates easier. (Users need to own the game in their Steam libraries to run it)
6.  **Use Any Proton:** MultiScope lets you use any version of Proton to run your games, including custom protons like [ProtonGE](https://github.com/GloriousEggroll/proton-ge-custom).
7.  **Play What You Want:** Instances are not limited to playing the same game; each instance can play whichever game it wants (provided the user owns the game in their Steam library).

## 🎬 Demo

[horizontal-demo.webm](https://github.com/user-attachments/assets/7f74342f-415f-4296-8dbf-1c66e8286092)

## 📦 Installation

The easiest and recommended way to use MultiScope is via the AppImage version. This single file works on most modern Linux distributions without requiring system installation.

1.  **Download the Latest AppImage:**
    Go to the [**Releases**](https://github.com/Mallor705/MultiScope/releases) page and download the latest `.AppImage` file.

2.  **Make it Executable:**
    After downloading, right-click the file, go to "Properties," and check the "Allow executing file as program" box. Alternatively, you can use the terminal:
    ```bash
    chmod +x MultiScope-*.AppImage
    ```

3.  **Run the Application:**
    Run the AppImage and enjoy. That's it!

#### AppImage Integration (Optional)

For better system integration (e.g., adding a menu entry), you can use a tool like **[Gear Lever](https://github.com/mijorus/gearlever)** to manage your AppImage.

## How to Use It?

Access our [Guide](docs/GUIDE.md) for more information on how to use MultiScope.

---

## 🚀 Project Status and Compatibility

You need to have the `steam` and `gamescope` packages native to your distro. MultiScope should work fine on systems that can already run `Gamescope` and `Steam` normally.

For window auto-tiling to work properly, it is recommended to use KDE Plasma 6.0 or higher. In other DEs, you will need to move the windows yourself.

MultiScope is under active development; some bugs may still be encountered.

If you encounter issues, feel free to share your feedback and report bugs in the [Issues](https://github.com/Mallor705/MultiScope/issues) section.

---

## ⚙️ How It Works

MultiScope orchestrates multiple independent Steam instances by leveraging Linux sandboxing and display management technologies. The main goal is to run separate Steam sessions that do not conflict with each other, allowing different users to log in and play simultaneously without interference between the Steam clients.

---

## 🛠️ For Developers

If you wish to contribute to MultiScope or run it directly from the source code, follow the instructions below.

### Running from Source

The `run.sh` script provides a quick way to set up a local environment and run the application. It will automatically create a virtual environment and install the necessary dependencies.

```bash
# Clone the repository
git clone https://github.com/Mallor705/MultiScope.git
cd MultiScope

# Run the launch script
./run.sh
```

### Building from Source

The `build.sh` script compiles the application into a standalone executable using PyInstaller. The final binary will be placed in the `dist/` directory.

```bash
./build.sh
```

### Packaging an AppImage

The `package-appimage.sh` script automates the process of creating an AppImage. It first runs the build script and then uses `linuxdeploy` to package the application into a distributable `.appimage` file.

```bash
./package-appimage.sh
```

## 🤝 How to Contribute

We welcome contributions from everyone! If you are interested in helping improve MultiScope, follow these steps:

1.  **Fork the Repository:** Create your own copy of the project on GitHub.
2.  **Create a Branch:** Create a new branch for your feature or bug fix (`git checkout -b my-amazing-feature`).
3.  **Make Your Changes:** Implement your improvements.
4.  **Submit a Pull Request:** Open a pull request detailing your changes for review.

## 📜 License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**. For more details, see the [LICENSE](../LICENSE) file.

## ⚖️ Legal Disclaimer

MultiScope is an independent open-source project and is not affiliated with, endorsed by, or in any way officially connected to Valve Corporation or Steam.

This tool acts as an orchestration layer that leverages sandboxing technologies (`bubblewrap`) to run multiple isolated instances of the official Steam client. MultiScope **does not modify, patch, reverse engineer, or alter** any Steam files or its normal operation. All Steam instances launched by this tool are the official, unmodified versions provided by Valve.

Users are solely responsible for complying with the terms of the Steam Subscriber Agreement.

## 🙏 Credits

This project was inspired by the work of:

-   [NaviVani-dev](https://github.com/NaviVani-dev) and their script [dualscope.sh](https://gist.github.com/NaviVani-dev/9a8a704a31313fd5ed5fa68babf7bc3a).
-   [Tau5](https://github.com/Tau5) and their project [Co-op-on-Linux](https://github.com/Tau5/Co-op-on-Linux).
-   [wunnr](https://github.com/wunnr) and their project [Partydeck](https://github.com/wunnr/partydeck) (I recommend using it if you're looking for an approach closer to [Nucleus Co-op](https://github.com/SplitScreen-Me/splitscreenme-nucleus)).
