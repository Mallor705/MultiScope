// This script is executed by the HandlerParser service in Python.
// It mocks the Game object and executes the handler.js file.

const fs = require('fs');
const vm = require('vm');

// The path to the handler.js file is passed as a command-line argument.
const handlerPath = process.argv[2];
if (!handlerPath) {
    console.error("Usage: node handler_parser.js <path_to_handler.js>");
    process.exit(1);
}

// Mock the Game object that the handler.js script will interact with.
const Game = {
    GameName: '',
    ExecutableName: '',
    GUID: '',
    SteamID: '',
    ExecutableToLaunch: '',
    LauncherExe: '',
    SymlinkGame: true,
    SymlinkExe: false,
    SymlinkFolders: false,
    KeepSymLinkOnExit: true,
    SymlinkFiles: [],
    CopyFiles: [],
    HardcopyGame: false,
    HardlinkGame: false,
    ForceSymlink: false,
    DirSymlinkExclusions: [],
    FileSymlinkExclusions: [],
    FileSymlinkCopyInstead: [],
    DirSymlinkCopyInstead: [],
    DirSymlinkCopyInsteadIncludeSubFolders: false,
    SymlinkFoldersTo: [],
    HardlinkFoldersTo: [],
    ChangeExe: false,
    CopyCustomUtils: [],
    Hook: {},
    ProtoInput: {},
    // Add a no-op function for AddOption to prevent errors
    AddOption: function() {},
    // Add other properties as needed in the future.
};

const Hub = {
    Handler: {
      Id: '',
      Version: '',
    },
    Maintainer: {
      Name: '',
      Id: '',
    },
};

// Create a context for the script execution.
const context = {
    Game: Game,
    Hub: Hub,
    console: console,
};
vm.createContext(context);


// Read the handler.js file.
const handlerCode = fs.readFileSync(handlerPath, 'utf8');

// Execute the handler.js code in the sandboxed context.
try {
    vm.runInContext(handlerCode, context);
} catch (e) {
    console.error("Error executing handler.js:", e);
    process.exit(1);
}

// Output the extracted data as JSON.
console.log(JSON.stringify({
    GameName: Game.GameName,
    ExecutableName: Game.ExecutableName,
    GUID: Game.GUID,
    SteamID: Game.SteamID,
    ExecutableToLaunch: Game.ExecutableToLaunch,
    LauncherExe: Game.LauncherExe,
    SymlinkGame: Game.SymlinkGame,
    SymlinkExe: Game.SymlinkExe,
    SymlinkFolders: Game.SymlinkFolders,
    KeepSymLinkOnExit: Game.KeepSymLinkOnExit,
    SymlinkFiles: Game.SymlinkFiles,
    CopyFiles: Game.CopyFiles,
    HardcopyGame: Game.HardcopyGame,
    HardlinkGame: Game.HardlinkGame,
    ForceSymlink: Game.ForceSymlink,
    DirSymlinkExclusions: Game.DirSymlinkExclusions,
    FileSymlinkExclusions: Game.FileSymlinkExclusions,
    FileSymlinkCopyInstead: Game.FileSymlinkCopyInstead,
    DirSymlinkCopyInstead: Game.DirSymlinkCopyInstead,
    DirSymlinkCopyInsteadIncludeSubFolders: Game.DirSymlinkCopyInsteadIncludeSubFolders,
    SymlinkFoldersTo: Game.SymlinkFoldersTo,
    HardlinkFoldersTo: Game.HardlinkFoldersTo,
    ChangeExe: Game.ChangeExe,
    CopyCustomUtils: Game.CopyCustomUtils,
}));
