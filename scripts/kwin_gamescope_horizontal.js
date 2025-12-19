/*
 * KWin Script: kwin_gamescope_horizontal.js
 * 
 * This script arranges multiple gamescope windows in a horizontal splitscreen layout.
 * It is intended for use with MultiScope to automatically tile game instances across monitors.
 * 
 * - Each group of up to 4 gamescope instances is assigned to a monitor.
 * - Within each monitor, instances are arranged horizontally (side by side).
 * - If there are more than 4 instances, additional monitors are used (cycling if needed).
 * - The script ensures that gamescope windows are always kept above other windows when active.
 * 
 * This script is automatically loaded and managed by MultiScope when "horizontal splitscreen" is selected.
 */

// Position and size multipliers for up to 4 instances per monitor (horizontal layout)
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
 * Returns a list of all gamescope client windows.
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
 * Returns the number of gamescope clients assigned to a given output (monitor).
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
 * Main function to arrange gamescope windows in horizontal splitscreen groups.
 * Each group of up to 4 instances is tiled horizontally on a monitor.
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

// Connect the arrangement logic to KWin window events
workspace.windowAdded.connect(gamescopeSplitscreen);
workspace.windowRemoved.connect(gamescopeSplitscreen);
workspace.windowActivated.connect(gamescopeAboveBelow);