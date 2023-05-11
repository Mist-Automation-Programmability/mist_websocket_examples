import base64
import json

import websocket  # websocket-client==0.44.0

msg_received = 0


token = ''
org_id = ''
site_id = ''

def on_message(ws, message):
    global msg_received
    print('new message'.center(80, "-"))
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
    ws.send(json.dumps({'subscribe': f'/sites/{site_id}/stats/devices'}))


if __name__ == "__main__":
    ws = websocket.WebSocketApp("wss://api-ws.mist.com/api-ws/v1/stream",
                                header={'Authorization': f'Token {token}'},
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()