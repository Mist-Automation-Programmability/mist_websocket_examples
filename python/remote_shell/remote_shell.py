"""
-------------------------------------------------------------------------------

    Remote Shell for Mist Devices
    ----------------------------

    Authors:
      - Thomas Munzer (tmunzer@juniper.net)
      - Hartmut Schroeder

    GitHub Repository:
      https://github.com/Mist-Automation-Programmability/mist_websocket_examples

    License:
      MIT License

-------------------------------------------------------------------------------
Description:
    This Python script opens an interactive remote shell session to a Mist device
    using the Mist API. It connects via WebSocket and provides a terminal-based
    shell interface.

-------------------------------------------------------------------------------
Requirements:
    - websocket-client: https://pypi.org/project/websocket-client/
    - python-dotenv:    https://pypi.org/project/python-dotenv/
    - sshkeyboard:      https://pypi.org/project/sshkeyboard/
    - requests:         https://pypi.org/project/requests/

-------------------------------------------------------------------------------
Configuration:
    You can provide required parameters in one of the following ways:
      1. Inline in the PARAMETERS section of this script.
      2. Using an environment file (recommended).
      3. As command-line arguments.

    Best Practice:
      - Store MIST_HOST and MIST_APITOKEN in an environment file.
      - Provide site and device IDs via command-line arguments.

-------------------------------------------------------------------------------
Command-Line Arguments:
    -h, --help              Show this help message and exit.
    -c, --cloud=HOST        Set the Mist cloud host (default: api.mist.com).
    -s, --site=SITE_ID      Set the site_id.
    -d, --device=DEVICE_ID  Set the device_id.
    -e, --env=FILE          Specify the environment file (default: "~/.mist_env").
    -l, --log_file=FILE     Set the log file path (default: "./websocket.log").

-------------------------------------------------------------------------------
Examples:
    python3 remote_shell.py
    python3 remote_shell.py --site=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 --device=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

"""
import sys
import os
import logging
import json
import time
import re
import threading
import shutil
import getopt
from sshkeyboard import listen_keyboard, stop_listening
from dotenv import load_dotenv
import websocket
import requests
if os.name == 'nt':
    import msvcrt
else:
    import termios

MSG_RECEIVED = 0

ENV_FILE = "~/.mist_env"
MIST_HOST = "api.mist.com"
MIST_APITOKEN = ''
MIST_SITE_ID = '00000000-0000-0000-0000-000000000000'
MIST_DEVICE_ID = '00000000-0000-0000-1000-000000000000'
LOG_FILE="./websocket.log"


