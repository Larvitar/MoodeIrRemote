# Overview
You can define your own buttons here and script will always ask you to assign an IR code to it during <code>setup</code> process.

You can easily define a different command for different contexts (active players) as well as a command that is supposed to run in every context (<code>global</code>).

      "vol_dn": {               <-- Button name
        "moode": {              <-- Run this command only when Moode is active
          "target": "moode",    <-- Where to run this command
          "command": "vol_dn",
          "value": 2
        },
        "spotify": {            <-- Run this command only when Spotify is active
          "target": "spotify",
          "command": "vol_dn",
          "value": 2
        },
        "bluetooth": {          <-- Run this command only when Bluetooth is active
          "target": "bluetooth",
          "command": "vol_dn",
          "value": 2
        }
      },
      "power": {
        "global": {             <-- Run this command in every context
          "target": "moode",
          "command": "poweroff"
        }
      }
      
You can see examples of other commands already defined in <code>commands/base.json</code> and <code>commands/custom.json</code>

Possible states are: <code>roonbridge</code>, <code>airplay</code>, <code>bluetooth</code>, <code>squeezelite</code>, <code>spotify</code>, <code>input</code>, <code>moode</code>, <code>global</code> (always)\
Possible targets are: <code>bluetooth</code>, <code>spotify</code>, <code>moode</code>, <code>shell</code>

**Note:** Only one command can be run at the same time. <code>global</code> will be run only if active player does not match any other command.

### Command lists
Command lists are also supported so you can run multiple commands at one button click:

      "red": {
        "global": [
          {
            "target": "shell",
            "command": "echo \"some command\""
          },
          {
            "target": "moode",
            "command": "radio",
            "value": "RTR Radio"
          }
        ]
      }

# Shell
You can run basically any shell command. List of commands are also supported:

      "1": {
        "moode": {
          "target": "shell",
          "command": ["mpc clear", "mpc load \"Fate Series OST\"", "mpc play"]
        }
      }
      
Please take note that <code>ShellCommandsHandler</code> will not take care of renderer switching so you can end up with Spotify and MPD playing at the same time etc.

# Moode
Commands that can be run using Moode Web API. Supported commands are:

    poweroff
    reboot
    play
    pause
    toggle                  - Play/Pause
    next                    - Next song
    previous                - Previous song
    random                  - Toggle 'random' option
    repeat                  - Toggle 'repeat' option
    disconnect-renderer     - Disconnect external player from MoodeAudio. Some might not work (bluetooth)
    mute                    - Toggle mute
    vol_up  : int value     - Increase volume by 'value'    (0-100)
    vol_dn  : int value     - Decrease volume by 'value'    (0-100)
    seek  : int value       - Seek forward or backwards by 'value' seconds
    playlist  : str value   - Clear play a playlist
    radio  : str value      - Clear play a radio
    
    # Custom WEB api command
    custom : str value : dict data
    
**Note:** By default script will try to disconnect any external player (renderer) that is currently connected but if that fails (see <code>disconnect-renderer</code>) command execution will continue anyway.
    
### Custom commands
You can send any command that is not defined above, but you have to take care of some things yourself.

      "button": {
        "global": {
          "target": "moode",
          "command": "custom",
          "value": "moode.php?cmd=clear_play_item"      <-- Actual command
          "data": {some data}                           <-- Optional data dictionary. Required for some POST requests.
        }
      }

# Spotify
Enabled only when Spotify is correctly configured and user was authorized. Script will read device name from MoodeAudio config and try to locate that device in Spotify.

Available commands are:

    play
    pause
    toggle                  - Play/Pause
    next                    - Next song
    previous                - Previous song
    shuffle                 - Toggle 'shuffle' option
    repeat                  - Change 'repeat' setting: track --> context --> off
    mute                    - Toggle mute
    vol_up  : int value     - Increase volume by 'value'    (0-100)
    vol_dn  : int value     - Decrease volume by 'value'    (0-100)
    seek  : int value       - Seek forward or backwards by 'value' seconds
    playlist  : str value   - Load a user playlist by name
    album  : str value      - Load a user saved album by name
    
Most commands will only work when Spotify is already active on your device. <code>playlist</code> and <code>album</code> will force connection and playback regardless of current context.

# Bluetooth
Possible when Moode is acting as bluetooth speaker. Script will try to read the name of the first connected BT player and execute commands on it.

Available commands are:

    mute                    - Toggle mute
    vol_up  : int value     - Increase volume by 'value'    (0-100)
    vol_dn  : int value     - Decrease volume by 'value'    (0-100)