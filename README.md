# MoodeIrRemote
Simple project designed to help with IR remote setup for MoodeAudio.

# Supports
1. Moode Web API
2. Spotify control
3. Shell commands
4. BT mode volume control

# IR Setup
TODO

# Configuration
Configuration is stored in <code>config.json</code>

    {
      "remotes": ["default.json"],              # List of remote controllers that will be loaded on startup
      "ir_gpio_pin":  24,                       # GPIO pin where IR receiver is attached
      "logging": {
        "level": "INFO",                        # Level of console logs
        "file_level": "DEBUG",                  # Level of file logs
        "global_level": "WARNING",              # Level of root logger (logs from any imported libraries)
        "log_all_to_file": true                 # Write logs from imported libraries to log file
      },
      "spotify": {                              # Spotify configuration
        "redirect_uri": "http://moode.local:8080/auth",
        "client_id": "",
        "client_secret": "",
        "auth_server_listen_ip": "0.0.0.0",
        "auth_server_listen_port": 8080
      }
    }
        
# Remotes configuration
Remotes configuration is stored in <code>keymaps/*.json</code> files. Run the script with <code>setup <file_name></code> parameter and it will guide you through the process of configuring your own remote. If <code>file_name</code> is not provided <code>default.json</code> will be used.

        > python3  mpd_control.py setup test_remote.json
        Running setup of test_remote.json
        Button "power"  (recorded: 0) [(R)ecord / (D)elete last / (C)lear all / (N)ext / (E)nd]: r
                Press the key again to verify
        Button "power"  (recorded: 1) [(R)ecord / (D)elete last / (C)lear all / (N)ext / (E)nd]: n
        Button "ok"     (recorded: 0) [(R)ecord / (D)elete last / (C)lear all / (N)ext / (E)nd]: r
                Press the key again to verify
        Button "ok"     (recorded: 0) [(R)ecord / (D)elete last / (C)lear all / (N)ext / (E)nd]: e
        Setup result: {....}
        
You can run <code>Record</code> multiple times in order to assign multiple buttons to the same function (i.e. <code>Right</code> and <code>Channel Up</code> for <code>next song</code>).
        
Script will scan through commands defined in <code>commands/base.json</code> and <code>commands/custom.json</code>. If you run <code>setup</code> on already existing keymap, you'll be able to update it.

Run script in test mode if you want to verify a keymap:

        > python3 mpd_control.py test test_remote.json
        MoodeIrController:INFO - Loaded keymap test_remote.json
        MoodeIrController:INFO - Monitoring started (test mode)
        Key "ok" received.
        Key "power" received.
        
**Note:** Some remotes use 2 alternating codes for the same button. Script will try to recognize it and ask you to click it multiple times but if you run into any troubles just try running <code>Record</code> multiple times.

**Note:** If by accident you assign same button to multiple functions (or if 2 remotes send same code for different buttons) script will only run the first action that matches that code.

# Spotify
Spotify Premium is required. 

1. You will need to create a Spotify developer app.

    1. Log into https://developer.spotify.com/dashboard/login
    2. Click on "CREATE AN APP" and fill required information.
    3. Save your "Client ID" and "Client Secret".
    
2. Now open <code>config.json</code>:
    1. Fill <code>client_id</code> and <code>client_secret</code>.
    2. <code>redirect_uri</code> - replace <code>moode.local</code> with your RPi IP if <code>moode.local</code> is not accessible from your PC.
    3. <code>auth_server_listen_ip</code> - IP to start the auth server on. <code>0.0.0.0</code> will listen on every interface.
    4. <code>auth_server_listen_port</code> - Port of the auth server. Change if something else is already using this port (You'll also need to change this value in <code>redirect_uri</code>).
    
3. Open Spotify developer page:
    1. In your app page click <code>EDIT SETTINGS</code>.
    2. Add address from <code>redirect_uri</code> in **Redirect URIs** section.
    
4. You can start <code>mpd_control.py</code> now. If all Spotify settings were filled script should run a server at <code>http://moode.local:8888 </code>. 
    1. Open this address in your browser and you'll be presented with a **Authorize with Spotify** button. Click it and allow your app to access to your Spotify account.
    2. You should see **Authentication success** message.
    3. Spotify should now work properly. 

**Note:** If any of spotify settings is not filled this setup process will be skipped.
 
**Note:** Script will only wait for 2 minutes for you to complete authentication process. After that server will shutdown and Spotify will not work.

**Note:** If Spotify authorization expires (password change, revoked app permissions etc.) script will drop all spotify commands and a restart will be required in order to run authorization process again.

# Commands
Basic command config:

      "vol_up": {                   <-- Button name
        "moode": {                  <-- When this command can be run (currently active player)
          "target": "moode",        <-- Where to execute command
          "command": "vol_up",      <-- Command to execute
          "value": 2                <-- Value to be send (only applicable for some commands)
        }
      }
      
Possible states are: <code>roonbridge</code>, <code>airplay</code>, <code>bluetooth</code>, <code>squeezelite</code>, <code>spotify</code>, <code>input</code>, <code>moode</code>, <code>global</code> (always)\
Possible targets are: <code>bluetooth</code>, <code>spotify</code>, <code>moode</code>, <code>shell</code>

**Note:** Only one command can be run at the same time. <code>global</code> will be run only if active player does not match any other command.

See [commands](commands/README.md).
