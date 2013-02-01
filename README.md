# Changes

  -Feb 01 Started working on sudo permissions for reading and moving to files
  -Feb 01 Moved SFTP setup to use parmiko ssh to allow auto adding hostkeys
  -Feb 01 Added symlink support
  -Jan 31 Updated install instructions and began debugging linux installs
  -Jan 23 Added Paramiko for OSX and Linux Support 

# Info

Sublime Text plugin to browse and edit files over sftp/ssh2

- Uses the power of the quick panel completions to browse around files
- Automatically hooks into file saves and uploads after saving
- Optionally, continues to spider the file tree populating the quick panel list

# Installation

## Windows

1. Download this package, save, and extract to your sublime text packages folder.

2. Download and install PuTTY, preferably the whole package.

   - (PuTTYgen is needed to create keys)
   
   - (PuTTY is needed to save sessions, (host,username,key information)
   
   - (Pageant to manage those sessions)
   
   - http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html

3. Make psftp accessible to the plugin
   
   - Copy `psftp.exe` to `Mote\`

##OSX

1. Download this package, save, and extract to your sublime text packages folder.
    
   - From the 'Sublime Text 2' Menu Select Preferences -> Browse Packages...

   - Copy the Mote directoy to this folder

2. Close and Reopen Sublime Text 2

If Connections do not work make sure you have connected to the server once from the command line using:
  ssh <username>@<domain> so you can accept the hostkey making it available to the plugin

##Linux

1. Download this package, save, and extract to your sublime text packages folder.
    
   - From the 'Sublime Text 2' Menu Select Preferences -> Browse Packages...

   - Copy the Mote directoy to this folder

2. Install python-dev so you can compile pycrypto
    
   - Download PyCrypto from https://github.com/dlitz/pycrypto

   - chmod +x setup.py

   - run ./setup.py build

   - copy the Crypto folder from build->lib.<OS>-<PythonVer> to the Mote Lib Folder overwriting the Crypto directory there

3. Close and Reopen Sublime Text 2

If Connections do not work make sure you have connected to the server once from the command line using:
  ssh <username>@<domain> so you can accept the hostkey making it available to the plugin

#Usage

## Add Servers

edit the `Mote\serves.json` file



connection_string
  connection string that's going to be passed to psftp
  See http://the.earth.li/~sgtatham/putty/0.61/htmldoc/Chapter6.html#psftp-pubkey

idle_recursive
  whether or not Mote should spider your sftp in the background

default_path
  default path to `cd` into
  
password
  password for sftp. Use this option if your PuTTY session name or password contains a space
  
private_key
  path to private key. Remember to escape the `\` into `\\`

NOTE: if you wish to place your password here, it cannot contain a '!'
Due to limitations of psftp
See http://the.earth.li/~sgtatham/putty/0.61/htmldoc/Chapter6.html#psftp-cmd-pling

### servers.json

Make sure you have a valid json object here.
http://jsonlint.com/

```json
{
    "SERVER_NICKNAME":{
        "connection_string": "saved_putty_session_name",
        "idle_recursive": true
    },
    "SERVER_NICKNAME2":{
        "connection_string": "USERNAME@HOSTNAME_OR_IP",
        "password":"MYPASSWORD",
        "idle_recursive": false,
        "default_path": "iniital/path/to/open/to"
    },
    "SERVER_NICKNAME3":{
        "connection_string": "USERNAME@HOSTNAME_OR_IP",
        "password":"MYPASSWORD",
        "private_key":"C:\\PATH\\TO\\PRIVATE\\KEY.ppk",
        "idle_recursive": false,
        "default_path": "iniital/path/to/open/to"
    }
}
```

## Then Invoke Mote

### Run through the command palette

    Ctrl+Shift+P
    Mote
    Enter
    
### Or, Add to your keybinds

```json
{ "keys": ["ctrl+m"], "command": "mote" }
```
    
Then

   `Ctrl+m`

## Then browse around and edit

- Browse around. The file list populates as you delve deeper into the file tree.
- Click on a file to download to a temp folder and open it
- Any saves on that file will automatically upload it. 

#ToDos

1. Allow for port configuration with paramiko for linux osx
2. Automate build for Crypto on install
3. If hostkey doesnot always exist direct user to ssh to location once before trying to connect
