<p align="right">
  <a href="https://github.com/mall0r/Twinverse/blob/master/docs/GUIDE.md"><img src="https://img.shields.io/badge/EN-🇬🇧-darkblue.svg" alt="English"/></a>
  <a href="https://github.com/mall0r/Twinverse/blob/master/docs/GUIDE.pt-br.md"><img src="https://img.shields.io/badge/PT-🇧🇷-darkgreen.svg" alt="Portuguese"/></a>
  <a href="https://github.com/mall0r/Twinverse/blob/master/docs/GUIDE.es.md"><img src="https://img.shields.io/badge/ES-🇪🇸-darkred.svg" alt="Spanish"/></a>
</p>

# Twinverse Guide

Welcome to the Twinverse guide! This document will walk you through the process of setting up and using the Twinverse application to run multiple Steam instances.

> [!IMPORTANT]
> To use Twinverse, it's necessary to add your user to the `input` group to allow the program to manage input devices.
> ```bash
> sudo usermod -aG input $USER
> ```
> in the Bazzite:
> ```bash
> ujust add-user-to-input-group
> ```
> **Restart the system for the changes to take effect.**

## 1. Number of Instances

First, you need to decide how many Steam instances you want to run. Twinverse supports up to 8 instances total.

- **Splitscreen:** You can run a maximum of 4 instances per monitor.
- **Fullscreen:** You can run a maximum of 1 instance per monitor.

Use the numeric selector "Number of Instances" to set the desired amount.

<img width="708" height="127" alt="general-layout" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/general-layout.png" />

## 2. Screen Mode

> [!NOTE]
> For window auto-tiling to work properly, it is recommended to use KDE Plasma 6.0+.
> In other DEs, you will need to move the windows yourself, everything else should work fine.

You can choose between two screen modes:

- **Fullscreen:** Each instance will run on a separate monitor.
- **Splitscreen:** Instances will be arranged on a single monitor, either horizontally or vertically.

<img width="708" height="204" alt="screen-settings" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/screen-settings.png" />

### Splitscreen Options

When selecting "Splitscreen," you can choose between two orientations:

- **Horizontal:** Instances are arranged side by side.
- **Vertical:** Instances are arranged stacked on top of each other.

Positions and layouts adjust automatically based on the number of instances.

Note: Instance auto-tiling only works with `KDE Plasma` environments.

<img width="1280" height="720" alt="horizontal-game" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/horizontal-game.png" />
<img width="1280" height="720" alt="vertical-game" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/vertical-game.png" />

## 3. Instance Configuration

For each instance, you can configure the following options:

- **Gamepad:** Assign a specific controller to the instance.
- **Capture Mouse:** Dedicate the mouse to a single instance. For now, only one instance at a time can use the mouse and keyboard.
- **Audio Device:** Select a specific audio output device for the instance.
- **Refresh Rate:** Set the refresh rate for the instance. Useful if you want to cap FPS or use a specific refresh rate.
- **Environment Variables:** Define specific environment variables for the instance.

<img width="595" height="409" alt="player-config" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/player-config.png" />

## 4. Starting an Instance

After configuring an instance, click the **"Start"** button next to it to launch an isolated Steam instance without gamescope. The first time, Steam will be installed automatically — this process may take a few minutes.

Each instance can be started individually via its **"Start"** button. To run multiple instances at once, use the **"Play"** button located at the bottom of the window.

Only instances that already have Steam installed can be launched with the **"Play"** button. You can verify this by the checkmark icon on the instance. If the icon is not present, install Steam by clicking that instance's **"Start"** button. This allows for quick and direct configuration, game, or application setup for a specific instance.

<img width="651" height="178" alt="instance-config" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/instance-config.png" />

## 5. Steam Big Picture Mode (Optional)

For the best experience, it is recommended to enable "Big Picture Mode" in Steam's settings. This provides a controller-friendly interface, ideal for Twinverse.

To do this, go to `Settings > Interface` and check the box for `Start Steam in Big Picture Mode`.

Repeat this process for all instances you wish to start in Big Picture Mode.

<img width="850" height="722" alt="enable-bigpicture" src="https://raw.githubusercontent.com/mall0r/Twinverse/master/share/screenshots/enable-bigpicture.png" />

## 6. Play

When all your instances are configured and running, you can start playing! Each instance will have its own dedicated input and audio devices, allowing you to play with your friends or family on the same computer.

Enjoy your gaming session!

## Keyboard shortcuts:
```
Super + F      Toggle fullscreen
```
```
Super + N      Toggle nearest neighbour filtering
```
```
Super + U      Toggle FSR upscaling
```
```
Super + Y      Toggle NIS upscaling
```
```
Super + I      Increase FSR sharpness by 1
```
```
Super + O      Decrease FSR sharpness by 1
```
```
Super + S      Take a screenshot
```
```
Super + G      Toggle keyboard grab
```
# Optional

## Multi GPU Support

> [!NOTE]
> This should be added directly to the game's arguments, do not add it to the environment variables.

Twinverse supports running multiple games on different GPUs.

Add the following line to your game's Steam arguments:

```bash
DRI_PRIME=1!

```

This makes GPU 1 be used in the game. You can adjust the numbers according to your system configuration.
