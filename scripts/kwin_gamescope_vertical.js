/*
 * KWin Script: Vertical Splitscreen Layout for Gamescope
 *
 * This script automatically arranges all windows with the resource class "gamescope"
 * into a vertical splitscreen layout, distributing up to 4 instances per monitor.
 * Each group of up to 4 instances is assigned to a monitor, and within each monitor,
 * the windows are tiled vertically according to the number of instances.
 *
 * - For 1 instance: occupies the full monitor.
 * - For 2 instances: each gets half the monitor, stacked vertically.
 * - For 3 or 4 instances: each gets a quarter of the monitor, stacked in a 2x2 grid.
 *
 * The script also ensures that gamescope windows are kept above other windows when active.
 * It automatically updates the layout whenever a gamescope window is added, removed, or activated.
 */

// X, Y, width, and height ratios for each possible number of splits (1-4)
const x = [
  [],
  [0],
  [0, 0],
  [0, 0, 0.5],
  [0, 0.5, 0, 0.5]
];

const y = [
  [],
  [0],
  [0, 0.5],
  [0, 0.5, 0.5],
  [0, 0, 0.5, 0.5]
];

const width = [
  [],
  [1],
  [1, 1],
  [1, 0.5, 0.5],
  [0.5, 0.5, 0.5, 0.5]
];

const height = [
  [],
  [1],
  [0.5, 0.5],
  [0.5, 0.5, 0.5],
  [0.5, 0.5, 0.5, 0.5]
];

/**
 * Returns a list of all gamescope clients (windows).
 */
function getGamescopeClients() {
  var allClients = workspace.windowList();
  var gamescopeClients = [];

  for (var i = 0; i < allClients.length; i++) {
    if (
      allClients[i].resourceClass == "gamescope"
    ) {
      gamescopeClients.push(allClients[i]);
    }
  }
  return gamescopeClients;
}

/**
 * Counts how many gamescope clients are assigned to a given output (monitor).
 */
function numGamescopeClientsInOutput(output) {
  var gamescopeClients = getGamescopeClients();
  var count = 0;
  for (var i = 0; i < gamescopeClients.length; i++) {
    if (gamescopeClients[i].output == output) {
      count++;
    }
  }
  return count;
}

/**
 * Ensures that all gamescope windows are kept above other windows when one is active.
 */
function gamescopeAboveBelow() {
  var gamescopeClients = getGamescopeClients();
  for (var i = 0; i < gamescopeClients.length; i++) {
    if (
      workspace.activeWindow.resourceClass == "gamescope"
    ) {
      gamescopeClients[i].keepAbove = true;
    } else {
      gamescopeClients[i].keepAbove = false;
    }
  }
}

/**
 * Arranges gamescope windows in a vertical splitscreen layout.
 * Each group of up to 4 instances is assigned to a monitor.
 * Within each monitor, windows are tiled vertically.
 */
function gamescopeSplitscreen() {
  var gamescopeClients = getGamescopeClients();
  var screens = workspace.screens;
  var totalScreens = screens.length;

  for (var i = 0; i < gamescopeClients.length; i++) {
    var groupIndex = Math.floor(i / 4); // group of 4 instances per monitor
    var monitor = screens[groupIndex % totalScreens]; // distribute among available monitors

    var monitorX = monitor.geometry.x;
    var monitorY = monitor.geometry.y;
    var monitorWidth = monitor.geometry.width;
    var monitorHeight = monitor.geometry.height;

    var playerIndex = i % 4 + 1; // position within the group (1-based)
    var playerCount = Math.min(4, gamescopeClients.length - groupIndex * 4);

    gamescopeClients[i].noBorder = true;
    gamescopeClients[i].frameGeometry = {
      x: monitorX + x[playerCount][playerIndex - 1] * monitorWidth,
      y: monitorY + y[playerCount][playerIndex - 1] * monitorHeight,
      width: monitorWidth * width[playerCount][playerIndex - 1],
      height: monitorHeight * height[playerCount][playerIndex - 1],
    };
  }
  gamescopeAboveBelow();
}

// Connect layout logic to KWin window events
workspace.windowAdded.connect(gamescopeSplitscreen);
workspace.windowRemoved.connect(gamescopeSplitscreen);
workspace.windowActivated.connect(gamescopeAboveBelow);