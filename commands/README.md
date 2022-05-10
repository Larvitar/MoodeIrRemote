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
      
You can see examples of other commands already defined in [base.json](base.json) and [example_custom.json](example_custom.json).

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
    toggle                                      - Play/Pause
    next                                        - Next song
    previous                                    - Previous song
    random                                      - Toggle 'random' option
    repeat                                      - Toggle 'repeat' option
    fav-current-item                            - Add currently playing item to 'Favorites'
    disconnect-renderer                         - Disconnect any external player from MoodeAudio.
    mute                                        - Toggle mute
    vol_up  : int value                         - Increase volume by 'value'    (0-100)
    vol_dn  : int value                         - Decrease volume by 'value'    (0-100)
    playlist  : str value : <bool shuffled>     - Clear play a playlist or other library entry
    radio  : str value                          - Clear play a radio
    
    # Custom WEB api command
    custom : str value : dict data
    
**Note:** By default script will try to disconnect any external player (renderer) that is currently connected but if that fails (see <code>disconnect-renderer</code>) command execution will continue anyway.

### Sets
`Moode` support setting of `sets` of defined commands. Depending on what `set` is currently defined a different action can be performed.

     "4": {                         <-- When button "4" is clicked
       "global": {                  <-- In every context
         "target": "moode",         <-- Trigger moode action
         "set_playlist": {          <-- Only when "set_playlist" is active
           "command": "playlist",
           "value": "Favorites"
         },
         "set_radio": {             <-- Only when "set_radio" is active
           "command": "radio",
           "value": "BBC Radio"
         }
       }
     },

This can be used to expand the defined action list when you're running out of buttons on your remote. You still need to define a button dedicated to switching between `sets`.

     "red": {
       "global": {
         "target": "moode",
         "command": "disconnect-renderer",   <-- Disconnect any active renderer (spotify, bluetooth etc.)
         "set": "set_playlist"               <-- Switch to set "set_playlist"
       }
     }

You can either define different buttons for different `sets` or make one button cycle between all states you defined:

     "red": {
       "global": {
         "target": "moode",         # set_playlist_1 -> set_playlist_2 -> set_radio -> set_playlist_1...
         "set_playlist_1": {
           "command": "disconnect-renderer",
           "set": "set_playlist_2"
         },
         "set_playlist_2": {
           "command": "disconnect-renderer",
           "set": "set_radio"
         },
         "set_radio": {
           "command": "disconnect-renderer",
           "set": "set_playlist_1"
         }
       }
     }

### Playlist
Optional <code>shuffled</code> (random) setting available. Set to <code>true</code> to always start playing at random, <code>false</code> to always play in order. If not set script will read current <code>random</code> state from Moode.

Command <code>playlist</code> supports library paths:

      "1": {
        "global": {
          "target": "moode",
          "command": "playlist",
          "value": "NAS/HomeServer/Music"
          "shuffled": true
        }
      }
    
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
Enabled only when Spotify is correctly configured and user was authorized. Spotify renderer has to be enabled in Moode settings and running. You also have to manually connect your device using Spotify at least once before it becomes available in Spotify API. 

Script will read device name from Moode config and try to locate that device in Spotify.

Available commands are:

    transfer-playback                               - Switch to Spotify, but do not start playback
    play
    pause
    toggle                                          - Play/Pause
    next                                            - Next song
    previous                                        - Previous song
    shuffle                                         - Toggle 'shuffle' option
    repeat                                          - Toggle 'repeat' setting: track --> context --> off
    mute                                            - Toggle mute
    vol_up : int value                              - Increase volume by 'value'    (0-100)
    vol_dn : int value                              - Decrease volume by 'value'    (0-100)
    seek : int value                                - Seek forward or backwards by 'value' miliseconds
    playlist : str value : <bool shuffled>          - Load a user playlist by name
    album : str value : <bool shuffled>             - Load a user saved album by name
    
### Albums and Playlists
Optional <code>shuffled</code> setting available. Set to <code>true</code> to always start playing at random, <code>false</code> to always play in order. If not set script will read current <code>shuffled</code> state from Spotify.

      "8": {
        "global": {
          "target": "spotify",
          "command": "playlist",
          "value": "Touhou Project",
          "shuffled": true
        }
      }
      "9": {
        "global": {
          "target": "spotify",
          "command": "playlist",
          "value": "Lord of the Rings Soundtrack",
          "shuffled": false
        }
      }

# Bluetooth
Possible when Moode is acting as bluetooth speaker. Script will try to read the name of the first connected BT player and execute commands on it.

Available commands are:

    mute                    - Toggle mute
    vol_up : int value     - Increase volume by 'value'    (0-100)
    vol_dn : int value     - Decrease volume by 'value'    (0-100)
    
# Examples

1. Same button for different playlists on Spotify/Moode

    First you'll need some buttons to switch between Spotify and Moode:
            
          # Switch to playback from Moode
          "red": {
            "global": {
              "target": "moode",
              "command": "disconnect-renderer"
            }
          }
          # Switch to playback from Spotify
          "green": {
            "global": {
              "target": "spotify",
              "command": "transfer-playback"
            }
          },
          # Or a single button to switch back and forth
          "source": {
            "moode": {
              "target": "spotify",
              "command": "transfer-playback"
            },
            "spotify": {
              "target": "moode",
              "command": "disconnect-renderer"
            }
          }
          
    Now configure <code>1</code> to start different playlists depending on what's currently active:
    
        "1": {
            "spotify": {
              "target": "spotify",
              "command": "playlist",
              "value": "SpotifyList1"
            },
            "global": {
              "target": "moode",
              "command": "playlist",
              "value": "MpdList2"
            }
          }
    
   When Spotify is active <code>SpotifyList1</code> will start playing, <code>MpdList2</code> otherwise.