class MistSocket:
    """
    Handles the WebSocket connection to the Mist shell, manages terminal resize, input/output,
    and keyboard event listening for interactive shell sessions.
    
    Args:
        uri (str): The WebSocket URI to connect to.
    """
    def __init__(self, uri:str) -> None:
        """
        Initializes the MistSocket with the given WebSocket URI.
        
        Args:
            uri (str): The WebSocket URI.
        """
        self.uri = uri
        self.ws = None

    def start(self):
        """
        Starts the WebSocket connection, resizes the terminal, and begins listening for keyboard events.
        Launches a thread for incoming WebSocket messages and listens for keyboard input to send to the shell.
        """
        #websocket.enableTrace(True)
        self.ws = websocket.create_connection(self.uri)
        self._resize()
        while not self.ws.connected:
            time.sleep(1)
        thread_in = threading.Thread(target=self._ws_in)
        thread_in.start()
        listen_keyboard(on_release=self._ws_out, delay_second_char=0, delay_other_chars=0, lower=False)

    def _pty_size(self):
        """
        Gets the current terminal size (rows, columns).
        
        Returns:
            tuple: (rows, columns) of the terminal.
        """
        rows, cols = 24, 80
        cols, rows = shutil.get_terminal_size()
        #print ('cols=', cols, '  rows=', rows)
        return rows, cols

    def _resize(self):
        """
        Sends a resize event to the WebSocket server with the current terminal size.
        """
        rows, cols = self._pty_size()
        self.ws.send(json.dumps({'resize': {'width': cols, 'height': rows}}))

    def _ws_in(self):
        """
        Listens for incoming messages from the WebSocket and writes them to stdout.
        Handles connection loss gracefully.
        """
        while self.ws.connected:
            if self.ws.sock:
                try:
                    data = self.ws.recv()
                    if data:
                        line = data.decode('utf-8')
                        output = re.sub('[\x00]', '', line)
                        sys.stdout.write(output)
                        sys.stdout.flush()
                except:
                    print('## Exception on listen thread. Perhaps lost connection ##')
                    return

    def _ws_out(self, key):
        """
        Handles keyboard events and sends the corresponding key codes to the WebSocket server.
        Special handling for navigation keys and shell exit.
        
        Args:
            key (str): The key pressed.
        """
        if self.ws.connected:
            if key:
                if key == "enter":
                    k = "\n"
                elif key == "space":
                    k = " "
                elif key == "tab":
                    k = "\t"
                elif key == "up":
                    k = "\x00\x1b[A"
                elif key == "right":
                    k = "\x00\x1b[C"
                elif key == "down":
                    k = "\x00\x1b[B"
                elif key == "left":
                    k = "\x00\x1b[D"
                elif key == "backspace":
                    k = "\x08"
                elif key == "~":
                    print('## Exit from shell pressed ##')
                    self.ws.sock.shutdown(2)
                    self.ws.sock.close()
                    stop_listening()
                    return
                else:
                    k = key
                data=f"\00{k}"
                data_byte = bytearray()
                data_byte.extend(map(ord, data))
                try:  
                    self.ws.send_binary(data_byte)
                except:
                    print('## Exception on key-enter thread. Perhaps lost connection ##')
                    return


def _load_env(env_file:str, mist_host:str, mist_apitoken:str, mist_site_id:str):
    """
    Loads environment variables from a .env file and overrides the provided Mist API parameters if present.
    
    Args:
        env_file (str): Path to the .env file.
        mist_host (str): Default Mist host.
        mist_apitoken (str): Default Mist API token.
        mist_site_id (str): Default Mist site ID.
    
    Returns:
        tuple: (mist_host, mist_apitoken, mist_site_id) with values from the environment or defaults.
    """
    if env_file.startswith("~/"):
        env_file = os.path.join(
            os.path.expanduser("~"), env_file.replace("~/", "")
        )
    load_dotenv(dotenv_path=env_file, override=True)
    if os.getenv("MIST_HOST"):
        mist_host = os.getenv("MIST_HOST")
    if os.getenv("MIST_APITOKEN"):
        mist_apitoken = os.getenv("MIST_APITOKEN")
    if os.getenv("MIST_SITE_ID"):
        mist_site_id = os.getenv("MIST_SITE_ID")
    return mist_host, mist_apitoken, mist_site_id


def get_shell_info(mist_host:str, mist_site_id:str, mist_device_id:str, mist_apitoken:str):
    """
    Requests shell connection information from the Mist API for a given device.
    
    Args:
        mist_host (str): Mist API host.
        mist_site_id (str): Mist site ID.
        mist_device_id (str): Mist device ID.
        mist_apitoken (str): Mist API token.
    
    Returns:
        dict: Shell connection data (including WebSocket URL) if successful, else None.
    """
    url = f"https://{mist_host}/api/v1/sites/{mist_site_id}/devices/{mist_device_id}/shell"
    headers={'Authorization': f'Token {mist_apitoken}'}
    response = requests.post(url=url, headers=headers, json={})
    if response.status_code == 200:
        data = response.json()
        return data

