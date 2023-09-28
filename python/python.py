import json
import os
from datetime import datetime
from dotenv import load_dotenv

import websocket  # websocket-client==0.44.0

MSG_RECEIVED = 0

ENV_FILE = "~/.mist_env"
MIST_HOST = "api.mist.com"
MIST_APITOKEN = ''
MIST_ORG_ID = ''
MIST_SITE_ID = ''

def on_message(ws, message):
    global MSG_RECEIVED
    print(f' new message - {datetime.now()} '.center(80, "-"))
    try:
        message_json = json.loads(message)
        data_json = json.loads(message_json.get("data", {}))
        print(f"event: {message_json.get('event')}")
        print(f"channel: {message_json.get('channel')}")
        print("data:")
        print(json.dumps(data_json, indent=2))
    except:
        print(message)


def on_error(ws, error):
    print('onerror')
    print(error)


def on_close(wsapp, close_status_code, close_msg):
    print('onclose')
    print(close_status_code)
    print(close_msg)


def on_open(ws):
    print('onopen')
    ws.send(json.dumps({'subscribe': f'/sites/{MIST_SITE_ID}/stats/devices'}))

def _load_env(env_file:str, mist_host:str, mist_apitoken:str, mist_org_id:str, mist_site_id:str):
    if env_file.startswith("~/"):
        env_file = os.path.join(
            os.path.expanduser("~"), env_file.replace("~/", "")
        )
    load_dotenv(dotenv_path=env_file, override=True)
    if os.getenv("MIST_HOST"):
        mist_host = os.getenv("MIST_HOST")
    if os.getenv("MIST_APITOKEN"):
        mist_apitoken = os.getenv("MIST_APITOKEN")
    if os.getenv("MIST_ORG_ID"):
        mist_org_id = os.getenv("MIST_ORG_ID")
    if os.getenv("MIST_SITE_ID"):
        mist_site_id = os.getenv("MIST_SITE_ID")
    return mist_host, mist_apitoken, mist_org_id, mist_site_id


if __name__ == "__main__":
    MIST_HOST, MIST_APITOKEN, MIST_ORG_ID, MIST_SITE_ID = _load_env(ENV_FILE, MIST_HOST, MIST_APITOKEN, MIST_ORG_ID, MIST_SITE_ID)
    # host for websocket is api-ws.mist.com, so replacing "api." or "manage." with "api-ws." if not the right host
    if MIST_HOST.startswith("api."):
        MIST_HOST = MIST_HOST.replace("api.", "api-ws.")
    elif MIST_HOST.startswith("manage."):
        MIST_HOST = MIST_HOST.replace("manage.", "api-ws.")
    print(f"MIST_HOST     : {MIST_HOST}")
    print(f"MIST_APITOKEN : {MIST_APITOKEN[:6]}...{MIST_APITOKEN[-6:]}")
    print(f"MIST_ORG_ID   : {MIST_ORG_ID}")
    print(f"MIST_SITE_ID  : {MIST_SITE_ID}")
    ws = websocket.WebSocketApp(f"wss://{MIST_HOST}/api-ws/v1/stream",
                                header={'Authorization': f'Token {MIST_APITOKEN}'},
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()
