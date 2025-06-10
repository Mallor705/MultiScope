# Nemirtingas Epic Emulator

This is a project to try to understand how the eos api works under the hood.

Valid debug levels: (only in debug version)

```
TRACE: Very verbose, will log DEBUG + All functions enter
DEBUG: Very verbose, will log INFO  + Debug infos like function parameters
INFO : verbose     , will log WARN  + some informations about code execution and TODOs
WARN : not verbose , will log ERR   + some warnings about code execution
ERR  : not verbose , will log FATAL + errors about code execution
FATAL: not verbose , will log only Fatal errors like unimplemented steam_api versions
OFF  : no logs     , saves cpu usage when running the debug versions
```


# Internals - Any reference to "config file" is the emulator config file: NemirtingasEpicEmu.json
- **The config file is generated if it is missing**. If you're lazy to build one or copy the example, just don't do it, the emu will do it for you. **You might want** to create a simple json with only { "username": "MyAwesomeUsername" } to let the emulator know who you are and generate a consistent id.
- { "username": "DefaultName" }: it is used to generate your epicid if you want to (see "epicid" entry below). Some games use it to set your in-game username, some don't (like civilization 6).
- **[MUST BE UNIQUE][AUTO GENERATED]** { "epicid": "156abc156f1c5487f91c" }: is generated if it is missing or invalid. An epicid is invalid if it does contain non-hex chars (Anything not 0,1,2,3,4,5,6,7,8,9,a,b,c,d,e,f) but it **can** start with 0x (the hex prefix)
  - If the "epicid" is missing or invalid, it will be generated based on some rules
    1. Your username is "DefaultName" ( "username": "DefaultName"), the epicid is generated randomly. (it prevents users that doesn't setup correctly the emu to have duplicated epicids)
    2. Your username is not "DefaultName" ("username": "SomethingGreat"), the epicid is generated using your username as a seed making it the same whatever you do. (Playing another game, another computer)
    3. If it is not invalid or missing, it will be left untouched, so you can modify it to any **valid** epicid you want
- **[MUST BE UNIQUE][AUTO GENERATED]** { "productuserid": "156abc156f1c5487f91c" }: is generated if it is missing or invalid. Is it used to identify a peer on the network allowing multiplayer. An productuserid is invalid if it does contain non-hex chars (Anything not 0,1,2,3,4,5,6,7,8,9,a,b,c,d,e,f)
  - If the "productuserid" is missing or invalid, it will be generated based on some rules
    1. If the product user id is invalid or missing, it will be generated with the appid + epicid as a seed.
    2. If it is not invalid or missing, it will be left untouched, so you can modify it to any **valid** epicid you want
- { "appid": "CrabTest" }: This **will** be used to search friends and lobbies that use the same appid. It can be retrieved on https://epicdata.info/items/ For example, for Satisfactory experimental, search for Satisfactory and click on the main game's item. The appid is in the "releaseInfo", the "appId" field.
- { "savepath": "xxxxx" }: it is used to decide where your "cloud" saves, achievements, items, dlcs go. It has 1 special value:
  1. { "savepath" : "appdata" }:
    - On Windows, saves will go in: %appdata%\NemirtingasEpicEmu\
    - On Linux, saves will go in: $XDG_DATA_HOME/NemirtingasEpicEmu or $HOME/.local/share/NemirtingasEpicEmu if $XDG_DATA_HOME is not set in the env.
    - On MacOS, saves will go in $HOME/NemirtingasEpicEmu
  2. { "savepath": "something" }: (savepath can be empty like { "savepath": "" }), saves will go in the directory specified by savepath, relative to the game's working directory. In the example, it could be "game dir"\something\NemirtingasEpicEmu or "game dir"\NemirtingasEpicEmu.
- { "disable_online_networking": true|false }: it will try to disable all **online** networking, not lan or vpn. This prevents games to go on the internet. If your game crash and you've set this to true, try to set it to false. I use my own solution to override the classic network functions, it can be buggy.
- { "enable_overlay": true|false}: For **for future use**, it will allow you to have an overlay like the EOS social overlay, invite people to games and receive notifications like achievements unlocked.
- { "gamename": "DefaultGameName" }: If the gamename is "DefaultGameName" or missing, the emulator will replace it with what the game provides it.
- { "unlock_dlcs": true|false }: This will try to enable all dlcs/items that the game requests. If the game wants more infos on em it might not work. (Like unlock_all_dlcs on a steam emu, some need you to provide the appid = name).
- { "log_level": "OFF|FATAL|ERR|WARN|INFO|DEBUG|TRACE" }: Decides how verbose the emulator will be, for debugging purpose. Defaults to OFF
- { "language": "en" }: Sets the user language. It follows the ISO639 language codes. Search on the web for your language code if needed. Defaults to "en".