def usage(err:str=""):
    print("""
-------------------------------------------------------------------------------

    Remote Shell for Mist Devices
    ----------------------------

    Authors:
      - Thomas Munzer (tmunzer@juniper.net)
      - Hartmut Schroeder

    GitHub Repository:
      https://github.com/Mist-Automation-Programmability/mist_websocket_examples

    License:
      MIT License

-------------------------------------------------------------------------------
Description:
    This Python script opens an interactive remote shell session to a Mist device
    using the Mist API. It connects via WebSocket and provides a terminal-based
    shell interface.

-------------------------------------------------------------------------------
Requirements:
    - websocket-client: https://pypi.org/project/websocket-client/
    - python-dotenv:    https://pypi.org/project/python-dotenv/
    - sshkeyboard:      https://pypi.org/project/sshkeyboard/
    - requests:         https://pypi.org/project/requests/

-------------------------------------------------------------------------------
Configuration:
    You can provide required parameters in one of the following ways:
      1. Inline in the PARAMETERS section of this script.
      2. Using an environment file (recommended).
      3. As command-line arguments.

    Best Practice:
      - Store MIST_HOST and MIST_APITOKEN in an environment file.
      - Provide site and device IDs via command-line arguments.

-------------------------------------------------------------------------------
Command-Line Arguments:
    -h, --help              Show this help message and exit.
    -c, --cloud=HOST        Set the Mist cloud host (default: api.mist.com).
    -s, --site=SITE_ID      Set the site_id.
    -d, --device=DEVICE_ID  Set the device_id.
    -e, --env=FILE          Specify the environment file (default: "~/.mist_env").
    -l, --log_file=FILE     Set the log file path (default: "./websocket.log").

-------------------------------------------------------------------------------
Examples:
    python3 remote_shell.py
    python3 remote_shell.py --site=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 --device=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

""")
    if (err): 
        print(f"ERROR: {err}")
    sys.exit(0)


def start(env_file, mist_host, mist_site_id, mist_device_id, mist_apitoken):
    """
    Main entry point for starting the remote shell session. Loads environment variables, prints settings,
    retrieves shell info, and starts the MistSocket client.
    
    Args:
        env_file (str): Path to the .env file.
        mist_host (str): Mist API host.
        mist_site_id (str): Mist site ID.
        mist_device_id (str): Mist device ID.
        mist_apitoken (str): Mist API token.
    """
    logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.DEBUG,filename=LOG_FILE,filemode='w'
)
    mist_host, mist_apitoken, mist_site_id = _load_env(env_file, mist_host, mist_apitoken, mist_site_id)
    mist_apitoken = mist_apitoken.split(",")[0]
    
    print(" SETTINGS ".center(80, "-"))
    print(f"mist_host     : {mist_host}")
    print(f"mist_apitoken : {mist_apitoken[:6]}...{mist_apitoken[-6:]}")
    print(f"mist_site_id  : {mist_site_id}")
    print(f"MIST_DEVICE_ID: {mist_device_id}")
    WS_DATA = get_shell_info(mist_host, mist_site_id, mist_device_id, mist_apitoken)

    print(" WS DATA ".center(80, "-"))
    print(WS_DATA)
    print(" STARTING CLI ".center(80, "-"))
    print(" Enter '~'-Key for Shell exit ".center(80, "-"))
    socket = MistSocket(WS_DATA["url"])
    socket.start()


#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "hc:s:d:e:l:",
            [
                "help",
                "cloud="
                "site=",
                "device=",
                "env=",
                "log_file=",
            ],
        )
    except getopt.GetoptError as err:
        usage(err.msg)

    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-c", "--cloud"]:
            MIST_HOST = a
        elif o in ["-s", "--site"]:
            MIST_SITE_ID = a
        elif o in ["-d", "--device"]:
            MIST_DEVICE_ID = a
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    ### START ###
    start(
        ENV_FILE,
        MIST_HOST,
        MIST_SITE_ID,
        MIST_DEVICE_ID,
        MIST_APITOKEN
    )
