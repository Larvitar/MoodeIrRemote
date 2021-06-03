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
      "remotes": [],            # List of remote controllers that will be loaded on startup
      "ir_gpio_pin":  24,       # GPIO pin where IR receiver is attached
      "spotify": {  # Spotify configuration
        "device_name": "Moode Spotify",
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "http://moode.local:8888/auth",
        "auth_server_listen_ip": "0.0.0.0",
        "auth_server_listen_port": 8888
      }
    }
        
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

# Remotes configuration
Remotes configuration is stored in <code>keymaps/*.json</code> files. Run the script with <code>setup</code> parameter and it will guide you through the process of configuring your own remote. This configuration will be saved into <code>keymaps/default.json</code>

        python3  mpd_control.py setup
        # TODO:

By default the script will scan through commands defined in <code>commands/base.json</code> and <code>commands/custom.json</code> and only ask for keys to commands that are missing. Run <code>mpd_control.py clear setup</code> if you want to reconfigure every key.

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
