[Português](./GUIDE.pt-br.md) | [Español](./GUIDE.es.md)

# MultiScope Guide

Welcome to the MultiScope guide! This document will walk you through the process of setting up and using the MultiScope application to run multiple Steam instances.

> [!NOTE]
> To use MultiScope, it's necessary to add your user to the `input` group to allow the program to manage input devices.
> ```bash
> sudo usermod -aG input $USER
> ```
> in the Bazzite:
> ```bash
> ujust add-user-to-input-group
> ```
> **Restart the system for the changes to take effect.**

## 1. Number of Instances

First, you need to decide how many Steam instances you want to run. MultiScope supports up to 8 instances total.

- **Splitscreen:** You can run a maximum of 4 instances per monitor.
- **Fullscreen:** You can run a maximum of 1 instance per monitor.

Use the numeric selector "Number of Instances" to set the desired amount.

<img width="708" height="127" alt="general_layout" src="https://github.com/user-attachments/assets/3a764b39-fccf-451d-b2c4-56661a9a344e" />


## 2. Screen Mode

You can choose between two screen modes:

- **Fullscreen:** Each instance will run on a separate monitor.
- **Splitscreen:** Instances will be arranged on a single monitor, either horizontally or vertically.

<img width="708" height="204" alt="screen_settings" src="https://github.com/user-attachments/assets/d8b87c4c-3112-46a7-a85c-5ec35d7d043d" />

### Splitscreen Options

When selecting "Splitscreen," you can choose between two orientations:

- **Horizontal:** Instances are arranged side by side.
- **Vertical:** Instances are arranged stacked on top of each other.

Positions and layouts adjust automatically based on the number of instances.

Note: Instance auto-tiling only works with `KDE Plasma` environments.

<img width="1280" height="720" alt="horizontal-game" src="https://github.com/user-attachments/assets/15ba21f3-c1cc-4f3c-8b9c-7e54bebdb90a" />
<img width="1280" height="720" alt="vertical-game" src="https://github.com/user-attachments/assets/28a4b3f2-8588-4e89-be28-6728decb7a25" />

## 3. Instance Configuration

For each instance, you can configure the following options:

- **Gamepad:** Assign a specific controller to the instance.
- **Capture Mouse:** Dedicate the mouse to a single instance. For now, only one instance at a time can use the mouse and keyboard.
- **Audio Device:** Select a specific audio output device for the instance.
- **Refresh Rate:** Set the refresh rate for the instance. Useful if you want to cap FPS or use a specific refresh rate.
- **Environment Variables:** Define specific environment variables for the instance.

<img width="595" height="409" alt="player_config" src="https://github.com/user-attachments/assets/f6e38bea-1685-4d63-835a-464305b71cee" />

## 4. Starting an Instance

After configuring an instance, click the **"Start"** button next to it to launch an isolated Steam instance without gamescope. The first time, Steam will be installed automatically — this process may take a few minutes.

Each instance can be started individually via its **"Start"** button. To run multiple instances at once, use the **"Play"** button located at the bottom of the window.

Only instances that already have Steam installed can be launched with the **"Play"** button. You can verify this by the checkmark icon on the instance. If the icon is not present, install Steam by clicking that instance's **"Start"** button. This allows for quick and direct configuration, game, or application setup for a specific instance.

<img width="651" height="178" alt="instance_config" src="https://github.com/user-attachments/assets/9cff5635-1f4b-4571-bd5a-8816d9a59376" />

## 5. Steam Big Picture Mode (Optional)

For the best experience, it is recommended to enable "Big Picture Mode" in Steam's settings. This provides a controller-friendly interface, ideal for MultiScope.

To do this, go to `Settings > Interface` and check the box for `Start Steam in Big Picture Mode`.

Repeat this process for all instances you wish to start in Big Picture Mode.

<img width="850" height="722" alt="bigpicture" src="https://github.com/user-attachments/assets/f9f3f4be-4322-4dfb-97f3-72aabe10bc9d" />

## 6. Play

When all your instances are configured and running, you can start playing! Each instance will have its own dedicated input and audio devices, allowing you to play with your friends or family on the same computer.

Enjoy your gaming session!

### Keyboard shortcuts:

  Super + F                      toggle fullscreen
  Super + N                      toggle nearest neighbour filtering
  Super + U                      toggle FSR upscaling
  Super + Y                      toggle NIS upscaling
  Super + I                      increase FSR sharpness by 1
  Super + O                      decrease FSR sharpness by 1
  Super + S                      take a screenshot
  Super + G                      toggle keyboard grab

# Optional

## Applications

To add applications to your instance, go to `Add a Game` and click `Add a Non-Steam Game...`. Select the application you wish to add.

<img width="364" height="142" alt="add-game" src="https://github.com/user-attachments/assets/7de6ce46-5ba4-4060-9d18-d718bc390053" />

### Why do this?

This allows you to run applications directly from the instance, enabling a unique configuration per instance for that application. This is because each instance has its own unique `HOME` directory. They can be found at `~/.local/share/multiscope/home_{n}`.

A good example is [mangojuice](https://github.com/radiolamp/mangojuice); if you want to use it with custom settings, you will need to run and configure it for each instance individually.

## Multi GPU Support

> [!NOTE]
> This should be added directly to the game's arguments, do not add it to the environment variables.

MultiScope supports running multiple games on different GPUs.

Add the following line to your game's Steam arguments:

```bash
DRI_PRIME=1!

```

This makes GPU 1 be used in the game. You can adjust the numbers according to your system configuration.
