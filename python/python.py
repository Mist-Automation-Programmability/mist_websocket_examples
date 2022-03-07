import base64
import json

import websocket  # websocket-client==0.44.0

msg_received = 0


token = ''
org_id = ''
site_id = ''

def on_message(ws, message):
    global msg_received
    print('onmessage', message)


def on_error(ws, error):
    print('onerror')
    print(error)


def on_close(wsapp, close_status_code, close_msg):
    print('onclose')
    print(close_status_code)
    print(close_msg)


def on_open(ws):
    print('onopen')
    ws.send(json.dumps({'subscribe': '/sites/{0}/devices'.format(site_id)}))


if __name__ == "__main__":
    ws = websocket.WebSocketApp("wss://api-ws.mist.com/api-ws/v1/stream",
                                header={'Authorization': 'Token {0}'.format(token)},
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()