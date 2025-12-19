/*
 * KWin Script: Assign each gamescope instance to a different monitor (Fullscreen Mode)
 *
 * This script is intended for use with MultiScope to automatically place each
 * gamescope window on a separate monitor, maximizing it to fill the entire screen.
 * Only one gamescope instance will be assigned per monitor. If there are more
 * instances than monitors, the extras will not be assigned.
 *
 * Usage:
 *   - This script is loaded automatically by MultiScope when fullscreen mode is selected.
 *   - It listens for window addition and removal events to keep the layout updated.
 *
 * How it works:
 *   - Finds all windows with resourceClass "gamescope".
 *   - Assigns each to a monitor, setting its geometry to cover the full screen.
 *   - Removes window borders for a clean fullscreen experience.
 */

function getGamescopeClients() {
  // Returns a list of all gamescope windows currently managed by KWin.
  var allClients = workspace.windowList();
  var gamescopeClients = [];
  for (var i = 0; i < allClients.length; i++) {
    if (allClients[i].resourceClass == "gamescope") {
      gamescopeClients.push(allClients[i]);
    }
  }
  return gamescopeClients;
}

function gamescopePerMonitor() {
  // Assigns each gamescope instance to a different monitor, fullscreen.
  var gamescopeClients = getGamescopeClients();
  var screens = workspace.screens;
  var totalScreens = screens.length;

  // Only one instance per monitor is allowed.
  var count = Math.min(gamescopeClients.length, totalScreens);

  for (var i = 0; i < count; i++) {
    var monitor = screens[i];
    var monitorX = monitor.geometry.x;
    var monitorY = monitor.geometry.y;
    var monitorWidth = monitor.geometry.width;
    var monitorHeight = monitor.geometry.height;

    // Remove window border and maximize to monitor geometry
    gamescopeClients[i].noBorder = true;
    gamescopeClients[i].frameGeometry = {
      x: monitorX,
      y: monitorY,
      width: monitorWidth,
      height: monitorHeight,
    };
  }
}

// Update layout whenever a gamescope window is added or removed
workspace.windowAdded.connect(gamescopePerMonitor);
workspace.windowRemoved.connect(gamescopePerMonitor);

// Note: This script should only be loaded when MultiScope is in fullscreen mode.