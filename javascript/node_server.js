const WebSocket = require('ws');
const url = "wss://api-ws.mist.com/api-ws/v1/stream";
const org_id = "";
const site_id = "";
const apitoken = "";
let count = 0;
let topics = [];

function _subscribe(topic) {
    payload = {
        subscribe: topic
    }
    topics.push(topic)
    socket.send(JSON.stringify(payload))
}

function _unsubscribe(topic) {
    payload = {
        unsubscribe: topic
    }
    socket.send(JSON.stringify(payload))
}

function _close() {
    topics.forEach(topic => {
        _unsubscribe(topic)
    })
    socket.close(1000);
}


// create the socket
let socket = new WebSocket(url, {
    headers: {
        Authorization: "Token " + apitoken
    }
});
socket.onopen = function(e) {
    console.log("[open] Connection established");
    _subscribe("/sites/" + site_id + "/devices");
    //_subscribe("/test");
};

socket.onmessage = function(event) {
    console.log(`[message] Data received from server: ${event.data}`);
    count += 1;
    if (count == 5) {
        _close()
    }
};

socket.onclose = function(event) {
    if (event.wasClean) {
        console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
    } else {
        // e.g. server process killed or network down
        // event.code is usually 1006 in this case
        console.log('[close] Connection died');
    }
};

socket.onerror = function(error) {
    console.log(`[error] ${error.message}`);
};